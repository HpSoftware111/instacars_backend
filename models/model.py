from pydantic.v1 import BaseModel
from typing import List, Optional, Union

class ChatMessage(BaseModel):
  """
  Data Model for a message
  """
  role:str
  content: str

class ChatHistory(BaseModel):
  """
  Data Model for a chat history
  """
  messages: List[ChatMessage]

class Response(BaseModel):
  """
  Data model for a car search response
  """
  messages: List[str]

class SuggestedCar(BaseModel):
  """
  Data model for a suggested car
  """
  id: str
  title: Optional[str]
  km: Optional[int]
  sellingPrice: Optional[float]
  marketPrice: Optional[float]
  imgURL: Optional[str]

class CarSearchResponse(BaseModel):
  """
  Data model for a car search response
  """
  type: str
  content: Union[List[SuggestedCar], List[str], str]

class CarOptionsResponse(BaseModel):
  """
  Data model for a car options response
  """
  type: str
  content: List[str]

class CarDetailResponse(BaseModel):
  """
  Data model for a car detail response
  """

  type: str
  content: Union[List[str], str]

class GiphySuggestionResponse(BaseModel):
  """
  Data model for a car search response
  """
  type: str
  content: str
