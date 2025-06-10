# schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserSaveRequest(BaseModel):
    id: str
    email: str
    name: str
    picture: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    username: Optional[str] = ""
    login_type: Optional[str] = "email"
    social_id: Optional[str] = ""
    avatar_url: Optional[str] = "/uploads/avatars/test.png"
    is_active: Optional[bool] = True
    ai_data: Optional[bool] = False

class UserUpdate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    is_active: Optional[bool]
    ai_data: bool = False  # ✅ default to False if not provided

class EmailRequest(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    token: str
    new_password: str
class ConfirmResetRequest(BaseModel):
    token: str
    new_password: str
class AIDataUpdateRequest(BaseModel):
    ai_data: bool
class TokenRequest(BaseModel):
    token: str
