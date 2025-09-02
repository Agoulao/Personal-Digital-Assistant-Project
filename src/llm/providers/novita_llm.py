import json
import requests
import re
from llm.llm_client import LLMClient, BASE_SYSTEM_PARSER, SYSTEM_CHAT
from config import Config

class NovitaLLMClient(LLMClient):
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

    def parse_intents(self, user_input: str, available_actions_prompt: str = "") -> list[dict]:
        
        full_system_parser_prompt = BASE_SYSTEM_PARSER 
        if available_actions_prompt:
            full_system_parser_prompt += available_actions_prompt

        messages = [
            {"role": "system", "content": full_system_parser_prompt},
            {"role": "user", "content": user_input}
        ]

        payload = self._prepare_payload(messages, is_intent_parsing=True)
        
        try:
            res = requests.post(self.api_url, headers=self.headers, json=payload, timeout=Config.LLM_REQUEST_TIMEOUT)
            res.raise_for_status()
            
            raw_response_text = res.json()["choices"][0]["message"]["content"]
            
            # Use the shared helper method to extract and parse JSON
            parsed_json = self._extract_json_from_response(raw_response_text)
            
            # This specific check for missing/None 'action' key can remain here
            # as it's a final validation specific to intent parsing structure.
            if not parsed_json or not isinstance(parsed_json[0], dict) or parsed_json[0].get("action") is None:
                print(f"DEBUG: Triggering clarify action due to missing/None 'action' key in LLM response.")
                return [{"action": "None"}]

            return parsed_json

        except (json.JSONDecodeError, ValueError) as e:
            # Catch both JSON parsing errors and custom ValueError from _extract_json_from_response
            print(f"ERROR: JSON parsing or validation error for Novita AI LLM: {e}")
            return [{"action": "None"}]
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network or API request error with Novita AI LLM: {e}")
            return [{"action": "None"}]
        except Exception as e:
            print(f"ERROR: General exception calling Novita AI LLM API for intent parsing: {e}")
            return [{"action": "None"}]

    def generate_response(self, prompt: str, history: list[dict] = None, system_prompt: str = SYSTEM_CHAT) -> str:
        # Construct messages payload, including history if provided
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            # Append previous conversation turns
            for turn in history:
                messages.append({"role": turn["role"], "content": turn["content"]})
        
        # Add the current user prompt
        messages.append({"role": "user", "content": prompt})

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
