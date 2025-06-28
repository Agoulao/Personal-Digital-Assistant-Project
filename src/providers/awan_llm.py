import json
import requests
import re
# Import BASE_SYSTEM_PARSER and SYSTEM_CHAT directly from llm_client as they are defined there
from llm_client import LLMClient, SYSTEM_CHAT, BASE_SYSTEM_PARSER
from config import Config 

class AwanLLMClient(LLMClient):
    """LLMClient implementation for Awan LLM API."""

    def __init__(self, api_url: str, api_key: str, model: str):
        self.api_url = api_url
        self.api_key = api_key
        self.base_params = {
            "model": model,
            "temperature": Config.LLM_TEMPERATURE,
            "top_p": Config.LLM_TOP_P,
            "top_k": Config.LLM_TOP_K,
            "max_tokens": Config.LLM_MAX_TOKENS,
            "stream": False, # Keeping False as current parsing logic expects non-streaming
            "repetition_penalty": 1.1 
        }

    def parse_intents(self, user_input: str, last_filename: str | None = None, available_actions_prompt: str = "") -> list[dict]:
        json_string_to_parse = "" # Initialize for error messages
        
        # Build the full system parser prompt dynamically, including base rules,
        # available actions, and last remembered filename.
        full_system_parser_prompt = BASE_SYSTEM_PARSER
        
        if available_actions_prompt:
            # The available_actions_prompt already contains its own headers (e.g., "--- Currently Available Automation Actions ---")
            full_system_parser_prompt += available_actions_prompt

        if last_filename:
            full_system_parser_prompt += f"\n\nLAST_REMEMBERED_FILE: {last_filename}"

        payload = {
            **self.base_params,
            "messages": [
                {"role": "system", "content": full_system_parser_prompt}, # Use dynamically built prompt
                {"role": "user",   "content": user_input}
            ]
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            res = requests.post(self.api_url, headers=headers, json=payload)
            res.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            raw_response_text = res.json()["choices"][0]["message"]["content"]
            print(f"DEBUG: Raw response text from Awan API:\n---\n{raw_response_text}\n---")

            json_string_to_parse = raw_response_text.strip()

            # Strategy 1: Attempt to extract content from a markdown code block (most common case)
            match = re.search(r"```(?:\w+)?\s*(.*?)\s*```", json_string_to_parse, re.DOTALL)
            
            if match:
                json_string_to_parse = match.group(1).strip()
                print(f"DEBUG: Extracted JSON string from markdown block:\n---\n{json_string_to_parse}\n---")
            else:
                print(f"DEBUG: No markdown block found. Attempting to parse raw stripped text as JSON.")

            # Strategy 2: Further refine by finding the outermost JSON array boundaries '[' and ']'
            first_bracket = json_string_to_parse.find('[')
            last_bracket = json_string_to_parse.rfind(']')

            if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
                json_string_to_parse = json_string_to_parse[first_bracket : last_bracket + 1]
                print(f"DEBUG: Refined JSON string to array boundaries:\n---\n{json_string_to_parse}\n---")
            else:
                print(f"DEBUG: Could not find valid array boundaries. Parsing existing string as is.")

            return json.loads(json_string_to_parse)
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network or API request error with Awan LLM: {e}")
            return [{"action": "clarify", "prompt": "Sorry, I'm having trouble connecting to the Awan LLM service."}]
        except json.JSONDecodeError as e:
            print(f"ERROR: JSONDecodeError. The string that caused the error was:\n---\n{json_string_to_parse}\n---")
            print(f"ERROR: JSONDecodeError details: {e}")
            return [{"action": "clarify", "prompt": "Sorry, I couldn't parse the model's response. Can you rephrase?"}]
        except Exception as e:
            print(f"ERROR: General exception calling Awan LLM API for intent parsing: {e}")
            return [{"action": "clarify", "prompt": "Sorry, I had an issue understanding that command."}]

    def generate_response(self, prompt: str) -> str:
        payload = {
            **self.base_params,
            "messages": [
                {"role": "system", "content": SYSTEM_CHAT}, # Use SYSTEM_CHAT from llm_client
                {"role": "user",   "content": prompt}
            ]
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        try:
            res = requests.post(self.api_url, headers=headers, json=payload)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            print(f"Error calling Awan LLM API for chat response: {e}")
            return "I apologize, but I'm having trouble generating a response right now."
        except Exception as e:
            print(f"Error processing Awan LLM chat response: {e}")
            return "I apologize, but I'm having trouble generating a response right now."
