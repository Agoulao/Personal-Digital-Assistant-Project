from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAutomationModule(ABC):
    """
    Abstract Base Class for all automation modules.
    Each module should inherit from this and implement the required methods.
    """

    @abstractmethod
    def get_supported_actions(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns a dictionary where keys are action names (strings) and values
        are dictionaries containing:
        - "method_name": The name of the corresponding method in this module.
        - "description": A brief description of what the action does.
        - "example_json": An example of the JSON intent structure for this action,
                          as the LLM should generate it.

        Example:
        {
            "create_event": {
                "method_name": "create_calendar_event",
                "description": "Creates a new calendar event.",
                "example_json": '{"action":"create_event","summary":"Team Meeting","start_time":"2025-07-01T10:00:00","end_time":"2025-07-01T11:00:00"}'
            },
            "list_events": {
                "method_name": "list_calendar_events",
                "description": "Lists upcoming calendar events.",
                "example_json": '{"action":"list_events","time_period":"today"}'
            }
        }
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Returns a brief description of the module's overall functionality.
        """
        pass
