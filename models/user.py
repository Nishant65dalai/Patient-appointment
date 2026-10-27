import sqlite3
import logging
from fastapi import HTTPException,status
from pydantic import BaseModel
from auth import verify_password


logger = logging.getLogger("hospital_api")

class LoginRequest(BaseModel):
    username:str
    password:str

class TokenResponse(BaseModel):
    access_token:str
    token_type :str ='bearer'



class UserService:
    @staticmethod
    async def authenticate(db :sqlite3.Connection,username:str,password:str):
        try:
            row = db.execute(
                "select * from users where username = ?" ,(username,)
            ).fetchone()
            logging.info(f"the usr trying to login is {row['username']}")
            if row is None or not verify_password(password, row["hashed_pw"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                )
        except Exception as e:
            logging.exception(e)
            raise e
        return dict(row)
