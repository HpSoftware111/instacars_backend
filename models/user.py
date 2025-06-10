from pydantic import BaseModel
from sqlalchemy import TIMESTAMP, Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime,timezone

Base = declarative_base()
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, default="")
    login_type = Column(String, default="email")
    social_id = Column(String, default="")
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    ai_data = Column(Boolean, default=False)  # ✅ default False
    avatar_url = Column(String, nullable=True, default="/uploads/avatars/test.png")  # Add this line
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))