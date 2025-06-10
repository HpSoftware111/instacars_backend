import logging
from llama_index.core import PromptTemplate
from llama_index.llms.openai import OpenAI

from prompts.prompt import CONVERSATION_SUMMARY_PROMPT, DETERMINE_AGENTS_TO_CALL_PROMPT

class OrchestationAgent():
  def __init__(self):
    self.llm = OpenAI(temperature=1.0, model="gpt-4o-mini")

  async def generate_conversation_summary(self, chat_history):
    conversation_summary_template = PromptTemplate(CONVERSATION_SUMMARY_PROMPT)
    prompt = conversation_summary_template.format(chat_history=chat_history)
    output = self.llm.complete(prompt)
    # logging.info(output)
    return output

  async def determine_agent_to_call(self, store_chat_messages, conversation_summary: str, message: str, session={}):
    determine_agent_to_call_template = PromptTemplate(DETERMINE_AGENTS_TO_CALL_PROMPT)
    prompt = determine_agent_to_call_template.format(
      conversation_summary=conversation_summary,
      message=message, 
    )
    output = self.llm.complete(prompt)
    # logging.info(output)
    return str(output)
