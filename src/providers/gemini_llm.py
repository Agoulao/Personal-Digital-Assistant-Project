import json
import google.generativeai as genai
from llm_client import LLMClient, BASE_SYSTEM_PARSER, SYSTEM_CHAT
from config import Config
import re

class GeminiLLMClient(LLMClient):
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.client = genai.GenerativeModel(
            model_name=Config.GEMINI_MODEL,
            generation_config=genai.types.GenerationConfig(
                temperature=Config.LLM_TEMPERATURE,
                top_p=Config.LLM_TOP_P,
                top_k=Config.LLM_TOP_K,
                max_output_tokens=Config.LLM_MAX_TOKENS,
            )
        )

    def parse_intents(self, user_input: str, last_filename: str | None = None, available_actions_prompt: str = "") -> list[dict]:
        json_string_to_parse = "" # Initialize for error messages
        
        # Build the full system parser prompt dynamically
        full_system_parser_prompt = BASE_SYSTEM_PARSER # Start with the base static rules
        
        # Append dynamic actions and their examples provided by the Backend
        if available_actions_prompt:
            full_system_parser_prompt += available_actions_prompt # This already includes headers and formatting

        # Append last_filename for coreference
        if last_filename:
            full_system_parser_prompt += f"\n\nLAST_REMEMBERED_FILE: {last_filename}"

        try:
            response = self.client.generate_content(
                contents=[
                    {"role": "user", "parts": [full_system_parser_prompt]}, # Use the full, dynamic prompt
                    {"role": "user", "parts": [user_input]}
                ]
            )
            
            raw_response_text = response.text
            print(f"DEBUG: Raw response text from Gemini API:\n---\n{raw_response_text}\n---")

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
        except json.JSONDecodeError as e:
            print(f"ERROR: JSONDecodeError. The string that caused the error was:\n---\n{json_string_to_parse}\n---")
            print(f"ERROR: JSONDecodeError details: {e}")
            return [{"action": "clarify", "prompt": "Sorry, I couldn't parse the model's response. Can you rephrase?"}]
        except Exception as e:
            print(f"ERROR: General exception calling Gemini API for intent parsing: {e}")
            return [{"action": "clarify", "prompt": "Sorry, I had an issue understanding that command."}]

    def generate_response(self, prompt: str) -> str:
        try:
            response = self.client.generate_content(
                contents=[
                    {"role": "user", "parts": [SYSTEM_CHAT]},
                    {"role": "user", "parts": [prompt]}
                ]
            )
            return response.text
        except Exception as e:
            print(f"Error calling Gemini API for chat response: {e}")
            return "I apologize, but I'm having trouble generating a response right now."
