import logging
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core import ChatPromptTemplate

from prompts.prompt import GENERAL_CONVERSATION_PROMPT
from models.model import Response
import json_repair

class GeneralAgent():
  def __init__(self):
    self.llm = OpenAI(temperature=1.0, model="gpt-4o-mini")

  async def conversation(self, store_chat_messages, chat_history, message,  user_id, session):
    conversation_messages = [
      ChatMessage(
        role=MessageRole.SYSTEM,
        content=GENERAL_CONVERSATION_PROMPT,
      ),
      ChatMessage(role=MessageRole.USER, content=("Message: {message}"))
    ]

    store_chat_messages(session["session_id"], role="user", message=message, user_id=user_id)

    prompt = ChatPromptTemplate.from_messages(conversation_messages).format(chat_history=chat_history, message=message)
    response = self.llm.complete(prompt)
    final_response = Response(messages=json_repair.loads(str(response)))
    store_chat_messages(session["session_id"], role="assistant", message=str(response), user_id=user_id)
    # logging.info(response)
    return final_response



