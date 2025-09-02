# llm/providers/gemini_llm.py
import json
from typing import List, Dict, Optional

from openai import OpenAI

from llm.llm_client import LLMClient, BASE_SYSTEM_PARSER, SYSTEM_CHAT
from config import Config


class GeminiLLMClient(LLMClient):
    """
    Gemini client using Google's OpenAI-compatible endpoint.

    - Uses OpenAI Python SDK pointed at Google's Gemini base URL.
    - Sends system rules via the first system message.
    - Uses chat.completions for both intent parsing and chat responses.
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=Config.GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.model = Config.GEMINI_MODEL
        
        # Generation defaults mapped from config
        # Note: OpenAI-compatible API doesn't support top_k; it is omitted.
        self.temperature = getattr(Config, "LLM_TEMPERATURE", 0.2)
        self.top_p = getattr(Config, "LLM_TOP_P", 0.95)
        self.max_tokens = getattr(Config, "LLM_MAX_TOKENS", 1024)
    
    # ---- Intent parsing -----------------------------------------------------

    def parse_intents(
        self,
        user_input: str,
        available_actions_prompt: str = ""
    ) -> List[Dict]:
        """
        Ask the model to return ONLY a JSON array of intents.
        Rules are provided via system message (BASE_SYSTEM_PARSER + dynamic actions).
        """
        # Build the system prompt: rules + dynamic actions
        system_instruction = BASE_SYSTEM_PARSER
        if available_actions_prompt:
            system_instruction += available_actions_prompt

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=Config.LLM_TEMPERATURE,
                top_p=Config.LLM_TOP_P,
                max_tokens=Config.LLM_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_input},
                ],
            )

            raw = (completion.choices[0].message.content or "").strip()
            intents = self._extract_json_from_response(raw)

            # Validate minimal schema (raises ValueError on issues)
            self._validate_intents_schema(intents)
            return intents

        except (json.JSONDecodeError, ValueError) as e:
            # If parsing/validation fails, fall back to a neutral, safe intent.
            print(f"ERROR: JSON parsing/validation error (Gemini/OpenAI compat): {e}")
            return [{"action": "none"}]
        except Exception as e:
            print(f"ERROR: Gemini/OpenAI-compat intent call failed: {e}")
            return [{"action": "none"}]

    # ---- General chat / reply generation -----------------------------------

    def generate_response(
        self,
        prompt: str,
        history: Optional[List[Dict]] = None,
        system_prompt: str = SYSTEM_CHAT,
    ) -> str:
        """
        Generate a natural-language reply.
        History is mapped to role-based messages; rules go in system message.
        """
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if history:
            # history: [{"role": "user"|"assistant", "content": "..."}]
            for turn in history:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        # Current user message
        messages.append({"role": "user", "content": prompt})

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=Config.LLM_TEMPERATURE,
                top_p=Config.LLM_TOP_P,
                max_tokens=Config.LLM_MAX_TOKENS,
                messages=messages,
            )
            return (completion.choices[0].message.content or "").strip()

        except Exception as e:
            print(f"ERROR: Gemini/OpenAI-compat chat call failed: {e}")
            return "I'm having trouble generating a response right now."
