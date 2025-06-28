# File: providers/scaleway_llm.py

import json
import re
from openai import OpenAI
from llm_client import LLMClient, BASE_SYSTEM_PARSER, SYSTEM_CHAT
from config import Config

class ScalewayLLMClient(LLMClient):
    """LLMClient implementation for Scaleway Generative APIs (OpenAI-compatible)."""

    def __init__(self):
        self.client = OpenAI(
            base_url=Config.SCALEWAY_API_URL,
            api_key=Config.SCALEWAY_API_KEY,
            timeout=Config.LLM_REQUEST_TIMEOUT
        )
        self.model_name = Config.SCALEWAY_MODEL_NAME

    def parse_intents(self, user_input: str, last_filename: str | None = None, available_actions_prompt: str = "") -> list[dict]:
        json_string_to_parse = ""
        
        # Build the full system parser prompt dynamically
        full_system_parser_prompt = BASE_SYSTEM_PARSER 
        
        if available_actions_prompt:
            full_system_parser_prompt += available_actions_prompt

        if last_filename:
            full_system_parser_prompt += f"\n\nLAST_REMEMBERED_FILE: {last_filename}"

        messages = [
            {"role": "system", "content": full_system_parser_prompt},
            {"role": "user", "content": user_input}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=Config.LLM_TEMPERATURE,
                top_p=Config.LLM_TOP_P,
                max_tokens=Config.LLM_MAX_TOKENS,
                presence_penalty=Config.LLM_PRESENCE_PENALTY, 
                frequency_penalty=Config.LLM_FREQUENCY_PENALTY, 
                stream=False, # Keeping False for compatibility with current backend architecture
            )
            
            raw_response_text = response.choices[0].message.content
            print(f"DEBUG: Raw response text from Scaleway API:\n---\n{raw_response_text}\n---")

            json_string_to_parse = raw_response_text.strip()

            # Robust JSON extraction logic
            match = re.search(r"```(?:\w+)?\s*(.*?)\s*```", json_string_to_parse, re.DOTALL)
            
            if match:
                json_string_to_parse = match.group(1).strip()
                print(f"DEBUG: Extracted JSON string from markdown block:\n---\n{json_string_to_parse}\n---")
            else:
                print(f"DEBUG: No markdown block found. Attempting to parse raw stripped text as JSON.")

            first_bracket = json_string_to_parse.find('[')
            last_bracket = json_string_to_parse.rfind(']')

            if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
                json_string_to_parse = json_string_to_parse[first_bracket : last_bracket + 1]
                print(f"DEBUG: Refined JSON string to array boundaries:\n---\n{json_string_to_parse}\n---")
            else:
                print(f"DEBUG: Could not find valid array boundaries. Parsing existing string as is.")

            return json.loads(json_string_to_parse)
        except Exception as e:
            print(f"ERROR: Error calling Scaleway API for intent parsing: {e}")
            return [{"action": "clarify", "prompt": f"Sorry, I'm having trouble with the Scaleway LLM service for intent parsing: {e}"}]

    def generate_response(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_CHAT},
            {"role": "user", "content": prompt}
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=Config.LLM_TEMPERATURE,
                top_p=Config.LLM_TOP_P,
                max_tokens=Config.LLM_MAX_TOKENS,
                presence_penalty=Config.LLM_PRESENCE_PENALTY, 
                frequency_penalty=Config.LLM_FREQUENCY_PENALTY, 
                stream=False, # Keeping False for compatibility
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"ERROR: Error calling Scaleway API for chat response: {e}")
            return f"I apologize, but I'm having trouble generating a response right now with Scaleway: {e}"

