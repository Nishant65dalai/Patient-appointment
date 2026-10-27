from fastapi import Depends, APIRouter
import sqlite3
from db import get_db
from dependencies import require_admin, verify_jwt
from models.appointment import (
    AppointmentService, HistoryFilter, AppointmentCreate,
    AppointmentUpdate, AppointmentHistoryItem, AppointmentResponse,
)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/history", response_model=list[AppointmentHistoryItem]
            )
async def get_history(payload: HistoryFilter,
                       db: sqlite3.Connection = Depends(get_db)):
    appointments = AppointmentService()
    resp = await appointments.get_history(db, payload)
    return resp


@router.post("")
async def create_appointment(payload: AppointmentCreate,
                              db: sqlite3.Connection = Depends(get_db)):
    appointments = AppointmentService()
    resp = await appointments.create(db, payload)
    return resp


@router.put("", response_model=AppointmentResponse
        )
async def update_appointment(appointment_id: int,
                              payload: AppointmentUpdate,
                              db: sqlite3.Connection = Depends(get_db)):
    appointments = AppointmentService()
    resp = await appointments.update(db, appointment_id, payload)
    return resp
