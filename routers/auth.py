import sqlite3
from fastapi import Depends ,APIRouter
from db import get_db
from auth import create_token

from models.user import TokenResponse,LoginRequest,UserService


router= APIRouter()

@router.post("/login",response_model =TokenResponse)
async def login(credentails:LoginRequest,db: sqlite3.Connection = Depends(get_db)):
    user = UserService()
    my_user = await user.authenticate(db,credentails.username,credentails.password)
    token = create_token({'sub':my_user['username'],'role':my_user['role']})
    return TokenResponse(access_token=token,token_type='bearer')
