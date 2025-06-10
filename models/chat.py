from sqlalchemy import Column, DateTime, UUID, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime,timezone

Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(Integer, nullable=False)  # Added user_id field
    message = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))