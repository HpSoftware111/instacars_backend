import logging
import uuid
from models.chat import ChatMessage
from sqlalchemy.orm import sessionmaker, Session
from utils.util import engine

class ChatService():
  def __init__(self):
    self._session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

  def store_chat_messages_db(self, chat_id, message, user_id ):
    new_chat_message = ChatMessage(
      message_id=uuid.uuid4(),
      chat_id=chat_id,
      message=message,
      user_id= user_id
    )
    logging.info(f"message saved: {message}")

    session: Session = self._session()

    try:
      session.add(new_chat_message)
      session.commit()
      session.refresh(new_chat_message)
      return new_chat_message
    except Exception as e:
      session.rollback()
      raise e
    finally:
      session.close()

  def get_chat_messages(self, chat_id):
    session: Session = self._session()

    try:
      chat_messages = session.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).all()
      return chat_messages
    except Exception as e:
      raise e
    finally:
      session.close()