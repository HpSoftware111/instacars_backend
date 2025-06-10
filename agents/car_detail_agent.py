import logging, json
import json_repair

from llama_index.llms.openai import OpenAI
from llama_index.core import PromptTemplate, ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole
from sqlalchemy.orm import sessionmaker

from prompts.prompt import CAR_DETAILS_SUMMARY_PROMPT, CAR_DETAILS_PROMPT
from models.model import CarDetailResponse
from utils.util import engine
from models.car import Car

output_example = [
  {"type": "message", "content": "This car has a clean history with no reported accidents. It's in great condition!"},
  {"type": "options", "content": ["Pictures", "Book Test Drive"]}
]

class CarDetailAgent():
  def __init__(self):
    self.llm = OpenAI(temperature=1.0, model="gpt-4o-mini")
    self._session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

  async def generate_car_summary(self, car_detail):
    conversation_summary_template = PromptTemplate(CAR_DETAILS_SUMMARY_PROMPT)
    prompt = conversation_summary_template.format(car_detail=car_detail)
    output = self.llm.complete(prompt)
    logging.info(output)
    return output

  async def _get_all_car_details(self, id):
    with self._session() as session:
      car = session.query(Car).filter(Car.id==id).first()
      return car.to_dict_for_agent()

  async def conversation(self, store_chat_messages, chat_history, message, car_id, user_id, session={}):
    conversation_messages = [
      ChatMessage(
        role=MessageRole.SYSTEM,
        content=CAR_DETAILS_PROMPT,
      ),
      ChatMessage(role=MessageRole.USER, content=("Message: {message}"))
    ]
    store_chat_messages(session["session_id"], role="user", message=message, user_id=user_id)
    car = await self._get_all_car_details(car_id)
    logging.info(car.get("heading"))
    prompt = ChatPromptTemplate.from_messages(conversation_messages).format(
      car_details=json.dumps(car),
      # will think of keeping history separate
      chat_history=chat_history,
      message=message,
      output_example=json.dumps(output_example),
    )
    response = self.llm.complete(prompt)
    corrected_response = json_repair.loads(str(response))
    
    logging.info(corrected_response)
    
    final_response = [CarDetailResponse(type=msg.get("type"), content=msg.get("content")) for msg in corrected_response]
    
    store_chat_messages(session["session_id"], role="assistant", message=str([msg.get("content") for msg in corrected_response]), user_id=user_id)
    return final_response
