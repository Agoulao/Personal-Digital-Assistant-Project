import json
import os
import importlib
import datetime # date/time operations
import pytz # timezone handling
from dateutil.relativedelta import relativedelta # date calculations

from llm_client import parse_intents, generate_response, BASE_SYSTEM_PARSER
from modules.system_automation import SystemAutomation
from modules.base_automation import BaseAutomationModule

class Backend:
    def __init__(self, voice_module=None, tts_module=None):
        self.voice = voice_module
        self.tts = tts_module
        self.last_filename = None

        self.automation_modules = []
        # Maps action name to (module_instance, method_name, description, example_json)
        self.supported_actions_map = {} 
        self.load_automation_modules() 

        self._update_system_parser_with_actions() 
        self.local_tz = pytz.timezone('Europe/Lisbon') # Initialize local timezone

    def load_automation_modules(self):
        """
        Discovers and loads all automation modules from the 'modules' directory.
        """
        modules_dir = os.path.join(os.path.dirname(__file__), 'modules')
        if not os.path.exists(modules_dir):
            print(f"WARNING: Modules directory '{modules_dir}' not found.")
            return

        for filename in os.listdir(modules_dir):
            if filename.endswith('_automation.py') and filename != 'base_automation.py':
                module_name = filename[:-3] # Remove .py extension
                try:
                    module = importlib.import_module(f"modules.{module_name}")
                    
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BaseAutomationModule) and attr is not BaseAutomationModule:
                            module_instance = attr()
                            self.automation_modules.append(module_instance)
                            
                            # Collect supported actions with their details
                            for action_name, details in module_instance.get_supported_actions().items():
                                if action_name in self.supported_actions_map:
                                    print(f"WARNING: Duplicate action '{action_name}' found. First module takes precedence.")
                                self.supported_actions_map[action_name] = (
                                    module_instance, 
                                    details["method_name"], 
                                    details["description"], 
                                    details["example_json"]
                                )
                            print(f"INFO: Loaded automation module: {module_name} ({module_instance.get_description()})")
                            break
                except Exception as e:
                    print(f"ERROR: Failed to load automation module '{module_name}': {e}")

        if not self.automation_modules:
            print("WARNING: No automation modules loaded. Only chat functionality will be available.")

    def _update_system_parser_with_actions(self):
        """
        Generates a dynamic part for SYSTEM_PARSER based on loaded modules,
        describing all available actions to the LLM with examples.
        This string will be passed to the parse_intents function.
        """
        action_prompt_parts = []
        action_prompt_parts.append("\n--- Currently Available Automation Actions ---")
        action_prompt_parts.append("Each action has a specific JSON format. Here are the details and examples:")

        # Sort modules by name for consistent prompt generation
        sorted_modules = sorted(self.automation_modules, key=lambda m: m.get_description())

        for module in sorted_modules:
            action_prompt_parts.append(f"\n**Module: {module.get_description()}**")
            
            # Sort actions by name within each module for consistent prompt generation
            sorted_actions = sorted(module.get_supported_actions().items(), key=lambda item: item[0])

            for action_name, details in sorted_actions:
                action_prompt_parts.append(f"  • **{action_name}**: {details['description']}")
                action_prompt_parts.append(f"    Example: `{details['example_json']}`")
        
        self.all_supported_actions_list_for_llm = "\n".join(action_prompt_parts)


    def process_command(self, user_text: str) -> str:
        # Get current date and time in local timezone for the LLM
        now_local = datetime.datetime.now(self.local_tz)
        current_date_time_str = now_local.isoformat(timespec='seconds').split('+')[0] # YYYY-MM-DDTHH:MM:SS (local time)
        current_date_str = now_local.strftime('%Y-%m-%d') # YYYY-MM-DD
        current_year_str = str(now_local.year) # YYYY
        
        # Calculate start of current week (Monday) and end of week (Sunday)
        start_of_week = now_local - datetime.timedelta(days=now_local.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)
        current_week_range_str = f"{start_of_week.strftime('%Y-%m-%d')}/{end_of_week.strftime('%Y-%m-%d')}"

        # Calculate start and end of next week (Monday-Sunday)
        next_week_start = start_of_week + datetime.timedelta(weeks=1)
        next_week_end = end_of_week + datetime.timedelta(weeks=1)
        next_week_range_str = f"{next_week_start.strftime('%Y-%m-%d')}/{next_week_end.strftime('%Y-%m-%d')}"

        # Calculate start and end of current month
        start_of_month = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_of_month = (start_of_month + relativedelta(months=1) - datetime.timedelta(microseconds=1))
        current_month_range_str = f"{start_of_month.strftime('%Y-%m-%d')}/{end_of_month.strftime('%Y-%m-%d')}"

        # Construct the current context string for the LLM
        current_context_for_llm = (
            f"\n\n--- CURRENT CONTEXT ---\n"
            f"Current Date and Time (Local): {current_date_time_str}\n"
            f"Current Date (Local): {current_date_str}\n"
            f"Current Year: {current_year_str}\n"
            f"Current Week (Monday-Sunday): {current_week_range_str}\n"
            f"Next Week (Monday-Sunday): {next_week_range_str}\n"
            f"Current Month: {current_month_range_str}\n"
            f"Local Timezone: {str(self.local_tz)}\n"
            f"-------------------------"
        )

        try:
            intents = parse_intents(
                user_text, 
                last_filename=self.last_filename,
                available_actions_prompt=self.all_supported_actions_list_for_llm + current_context_for_llm # Add current context here
            )
        except Exception as e:
            print(f"Error parsing intents: {e}")
            return "Sorry, I didn't understand. Did you want me to run a command or chat?"

        if intents and intents[0].get("action") == "clarify":
            return intents[0].get("prompt", "Could you clarify your intent?")
        elif intents and intents[0].get("action") == "clarify_file":
            return intents[0].get("prompt", "Which file did you mean? Please specify the filename.")

        results = []

        for it in intents:
            act = it.get("action")
            
            if act == "none":
                continue

            if act not in self.supported_actions_map:
                print(f"WARNING: Received unsupported action: {act}")
                results = []
                return f"Sorry, I don't know how to '{act.replace('_', ' ')}'."
                
            module_instance, method_name, _, _ = self.supported_actions_map[act]
            
            kwargs = {k: v for k, v in it.items() if k not in ["action"]}

            try:
                method_to_call = getattr(module_instance, method_name)
                result = method_to_call(**kwargs)
                results.append(result)

                if act == "create_file" and "File created" in result:
                    self.last_filename = kwargs.get("filename")
                elif act == "write_file" and "File written" in result:
                    self.last_filename = kwargs.get("filename")
                elif act == "delete_file" and self.last_filename == kwargs.get("filename") and "File deleted" in result:
                    self.last_filename = None

            except TypeError as te:
                print(f"ERROR: Method '{method_name}' in module '{type(module_instance).__name__}' called with incorrect arguments for action '{act}'. Details: {te}")
                return f"Sorry, I had trouble executing the command. Missing or incorrect arguments for '{act.replace('_', ' ')}'."
            except Exception as e:
                print(f"ERROR: Failed to execute action '{act}' from module '{type(module_instance).__name__}'. Details: {e}")
                return f"Sorry, I encountered an error while trying to '{act.replace('_', ' ')}'."

        if results:
            return "\n".join(results)

        return generate_response(user_text)

    def run(self):
        print("Backend running. Type 'exit' to quit.")
        while True:
            cmd = input("You: ")
            if cmd.lower() in ("exit", "quit"):
                break
            print("Assistant:", self.process_command(cmd))


if __name__ == "__main__":
    backend = Backend()
    backend.run()
