import sqlite3
import logging
from datetime import date
from pathlib import Path
import yaml
from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger("hospital_api")


class HistoryFilter(BaseModel):
    """Body for POST /appointments/history.

    mrn is required. Every other field is optional - send only the
    ones you want to filter by, in any combination.
    """
    mrn: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    status: Optional[str] = None
    doctor_id: Optional[int] = None
    department: Optional[str] = None


class AppointmentHistoryItem(BaseModel):
    appointment_id: int
    appointment_date: str
    appointment_time: str
    status: str
    notes: str
    diagnosis: str
    patient_name: str
    mrn: str
    doctor_id: int
    doctor_name: str
    specialization: str
    department: str


class AppointmentCreate(BaseModel):
    """Body for POST /appointments. No path parameter - mrn included here."""
    mrn: str
    doctor_id: int
    appointment_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    appointment_time: str = "10:00"
    notes: str = ""


class AppointmentUpdate(BaseModel):
    """Body for PUT /appointments. appointment_id is a separate
    (query) parameter - see routers/appointments.py."""
    status: Optional[str] = None
    notes: Optional[str] = None
    diagnosis: Optional[str] = None


class AppointmentResponse(BaseModel):
    appointment_id: int
    patient_id: int
    doctor_id: int
    appointment_date: str
    appointment_time: str
    status: str
    notes: str
    diagnosis: str
    created_at: str
    patient_name: str
    mrn: str
    doctor_name: str
    specialization: str
    department: str


with open(Path(__file__).resolve().parent.parent / 'sql' / 'appointments.yaml') as f:
    queries = yaml.safe_load(f)


FILTER_MAP = {
    "from_date":  "a.appointment_date >= ?",
    "to_date":    "a.appointment_date <= ?",
    "status":     "a.status = ?",
    "doctor_id":  "a.doctor_id = ?",
    "department": "LOWER(d.department) = LOWER(?)",
}

VALID_STATUSES = {"scheduled", "confirmed", "completed", "cancelled"}


def _bad_request(detail: str):
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _parse_date(value: str, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise _bad_request(f"{label} must be a valid date in YYYY-MM-DD format")


def _validate_status(value: str):
    if value not in VALID_STATUSES:
        raise _bad_request(
            f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )


class AppointmentService:

    @staticmethod
    async def get_history(db: sqlite3.Connection, payload: HistoryFilter):
        try:
            from_date = _parse_date(payload.from_date, "from_date") if payload.from_date else None
            to_date = _parse_date(payload.to_date, "to_date") if payload.to_date else None
            if from_date and to_date and from_date > to_date:
                raise _bad_request("from_date cannot be greater than to_date")
            if payload.status is not None:
                _validate_status(payload.status)

            patient_row = db.execute(
                queries['get_patient_id'], (payload.mrn,)
            ).fetchone()
            if patient_row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No patient with MRN '{payload.mrn}'",
                )

            filters = ["p.mrn = ?"]
            params = [payload.mrn]
            data = payload.model_dump(exclude_none=True, exclude={"mrn"})
            for field, value in data.items():
                template = FILTER_MAP.get(field)
                if template:
                    filters.append(template)
                    params.append(value)
            where_clause = " AND ".join(filters)
            query = queries['history_base'].format(filters=where_clause)
            rows = db.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(e)
            raise e

    @staticmethod
    async def create(db: sqlite3.Connection, payload: AppointmentCreate):
        try:
            appointment_day = _parse_date(payload.appointment_date, "appointment_date")
            if appointment_day < date.today():
                raise _bad_request("Appointment date cannot be in the past")

            patient_row = db.execute(
                queries['get_patient_id'], (payload.mrn,)
            ).fetchone()
            if patient_row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No patient with MRN '{payload.mrn}'",
                )
            patient_id = patient_row["patient_id"]

            doctor_row = db.execute(
                queries['get_doctor_id'], (payload.doctor_id,)
            ).fetchone()
            if doctor_row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No doctor with id {payload.doctor_id}",
                )

            cursor = db.execute(
                queries['create'],
                (
                    patient_id,
                    payload.doctor_id,
                    payload.appointment_date,
                    payload.appointment_time,
                    payload.notes or "",
                ),
            )
            db.commit()
            new_id = cursor.lastrowid
            logger.info(f"appointment created id={new_id} mrn={payload.mrn}")
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(e)
            raise e
        return {"message": "appointment created", "appointment_id": new_id}

    @staticmethod
    async def update(db: sqlite3.Connection, appointment_id: int,
                      payload: AppointmentUpdate):
        try:
            fields = payload.model_dump(exclude_unset=True)
            logging.info(f"fields to update {fields}")
            if not fields:
                raise _bad_request("No fields provided to update")
            if "status" in fields:
                _validate_status(fields["status"])
            for key in ("notes", "diagnosis"):
                if key in fields and fields[key] is None:
                    fields[key] = ""

            existing = db.execute(
                queries['get_by_id'], (appointment_id,)
            ).fetchone()
            if existing is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Appointment {appointment_id} not found",
                )

            if fields.get("status") == "completed":
                diagnosis = fields.get("diagnosis") or existing["diagnosis"]
                if not diagnosis or not diagnosis.strip():
                    raise _bad_request(
                        "Diagnosis is required when appointment status is completed"
                    )

            set_clause = ", ".join(f"{k} = ?" for k in fields)
            query = queries['update_table'].format(placeholder=set_clause)
            db.execute(query, list(fields.values()) + [appointment_id])
            db.commit()
            logger.info(f"appointment updated id={appointment_id}")
            row = db.execute(
                queries['get_by_id'], (appointment_id,)
            ).fetchone()
            return dict(row)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(e)
            raise e
