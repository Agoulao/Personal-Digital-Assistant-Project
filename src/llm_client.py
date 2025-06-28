import json
from abc import ABC, abstractmethod
from config import Config
import re

# ─── Shared Prompts ────────────────────────────────────────────────────────────
SYSTEM_CHAT = (
    "You are a helpful conversational AI assistant."
)

# BASE_SYSTEM_PARSER - contains ONLY general rules and meta-instructions.
# Specific action definitions and examples will be provided dynamically by the Backend.
BASE_SYSTEM_PARSER = """
You are an automation parser. Given a user instruction, return *only* a JSON array
of action objects.

**Current Date Context:** If the backend provides a `CURRENT_DATE_CONTEXT` in the input, use this as the current date for all relative time calculations (e.g., "today", "this week", "next month", "this year").

**Date and Time Formatting Rule:** For any date or time-related parameters (e.g., `start_time`, `end_time`, `time_period`), you MUST convert natural language into ISO 8601 format.
  - For specific date and time: `YYYY-MM-DDTHH:MM:SS` (e.g., `2025-07-10T15:30:00` for 3:30 PM local time on July 10, 2025). If the user specifies a timezone, use that timezone. Otherwise, assume the local timezone provided in `CURRENT_CONTEXT`.
  - For all-day dates or date ranges: `YYYY-MM-DD` (e.g., `2025-07-10`).
  - For periods like "this year", "this week", "July", you should derive the appropriate `YYYY-MM-DD` start and end dates for the `time_period` parameter. For "this year", use `YYYY-01-01` to `YYYY-12-31`. For "this week", use the `Current Week (Monday-Sunday)` value from `CURRENT_CONTEXT`. For "next week", use the `Next Week (Monday-Sunday)` value from `CURRENT_CONTEXT`. For a month like "July", you should derive `YYYY-07-01` to `YYYY-07-31`.

**Action Selection and Parameter Handling:**
  - You MUST strictly select an action from the list provided by the backend (which follows this prompt).
  - You MUST map the user's input to the *exact* parameter names specified in the examples for each action.
  - When an example uses a placeholder (e.g., "DIRECTORY", "FILENAME"), you must replace that placeholder with the actual value provided by the user in their instruction.
  - Do NOT invent new actions or parameters. If a user's request doesn't clearly map to an existing action and its parameters, use the "clarify" action.

**Coreference & Defaults** If the user says “it”, “that file”, or “the file” without naming it, bind **filename** to the last remembered file in memory. If the backend provides a `LAST_REMEMBERED_FILE` in the input,
  use that value as the 'last remembered file.'
  If multiple files exist and you cannot confidently pick one, emit:
  `[{"action":"clarify_file","prompt":"Which file did you mean? Please specify the filename."}]`

**Ambiguity** If the user's request is purely conversational, emit:
  `[{"action":"none"}]`  

**Clarification** If you are uncertain whether to chat or to automate, emit:
  `[{"action":"clarify","prompt":"Did you want me to run a command or just chat?"}]`  

**Crucial Instruction for write_file:** When the user asks to write content that needs generation (e.g., a recipe, an essay, an introduction), directly generate that content and place it into the "content" field. The examples for generated content (like "A complete, detailed cheesecake recipe") are illustrative and describe the *type* of content expected, not literal text to be outputted.

---
Your response MUST be a valid JSON array. Do NOT include any other text, explanations, or markdown outside the JSON array.
"""

# ─── LLMClient Interface ───────────────────────────────────────────────────────
class LLMClient(ABC):
    """Abstract interface for chat + intent parsing."""

    @abstractmethod
    def parse_intents(self, user_input: str, last_filename: str | None = None, available_actions_prompt: str = "") -> list[dict]:
        """
        Return a list of intent dicts given the user input.
        Includes last_filename for coreference and available_actions_prompt for dynamic capabilities.
        """
        pass

    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        """Return a conversational reply given the prompt."""
        pass

# ─── Factory & Module-Level API ────────────────────────────────────────────────
def get_llm_client() -> LLMClient:
    provider = Config.LLM_PROVIDER.lower()
    if provider == "awan":
        from providers.awan_llm import AwanLLMClient
        return AwanLLMClient(
            api_url = Config.AWAN_API_URL,
            api_key = Config.AWAN_API_KEY,
            model   = Config.AWAN_MODEL_NAME
        )
    elif provider == "gemini":
        from providers.gemini_llm import GeminiLLMClient
        return GeminiLLMClient()
    elif provider == "huggingface":
        from providers.huggingface_llm import HuggingFaceLLMClient
        return HuggingFaceLLMClient(
            api_url = Config.HUGGINGFACE_API_URL,
            api_key = Config.HUGGINGFACE_API_KEY,
            model   = Config.HUGGINGFACE_MODEL_NAME,
            # Removed provider_name as it's not used with direct requests
        )
    elif provider == "scaleway":
        from providers.scaleway_llm import ScalewayLLMClient
        return ScalewayLLMClient() # ScalewayLLMClient initializes with Config directly    
    else:
        raise ValueError(f"Unsupported LLM provider: {Config.LLM_PROVIDER}")

# Singleton instance
_client = get_llm_client()

# parse_intents and generate_response pass through the client method
def parse_intents(user_input: str, last_filename: str | None = None, available_actions_prompt: str = "") -> list[dict]:
    # Pass all relevant context to the client's method
    return _client.parse_intents(user_input, last_filename, available_actions_prompt)

def generate_response(prompt: str) -> str:
    return _client.generate_response(prompt)
