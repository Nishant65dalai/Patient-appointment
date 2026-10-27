from fastapi import Depends ,APIRouter
import sqlite3
from db import get_db
from auth import create_token
from dependencies import require_admin,verify_jwt
from models.doctor import DoctorService,DoctorCreate,DoctorResponse,DoctorUpdate

router= APIRouter()

@router.post("",dependencies=[Depends(require_admin)])
async def create_doctor(doctor:DoctorCreate,db: sqlite3.Connection = Depends(get_db)):
    doctors = DoctorService()
    resp =  await doctors.create(db,doctor)
    return resp


@router.get("",response_model=list[DoctorResponse],dependencies=[Depends(verify_jwt)])
async def get_all_list(limit:int =20,offset: int =0,db : sqlite3.Connection = Depends(get_db)):
    doctors = DoctorService()
    resp = await doctors.list_all(db,limit,offset)
    return resp

@router.get("/department",response_model=list[DoctorResponse],dependencies=[Depends(verify_jwt)])
async def get_all_list(department:str,limit:int =20,offset: int =0,db : sqlite3.Connection = Depends(get_db)):
    doctors = DoctorService()
    resp = await doctors.list_as_department(db,department,limit,offset)
    return resp

@router.put("",response_model=DoctorResponse,dependencies=[Depends(require_admin)])
async def update_doctor(doctor_id:int,doctor:DoctorUpdate,db : sqlite3.Connection = Depends(get_db)):
    doctors = DoctorService()
    resp = await doctors.doctor_update(db,doctor_id,doctor)
    return resp

@router.delete("",dependencies=[Depends(require_admin)])
async def delete_doctor(doctor_id,db : sqlite3.Connection = Depends(get_db)):
    doctors = DoctorService()
    resp = await doctors.doctor_delete(db,doctor_id)
    return resp

