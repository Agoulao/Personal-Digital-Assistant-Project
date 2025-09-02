import json
from abc import ABC, abstractmethod
from config import Config
import re

# ─── Shared Prompts ────────────────────────────────────────────────────────────
# This is the base system chat prompt that describes the assistant's capabilities.
# It will be dynamically updated with module capabilities after loading modules.
SYSTEM_CHAT = (
    "You are a helpful conversational AI assistant. "
    "You can assist users with various tasks by automating actions on their system."
)

# This variable will store the dynamically generated capabilities string
_dynamic_capabilities_text = ""

def update_system_chat_capabilities(capabilities_list: list[str]):
    """
    Updates the global _dynamic_capabilities_text based on the list of module descriptions.
    This function should be called by the backend after loading modules.
    """
    global _dynamic_capabilities_text
    if capabilities_list:
        # Join descriptions into a readable sentence or list
        # Example: "I can manage your emails, handle Google Calendar events, and provide meteorological information."
        _dynamic_capabilities_text = " Specifically, I can " + ", and ".join(capabilities_list) + "."
    else:
        _dynamic_capabilities_text = ""

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

**Ambiguity** If the user's request is purely conversational, emit:
  `[{"action":"none"}]`    

---
Your response MUST be a valid JSON array. Do NOT include any other text, explanations, or markdown outside the JSON array.
"""

#   - When an example uses a placeholder (e.g., "DIRECTORY", "FILENAME"), you must replace that placeholder with the actual value provided by the user in their instruction.

# ─── LLMClient Interface ───────────────────────────────────────────────────────
class LLMClient(ABC):
    """Abstract interface for chat + intent parsing."""

    @abstractmethod
    def parse_intents(self, user_input: str, available_actions_prompt: str = "") -> list[dict]:
        """
        Return a list of intent dicts given the user input.
        """
        pass

    @abstractmethod
    def generate_response(self, prompt: str, history: list[dict] = None, system_prompt: str = SYSTEM_CHAT) -> str:
        """
        Return a conversational reply given the prompt and optional conversation history.
        History is a list of {"role": "user"|"assistant", "content": "..."} dicts.
        """
        pass

    def _validate_intents_schema(self, intents: list[dict]):
        """
        Validates the structure of the parsed intents.
        Raises ValueError if the schema is not as expected.
        """
        if not isinstance(intents, list):
            raise ValueError("Parsed intents must be a list.")
        for intent in intents:
            if not isinstance(intent, dict):
                raise ValueError("Each intent in the list must be a dictionary.")
            if "action" not in intent:
                raise ValueError("Each intent dictionary must contain an 'action' key.")

    def _extract_json_from_response(self, raw_response_text: str) -> list[dict]:
        """
        Helper method to robustly extract and parse a JSON array from a raw LLM text response.
        It handles markdown code blocks, finds outermost array boundaries, and validates the structure.
        Returns a list of dictionaries. Returns an empty list if no valid JSON can be extracted.
        """
        json_string_to_parse = raw_response_text.strip()
        print(f"DEBUG: Raw response text for JSON extraction:\n---\n{raw_response_text}\n---")

        # Strategy 1: Attempt to extract content from a markdown code block (most common case)
        match = re.search(r"```(?:\w+)?\s*(.*?)\s*```", json_string_to_parse, re.DOTALL)
        
        if match:
            json_string_to_parse = match.group(1).strip()
            print(f"DEBUG: Extracted JSON string from markdown block:\n---\n{json_string_to_parse}\n---")
        else:
            print(f"DEBUG: No markdown block found. Checking for array boundaries.")

        # Strategy 2: Attempt to parse the entire string directly as JSON first
        try:
            parsed_json = json.loads(json_string_to_parse)
            if isinstance(parsed_json, dict):
                print(f"DEBUG: Parsed as single JSON object. Wrapping in list.")
                return [parsed_json]
            elif isinstance(parsed_json, list):
                print(f"DEBUG: Parsed as JSON array.")
                return parsed_json
            else:
                print(f"DEBUG: Parsed JSON is neither dict nor list ({type(parsed_json)}). Returning empty list.")
                return []
        except json.JSONDecodeError:
            print(f"DEBUG: Direct JSON parse failed. Attempting array boundary refinement.")
            pass # Continue to the next strategy if direct parse fails

        # Strategy 3: Further refine by finding the outermost JSON array boundaries '[' and ']'
        first_bracket = json_string_to_parse.find('[')
        last_bracket = json_string_to_parse.rfind(']')

        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            json_string_to_parse = json_string_to_parse[first_bracket : last_bracket + 1]
            print(f"DEBUG: Refined JSON string to array boundaries:\n---\n{json_string_to_parse}\n---")
        else:
            print(f"DEBUG: Could not find valid array boundaries. Attempting to parse raw string if it looks like JSON.")
            # If no array boundaries, it might be a single object not in markdown.
            # Try parsing the original string again as a single object if it wasn't already tried successfully.
            try:
                parsed_json = json.loads(raw_response_text.strip())
                if isinstance(parsed_json, dict):
                    print(f"DEBUG: Parsed as single JSON object after boundary check. Wrapping in list.")
                    return [parsed_json]
                else:
                    print(f"DEBUG: Parsed JSON is not a dict or list after boundary check. Returning empty list.")
                    return []
            except json.JSONDecodeError:
                print(f"DEBUG: Final JSON parse attempt failed. Returning empty list.")
                return [] # Return empty list if no valid JSON can be extracted
            except Exception as e:
                print(f"DEBUG: Unexpected error during final JSON parse attempt: {e}. Returning empty list.")
                return []


        try:
            # Attempt to load JSON. If it fails, this block will catch it.
            parsed_json = json.loads(json_string_to_parse)

            # Ensure the output is always a list of dictionaries
            if isinstance(parsed_json, dict):
                parsed_json = [parsed_json]
            elif not isinstance(parsed_json, list):
                # If it's not a dict or list, it's not the expected action format
                print(f"DEBUG: LLM returned unexpected JSON type: {type(parsed_json)}. Expected dict or list. Returning empty list.")
                return []
            
            return parsed_json
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSONDecodeError during parsing: {e}. Returning empty list.")
            return [] # Return empty list if JSON parsing fails
        except Exception as e:
            print(f"DEBUG: Unexpected error during JSON extraction: {e}. Returning empty list.")
            return [] # Catch any other unexpected errors during extraction

# ─── Factory & Module-Level API ────────────────────────────────────────────────
def get_llm_client() -> LLMClient:
    provider = Config.LLM_PROVIDER.lower()
    if provider == "awan":
        from llm.providers.awan_llm import AwanLLMClient
        return AwanLLMClient(
            api_url = Config.AWAN_API_URL,
            api_key = Config.AWAN_API_KEY,
            model   = Config.AWAN_MODEL_NAME
        )
    elif provider == "gemini":
        from llm.providers.gemini_llm import GeminiLLMClient
        return GeminiLLMClient()
    elif provider == "novita":
        from llm.providers.novita_llm import NovitaLLMClient
        return NovitaLLMClient(
            api_url = Config.NOVITA_API_URL,
            api_key = Config.NOVITA_API_KEY,
            model   = Config.NOVITA_MODEL_NAME,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {Config.LLM_PROVIDER}")

# Singleton instance
_client = get_llm_client()

# parse_intents and generate_response pass through the client method
def parse_intents(user_input: str, available_actions_prompt: str = "") -> list[dict]:
    # Pass all relevant context to the client's method
    return _client.parse_intents(user_input, available_actions_prompt)

def generate_response(prompt: str, history: list[dict] = None) -> str:
    # Concatenate the base SYSTEM_CHAT with the dynamic capabilities text
    full_system_chat_prompt = SYSTEM_CHAT + _dynamic_capabilities_text
    # Pass the full_system_chat_prompt to the client's generate_response method
    return _client.generate_response(prompt, history, full_system_chat_prompt)

