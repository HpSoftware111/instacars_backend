from utils.util import engine
from sqlalchemy.orm import sessionmaker
from models.form import ContactForm

import uuid

class FormService():
    def __init__(self):
      self._session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    async def store_contact_form(self, form, ip_address):
      with self._session() as session:
        try:
            new_contact = ContactForm(
                id=str(uuid.uuid4()),
                type=form.type,
                form_data=form.form,
                ip_address=ip_address
            )
            session.add(new_contact)
            session.commit()
            session.refresh(new_contact)
            return {
                "id": new_contact.id,
                "type": new_contact.type,
                "form_data": new_contact.form_data,
                "created_at": new_contact.created_at,
                "ip_address": new_contact.ip_address
            }
        except Exception as e:
            raise e
    async def delete_contact_form_by_id(self, id):
      with self._session() as session:
        try:
            contact = session.query(ContactForm).filter(ContactForm.id == id).first()
            if contact:
                session.delete(contact)
                session.commit()
                return {
                    "message": "Contact form deleted successfully"
                }
            return {
                "message": "Contact form not found"
            }
        except Exception as e:
            raise e
