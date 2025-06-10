from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from schema import schemas
from datetime import datetime, timedelta
from dotenv import load_dotenv
# from . import crud, models, schemas, utils, database

# Load environment variables
load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = os.getenv("JWT_TOKEN_ALGORITHM")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_user(db: Session, user_id: int):
    return crud.get_user(db, user_id)

def get_user_by_email(db: Session, email: str):
    return crud.get_user_by_email(db, email)

def verify_token(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        if user_update.email:
            db_user.email = user_update.email
        if user_update.username:
            db_user.username = user_update.username
        if user_update.password:
            db_user.hashed_password = utils.get_password_hash(user_update.password)
        db.commit()
        db.refresh(db_user)
        return db_user
    return None
def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)  
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=1000000)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_email_from_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Token missing subject")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
def get_user_id_from_token(token:str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Token missing subject")
        user = db.query(models.User).filter(models.User.email == email).first()    
        return user.id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")