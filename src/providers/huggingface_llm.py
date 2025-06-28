import json
import requests
import re
from llm_client import LLMClient, BASE_SYSTEM_PARSER, SYSTEM_CHAT
from config import Config

class HuggingFaceLLMClient(LLMClient):
    """LLMClient implementation for Hugging Face Inference API via Novita AI using direct requests."""

    def __init__(self, api_url: str, api_key: str, model: str, provider_name: str = None):
        self.api_url = api_url
        self.api_key = api_key
        self.model_name = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _prepare_payload(self, messages: list[dict], is_intent_parsing: bool = False) -> dict:
        """Prepares the common payload structure for Novita AI."""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": Config.LLM_TEMPERATURE,
            "top_p": Config.LLM_TOP_P,
            "top_k": Config.LLM_TOP_K,
            "max_tokens": Config.LLM_MAX_TOKENS,
            "repetition_penalty": Config.LLM_REPETITION_PENALTY,
            "min_p": Config.LLM_MIN_P,
            "presence_penalty": Config.LLM_PRESENCE_PENALTY,
            "frequency_penalty": Config.LLM_FREQUENCY_PENALTY,
            "stream": False, # Keep as False for current parsing logic
        }
        
        payload["response_format"] = {"type": "text"} 
        
        return payload

    def parse_intents(self, user_input: str, last_filename: str | None = None, available_actions_prompt: str = "") -> list[dict]:
        json_string_to_parse = ""
        
        full_system_parser_prompt = BASE_SYSTEM_PARSER 
        if available_actions_prompt:
            full_system_parser_prompt += available_actions_prompt
        if last_filename:
            full_system_parser_prompt += f"\n\nLAST_REMEMBERED_FILE: {last_filename}"

        messages = [
            {"role": "system", "content": full_system_parser_prompt},
            {"role": "user", "content": user_input}
        ]

        payload = self._prepare_payload(messages, is_intent_parsing=True)
        
        try:
            res = requests.post(self.api_url, headers=self.headers, json=payload, timeout=Config.LLM_REQUEST_TIMEOUT)
            res.raise_for_status()
            
            raw_response_text = res.json()["choices"][0]["message"]["content"]
            print(f"DEBUG: Raw response text from Novita AI:\n---\n{raw_response_text}\n---")

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

            # Attempt to extract array if explicit brackets are found
            if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
                json_string_to_parse = json_string_to_parse[first_bracket : last_bracket + 1]
                print(f"DEBUG: Refined JSON string to array boundaries:\n---\n{json_string_to_parse}\n---")
            else:
                print(f"DEBUG: Could not find valid array boundaries. Parsing existing string as is.")

            parsed_json = json.loads(json_string_to_parse)
            
            # Ensure the output is always a list of dictionaries
            if isinstance(parsed_json, dict):
                parsed_json = [parsed_json]
            elif not isinstance(parsed_json, list):
                # If it's neither a dict nor a list (unexpected), return a clarify action
                print(f"ERROR: LLM returned unexpected JSON type: {type(parsed_json)}. Expected dict or list.")
                return [{"action": "clarify", "prompt": "Sorry, the model's response was not in the expected format."}]
            
            if not parsed_json or not isinstance(parsed_json[0], dict) or parsed_json[0].get("action") is None:
                print(f"DEBUG: Triggering clarify action due to missing/None 'action' key in LLM response.") # Added debug print
                return [{"action": "clarify", "prompt": "Sorry, I couldn't determine a valid action from your request. Can you rephrase?"}]

            return parsed_json

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network or API request error with Novita AI LLM: {e}")
            return [{"action": "clarify", "prompt": "Sorry, I'm having trouble connecting to the Novita AI LLM service."}]
        except json.JSONDecodeError as e:
            print(f"ERROR: JSONDecodeError. The string that caused the error was:\n---\n{json_string_to_parse}\n---")
            print(f"ERROR: JSONDecodeError details: {e}")
            return [{"action": "clarify", "prompt": "Sorry, I couldn't parse the model's response. Can you rephrase?"}]
        except Exception as e:
            print(f"ERROR: General exception calling Novita AI LLM API for intent parsing: {e}")
            return [{"action": "clarify", "prompt": "Sorry, I had an issue understanding that command."}]

    def generate_response(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_CHAT},
            {"role": "user", "content": prompt}
        ]
        payload = self._prepare_payload(messages)

        try:
            res = requests.post(self.api_url, headers=self.headers, json=payload, timeout=Config.LLM_REQUEST_TIMEOUT)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            print(f"Error calling Novita AI LLM API for chat response: {e}")
            return "I apologize, but I'm having trouble generating a response right now."
        except Exception as e:
            print(f"Error processing Novita AI LLM chat response: {e}")
            return "I apologize, but I'm having trouble generating a response right now."
