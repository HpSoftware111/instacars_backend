import logging, json
import os
import time
import httpx
import json_repair
import asyncio

from typing import List
from sqlalchemy.orm import sessionmaker
from utils.util import filter_keys, structured_car_search_output, engine
from utils.nlp import normalize_price_from_text  # if stored separately

from models.car import Car, CarSummary
from services.car import CarService

from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core import ChatPromptTemplate

from models.model import CarOptionsResponse, CarSearchResponse

from prompts.prompt import CARS_OPTIONS_PROMPT_V2, CARS_SUGGESTION_PROMPT_V2, FILTER_CAR_PROMPT

output_example_with_introduction = [
  {"type": "message", "content": "Got it! Used cars under $50000 can offer great value. 👍"},
  {"type": "suggestion",
   "content": [
      {
        "id": "1FMCU0CZ7MUA87322-476da08c-c427",
        "title": "2021 Ford Escape SEL Hybrid 4dr Front-Wheel Drive",
        "km": 57542,
        "sellingPrice": 25774.0,
        "marketPrice": 25774.0,
        "imgURL": "https://images.edealer.ca/2/147266674.jpeg"
      }
  ]}
]

output_example_filters = {
    "car_type": "used",
    "price_range":"0-50000",
    "make": "Toyota",
    "model": "Camry",
    "year_range": "2015-2025",
    "mileage": "under 50,000 miles",
    "transmission": "automatic",
    "fuel_type": "gasoline",
    "drivetrain": "AWD",
    "body_type": "SUV,sedan",
    "doors": "4",
    "color": "blue",
    "seller_type": "franchise"
  }
options_output_example = {
    "type": "options",
    "content": [
      "Only electric and hybrid cars",
      "Show all fuel types",
      "Options under $30,000"
    ]
}

AVAILABLE_FILTER_OPTIONS = {
    "car_type": ["new", "used", "certified"],
    "make": ["Toyota", "Honda", "Ford", "Tesla", "Hyundai"],
    "model": ["Camry", "Accord", "Model 3", "Elantra"],
    "price_range": "numerical e.g., 'under 10k', 'between 5k and 15k'",
    "year_range": "e.g., '2015-2020'",
    "mileage": "e.g., 'under 50,000 miles'",
    "transmission": ["automatic", "manual", "CVT"],
    "fuel_type": ["gasoline", "diesel", "electric", "hybrid"],
    "drivetrain": ["FWD", "AWD", "RWD", "4WD"],
    "body_type": ["sedan", "SUV", "coupe", "pickup", "hatchback"],
    "doors": ["2", "4"],
    "color": ["black", "white", "blue", "silver", "red"],
    "seller_type": ["franchise", "independent"]
}


class CarSearchAgent():
  def __init__(self):
    self.llm = OpenAI(temperature=1.0, model="gpt-4o-mini")
  
  def get_filter_info_string(self):
    filter_info_lines = []
    for k, v in AVAILABLE_FILTER_OPTIONS.items():
        values = ", ".join(v) if isinstance(v, list) else v
        filter_info_lines.append(f"{k}: {values}")
    return "\n".join(filter_info_lines)

  async def get_suggested_cars(self, car_ids):
    Session = sessionmaker(bind=engine)
    with Session() as session:
      cars = session.query(Car).filter(Car.id.in_(tuple(car_ids))).all()
      if len(cars) > 0:
        return [{
          "id": car.id, 
          "title": car.heading, 
          "km": car.ref_miles,
          "sellingPrice": float(car.price), 
          "marketPrice": float(car.msrp), 
          "imgURL": car.media["photo_links"][0]
        } for car in cars]

      return []
 
  async def _get_all_car_summaries(self):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with Session() as session:
      cars_summary = session.query(CarSummary).all()
      return [{"id": cs.id, "summary": cs.summary} for cs in cars_summary]

  async def _get_suggested_cars_from_marketcheck(self,filter):
    host = os.getenv("MARKETCHECK_HOST")
    api_key = os.getenv("MARKETCHECK_API_KEY")

    base_url =  f"https://{host}/v2/search/car/active"

    params = {
      "api_key": api_key,
      "include_relevent_links": "true",
      "start": "0",
      "rows": "10",
      "country": "CA"
    }

    # copy filters into params
    for key, value in filter.items():
      if value is not None:
        if isinstance(value, list):  # Join list values into comma-separated strings
          params[key] = ",".join(value)
        else:
          params[key] = value

    async with httpx.AsyncClient() as client:
      response =await client.get(base_url,params = params)
      # logging.info(f"get => {response.request.url}")
      cars = response.json().get("listings") or []
      asyncio.create_task(asyncio.to_thread(CarService().save_cars_in_db, cars))
      return cars

  async def conversation_to_get_options(self, suggested_cars, chat_history, message):
    option_conversation_messages = [
      ChatMessage(
        role=MessageRole.SYSTEM,
        content=CARS_OPTIONS_PROMPT_V2,
      ),
      ChatMessage(role=MessageRole.USER, content=("Message: {message}"))
    ]
    
    options_prompt = ChatPromptTemplate.from_messages(option_conversation_messages).format(
      suggested_car_list=json.dumps(suggested_cars),
      chat_history=chat_history,
      message=message,
      output_example=options_output_example,
    )
    response = self.llm.complete(options_prompt)
    corrected_options_response = json_repair.loads(str(response))    
    logging.info(corrected_options_response)

    final_response = CarOptionsResponse(type=corrected_options_response.get("type"), content=corrected_options_response.get("content")) 

    return final_response

  async def extract_chat_filters(self,filter_history, message):
    filter_message = [
    ChatMessage(
        role=MessageRole.SYSTEM,
        content=FILTER_CAR_PROMPT,
      ),
      ChatMessage(role=MessageRole.USER, content= message)
    ]

    filter_prompt = ChatPromptTemplate.from_messages(filter_message).format(
      filter_history=filter_history,
      output_example=output_example_filters,
      current_date=time.strftime("%Y-%m-%d %H:%M:%S"),
      filter_options=self.get_filter_info_string()
    )

    #  🧠 Inject additional NLP-based price normalization

    response = self.llm.complete(filter_prompt)
    corrected_response = json_repair.loads(str(response))
    price_filters = normalize_price_from_text(message)
    corrected_response.update(price_filters)
    return corrected_response

  async def conversation(self, store_chat_messages, filter_history, chat_history, message, user_id, session={} ) :
    conversation_messages = [
      ChatMessage(
        role=MessageRole.SYSTEM,
        content=CARS_SUGGESTION_PROMPT_V2,
      ),
      ChatMessage(role=MessageRole.USER, content=(f"UserMessage: {message}"))
    ]

    store_chat_messages(session["session_id"], role="user", message=message, user_id=user_id)
    # logging.info(f"before extraction the filters are :{filter_history}")
    filter_start_time = time.time()
    filter = await self.extract_chat_filters(filter_history[session["session_id"]], message)
    filter_time = time.time() - filter_start_time
    logging.info(f"⏱️ Time taken for extracting chat filter: {filter_time:.4f} sec")
    filter_history[session["session_id"]]=filter
    # logging.info(f"FILTER => {filter_history}")
    # get cars list from marketcheck
    non_null_filters = {k: v for k, v in filter.items() if v is not None}
    
    car_list = await self._get_suggested_cars_from_marketcheck(non_null_filters)
    filtered_car_list = filter_keys(car_list) if car_list is not None else []
    # logging.info(filtered_car_list)
    prompt = ChatPromptTemplate.from_messages(conversation_messages).format(
      car_list=json.dumps(filtered_car_list),
      chat_history=chat_history,
      message=message,
      filter=filter,
      output_example=json.dumps(output_example_with_introduction),
    )
    # logging.info(f"PROMPT for handle car list => {prompt}")

    cars_filter_start_time = time.time()
    response = self.llm.complete(prompt)
    cars_filter_time = time.time() - cars_filter_start_time
    logging.info(f"⏱️ Time taken for car filter: {cars_filter_time:.4f} sec")
    corrected_response = json_repair.loads(str(response))
    # logging.info(corrected_response)

    parsed_response = structured_car_search_output(corrected_response)
    
    final_response = [CarSearchResponse(type=msg.get("type"), content=msg.get("content")) for msg in parsed_response]
    
    store_chat_messages(session["session_id"], role="assistant", message=str([msg.get("content") for msg in parsed_response]), user_id=user_id)

    return final_response

