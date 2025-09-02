import json
import requests
import re
from llm.llm_client import LLMClient, SYSTEM_CHAT, BASE_SYSTEM_PARSER
from config import Config 

class AwanLLMClient(LLMClient):
    """LLMClient implementation for Awan LLM API."""

    def __init__(self, api_url: str, api_key: str, model: str):
        super().__init__() # Call the constructor of the base class
        self.api_url = api_url
        self.api_key = api_key
        self.base_params = {
            "model": model,
            "temperature": Config.LLM_TEMPERATURE,
            "top_p": Config.LLM_TOP_P,
            "top_k": Config.LLM_TOP_K,
            "max_tokens": 1000,
            "stream": False, # Keeping False as current parsing logic expects non-streaming
            "repetition_penalty": 1.1 
        }

    def parse_intents(self, user_input: str, available_actions_prompt: str = "") -> list[dict]:
        
        # Build the full system parser prompt dynamically, including base rules,
        # available actions
        full_system_parser_prompt = BASE_SYSTEM_PARSER
        
        if available_actions_prompt:
            # The available_actions_prompt already contains its own headers (e.g., "--- Currently Available Automation Actions ---")
            full_system_parser_prompt += available_actions_prompt

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
            
            # Use the shared helper method from the base class to extract and parse JSON
            parsed_json = self._extract_json_from_response(raw_response_text)

            # Check if parsed_json is empty (meaning no valid JSON was extracted)
            if not parsed_json:
                print("DEBUG: _extract_json_from_response returned an empty list. Assuming no action was intended.")
                # If no JSON was extracted, it likely means the LLM responded conversationally
                # or failed to follow the JSON format. Return "none" action.
                return [{"action": "none"}]

            self._validate_intents_schema(parsed_json) # Validate the schema of the parsed JSON using base class method
            return parsed_json
        except (json.JSONDecodeError, ValueError) as e:
            # Catch both JSON parsing errors and custom ValueError from _extract_json_from_response or _validate_intents_schema
            print(f"ERROR: JSON parsing or validation error for Awan LLM: {e}")
            return [{"action": "None"}]
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network or API request error with Awan LLM: {e}")
            return [{"action": "None"}]
        except Exception as e:
            print(f"ERROR: General exception calling Awan LLM API for intent parsing: {e}")
            return [{"action": "None"}]

    def generate_response(self, prompt: str, history: list[dict] = None, system_prompt: str = SYSTEM_CHAT) -> str:
        # Construct messages payload, including history if provided
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            # Append previous conversation turns
            for turn in history:
                # Ensure parts is a list of strings/dicts, not just a string
                content_part = turn["content"]
                if isinstance(content_part, str):
                    messages.append({"role": turn["role"], "content": content_part})
                elif isinstance(content_part, list): # If content is already a list of parts
                    # Awan API expects 'content' to be a string, so flatten parts if necessary
                    # For simplicity, join parts into a single string for Awan if it's a list
                    messages.append({"role": turn["role"], "content": " ".join(str(p) for p in content_part)})
                else:
                    messages.append({"role": turn["role"], "content": str(content_part)}) # Fallback for other types

        # Add the current user prompt
        messages.append({"role": "user", "content": prompt})

        payload = {
            **self.base_params,
            "messages": messages
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

