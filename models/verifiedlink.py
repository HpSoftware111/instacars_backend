from pydantic import BaseModel
from sqlalchemy import TIMESTAMP, Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime,timezone
Base = declarative_base()

class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
