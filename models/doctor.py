import sqlite3
import logging
from pathlib import Path
import yaml
from fastapi import HTTPException,status
from pydantic import BaseModel,Field
from typing import Optional

logger = logging.getLogger("hospital_api")

class DoctorCreate(BaseModel):
    name : str = Field(min_length=2,max_length=100)
    specialization:str
    license_no :str
    department :str
    contact: Optional[str] = None
    available: bool = True

class DoctorUpdate(BaseModel):
    name : Optional[str] = Field(default=None,min_length=2,max_length=100)
    specialization:Optional[str] = None
    department :Optional[str] = None
    contact: Optional[str] = None
    available: Optional[bool] = True

class DoctorResponse(BaseModel):
    doctor_id: int
    name : str
    specialization:str
    license_no :str
    department :str
    contact: Optional[str] = None
    available: bool
    created_at : str



with open(Path(__file__).resolve().parent.parent / 'sql' / 'dcotors.yaml') as f:
    queries =yaml.safe_load(f)

class DoctorService:
    @staticmethod
    async def create(db:sqlite3.Connection, doctor: DoctorCreate):
        try:
            cursor = db.execute(queries['create'],(doctor.name, doctor.specialization,doctor.license_no,doctor.department,doctor.contact,int(doctor.available)))
            db.commit()
            new_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning("Duplicate license rejected: mrn=%s", doctor.license_no)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A dcotor with liscence '{doctor.license_no}' already exists",
            )
        return {'message':'dcotor created'}
    
    @staticmethod
    async def list_all(db:sqlite3.Connection,limit:int,offset:int):
        try:
            rows = db.execute(queries['read'] ,(limit,offset)).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logging.exception(e)
            raise e
    
    @staticmethod
    async def list_as_department(db:sqlite3.Connection,department:str,limit:int,offset:int):
        rows = db.execute(queries['get_doctor_by_dept'] ,(department,limit,offset)).fetchall()
        return [dict(r) for r in rows]
    
    @staticmethod
    async def doctor_update(db:sqlite3.Connection,doctor_id:int,doctor_data:DoctorUpdate):
        try:
            fields = doctor_data.model_dump(exclude_unset=True)
            logging.info(f'fileds to update {fields}')
            if not fields:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                     detail="No fields provided to update")
            if "available" in fields:
                fields["available"] = int(fields["available"])
            
            existing = db.execute(queries['get_by_id'],(doctor_id,)).fetchone()
            if existing is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                     detail=f"Doctor {doctor_id} not found")
            set_clause = ", ".join(f"{key}=?" for key in fields)
            query = queries['update_table'].format(placeholder=set_clause)
            db.execute(query,list(fields.values()) + [doctor_id])
            db.commit()
            logger.info (f"doctor value updated for {doctor_id}")
            row = db.execute(queries['get_by_id'],(doctor_id,)).fetchone()
            return dict(row)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(e)
            raise e
        
    @staticmethod    
    async def doctor_delete(db:sqlite3.Connection,doctor_id):
        try:
            doctor_id = doctor_id.split(",")
            placeholder = ",".join("?" *len(doctor_id))
            query = queries['delete_entry'].format(placeholder=placeholder)
            result = db.execute(query,doctor_id)
            db.commit()
            logging.info(f"deleted doctor id is {doctor_id}")
            if result.rowcount==0:
                logging.warning("No user deleted")
        except Exception as e:
            logging.exception(e)
            raise e
        return await DoctorService.list_all(db,20,0)
        

        
