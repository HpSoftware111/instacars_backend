import json
import logging
import json_repair
from prompts.prompt import GIPHY_SUGGESTION_PROMPT
from llama_index.core import PromptTemplate
from llama_index.llms.openai import OpenAI

giphys = {
  "good_luck": "https://i.giphy.com/cOtF7s5sM18VRoMfin.webp",
  "patience": "https://i.giphy.com/QvBoMEcQ7DQXK.webp" 
}

output_example = [
  {"type": "gif", "content": "https://example.com/introducing.gif"},
]

class GiphySuggestionAgent():
  def __init__(self):
    self.llm = OpenAI(temperature=0.8, model="gpt-4o-mini")

  async def suggest_giphy(self, store_chat_messages, chat_history, user_id, session={} ):
    logging.info("calling giphy suggestion agent")
    conversation_summary_template = PromptTemplate(GIPHY_SUGGESTION_PROMPT)
    prompt = conversation_summary_template.format(chat_history=chat_history, gif_list=giphys, output_example=json.dumps(output_example))
    output = self.llm.complete(prompt)
    # logging.info(output)
    store_chat_messages(session["session_id"], role="assistant", message=str(output), user_id=user_id)
    return json_repair.loads(str(output))
  
