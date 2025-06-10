from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime,timezone

Base = declarative_base()

class ContactForm(Base):
    __tablename__ = "contact_forms"
    
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    form_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    ip_address = Column(String)
