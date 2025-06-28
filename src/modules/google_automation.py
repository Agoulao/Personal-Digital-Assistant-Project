######################################################################################################
# IMPORTANT: Requires 'client_secret.json' from Google Calendar in the same directory as this module.
# Navigate to Google Cloud Console, create a project, enable Calendar API,
# and download the OAuth 2.0 credentials as 'client_secret(...).json'.
# Rename it to 'client_secret.json' and place it in the 'modules' directory.
#######################################################################################################


import functools
import logging
import datetime
import os.path
import json
import time # For performance measurement

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Date parsing library (no longer used for direct parsing, but for internal datetime objects)
from dateutil import parser
from dateutil.relativedelta import relativedelta
import pytz

from modules.base_automation import BaseAutomationModule # Import the base class
from typing import Dict, Any

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# Decorator for safe execution and uniform error handling
def safe_action(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HttpError as error:
            logging.error(f"Google Calendar API Error in {func.__name__}: {error}", exc_info=True)
            return f"[FAIL] Failed to {func.__name__.replace('_', ' ')}. Google Calendar API error: {error.resp.status} - {error.content.decode()}"
        except ValueError as ve:
            logging.error(f"Data parsing error in {func.__name__}: {ve}", exc_info=True)
            return f"[FAIL] Failed to {func.__name__.replace('_', ' ')}. Invalid input data: {ve}"
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return f"[FAIL] Failed to {func.__name__.replace('_', ' ')}. An unexpected error occurred: {e}"
    return wrapper

class GoogleCalendarAutomation(BaseAutomationModule):
    """
    Provides automation for Google Calendar via its API.
    Requires Google API setup, authentication, and credentials.
    """

    def __init__(self):
        self.module_dir = os.path.dirname(os.path.abspath(__file__))
        self.token_path = os.path.join(self.module_dir, 'token.json')
        self.client_secret_path = os.path.join(self.module_dir, 'client_secret.json')
        
        self.local_tz = pytz.timezone('Europe/Lisbon') 

        print("DEBUG: Authenticating Google Calendar API...")
        auth_start_time = time.time()
        self.service = self._authenticate_google_calendar()
        auth_end_time = time.time()
        print(f"DEBUG: Google Calendar API authentication took {auth_end_time - auth_start_time:.2f} seconds.")

        if self.service == "AUTHENTICATION_FAILED":
            print("WARNING: Google Calendar API authentication failed. Calendar features will be unavailable.")
            self.is_authenticated = False
        else:
            self.is_authenticated = True
            print("INFO: GoogleCalendarAutomation module initialized and authenticated.")

    def _authenticate_google_calendar(self):
        """
        Handles Google Calendar API authentication using OAuth 2.0.
        It looks for 'token.json' and creates it if not found or expired.
        Requires 'client_secret.json' in the same directory as this module.
        """
        creds = None
        if os.path.exists(self.token_path):
            print("DEBUG: Found existing token.json.")
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        if not creds or not creds.valid:
            print("DEBUG: Credentials not valid or not found. Initiating fresh authentication.")
            if creds and creds.expired and creds.refresh_token:
                print("DEBUG: Refreshing expired token.")
                creds.refresh(Request())
            else:
                try:
                    print("DEBUG: Running local server for OAuth flow.")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secret_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                except FileNotFoundError:
                    print(f"ERROR: client_secret.json not found at {self.client_secret_path}. Please download it from Google Cloud Console and place it in the same directory as this script.")
                    return "AUTHENTICATION_FAILED"
                except Exception as e:
                    print(f"ERROR: Google Calendar authentication failed: {e}")
                    return "AUTHENTICATION_FAILED"
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
            print("DEBUG: New token.json saved.")
        else:
            print("DEBUG: Credentials are valid.")
        
        if creds:
            try:
                return build('calendar', 'v3', credentials=creds)
            except Exception as e:
                print(f"ERROR: Failed to build Google Calendar service: {e}")
                return "AUTHENTICATION_FAILED"
        return "AUTHENTICATION_FAILED"


    def get_description(self) -> str:
        return "Manages events and appointments in Google Calendar."

    def get_supported_actions(self) -> Dict[str, Dict[str, Any]]:
        if not self.is_authenticated:
            return {}

        return {
            "list_events": {
                "method_name": "list_calendar_events",
                "description": "Lists upcoming calendar events for a specified time period. The time_period can be a single date (YYYY-MM-DD), a specific datetime (YYYY-MM-DDTHH:MM:SS), or a range (YYYY-MM-DD/YYYY-MM-DD).",
                "example_json": '{"action":"list_events","time_period":"2025-07-01/2025-07-31"}'
            },
            "create_event": {
                "method_name": "create_calendar_event",
                "description": "Creates a new calendar event with a summary, start time, and optional end time and description. Times must be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS for specific times, or INSEE-MM-DD for all-day).",
                "example_json": '{"action":"create_event","summary":"Team Sync","start_time":"2025-07-01T10:00:00","end_time":"2025-07-01T11:00:00","description":"Discuss Q3 goals"}'
            },
            "delete_event": {
                "method_name": "delete_calendar_event",
                "description": "Deletes a calendar event by its summary and optional time period. The summary should be an exact or very close match to an existing event. Time period must be in ISO 8601 format (YYYY-MM-DD or INSEE-MM-DD/YYYY-MM-DD).",
                "example_json": '{"action":"delete_event","summary":"Team Sync","time_period":"2025-07-01"}'
            },
            # Add more calendar actions as needed
        }

    @safe_action
    def list_calendar_events(self, time_period: str = "today") -> str:
        """
        Lists events for a specified time period.
        time_period is expected to be in ISO 8601 format (YYYY-MM-DD, INSEE-MM-DDTHH:MM:SS, or INSEE-MM-DD/YYYY-MM-DD).
        """
        if not self.is_authenticated:
            return "Google Calendar API not authenticated."

        time_min_iso = None
        time_max_iso = None

        try:
            if '/' in time_period: # Handle date range (e.g., "2025-01-01/2025-12-31")
                start_date_str, end_date_str = time_period.split('/')
                
                # Parse start date/time as local, then convert to UTC for query
                try: # Try parsing as full datetime first
                    start_dt_local = self.local_tz.localize(datetime.datetime.fromisoformat(start_date_str))
                except ValueError: # If only date is provided
                    start_dt_local = self.local_tz.localize(datetime.datetime.strptime(start_date_str, '%Y-%m-%d')).replace(hour=0, minute=0, second=0, microsecond=0)
                time_min_iso = start_dt_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
                
                # Parse end date/time as local, then convert to UTC for query
                try: # Try parsing as full datetime first
                    end_dt_local = self.local_tz.localize(datetime.datetime.fromisoformat(end_date_str))
                except ValueError: # If only date is provided, set to end of day
                    end_dt_local = self.local_tz.localize(datetime.datetime.strptime(end_date_str, '%Y-%m-%d')).replace(hour=23, minute=59, second=59, microsecond=999999)
                time_max_iso = end_dt_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')

            else: # Single date or datetime (e.g., "2025-07-10" or "2025-07-10T15:30:00")
                # Check if the time_period string contains a time component ('T')
                if 'T' in time_period:
                    # Specific datetime: parse as local, convert to UTC, set 1-minute window
                    dt_obj_local = self.local_tz.localize(datetime.datetime.fromisoformat(time_period.replace('Z', ''))) # Ensure 'Z' is removed if LLM adds it
                    time_min_iso = dt_obj_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
                    time_max_iso = (dt_obj_local + datetime.timedelta(minutes=1)).astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
                else:
                    # Date-only: parse as local date, set timeMin to start of day, timeMax to start of next day
                    date_obj_local = self.local_tz.localize(datetime.datetime.strptime(time_period, '%Y-%m-%d'))
                    time_min_iso = date_obj_local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
                    next_day_local = date_obj_local + datetime.timedelta(days=1)
                    time_max_iso = next_day_local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')

        except Exception as e:
            raise ValueError(f"Invalid ISO 8601 date/time format for time_period: '{time_period}'. Error: {e}")

        print(f"DEBUG: Calling Google Calendar API to list events (timeMin={time_min_iso}, timeMax={time_max_iso})...")
        api_call_start_time = time.time()
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=time_min_iso,
            timeMax=time_max_iso, # Will be None if no time_period specified
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        api_call_end_time = time.time()
        print(f"DEBUG: Google Calendar API list events call took {api_call_end_time - api_call_start_time:.2f} seconds.")

        events = events_result.get('items', [])

        if not events:
            return f"No upcoming events found for the period: {time_period}."
        
        output = f"Upcoming events for {time_period}:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            summary = event.get('summary', 'No Title')
            
            # For display, convert UTC times from Google back to local timezone for readability
            try:
                if 'dateTime' in event['start']:
                    start_dt_utc = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                    start_dt_local = start_dt_utc.astimezone(self.local_tz)
                    start_display = start_dt_local.strftime('%Y-%m-%d %H:%M')
                else: # All-day event (date string)
                    start_display = start 
                
                if 'dateTime' in event['end']:
                    end_dt_utc = datetime.datetime.fromisoformat(end.replace('Z', '+00:00'))
                    end_dt_local = end_dt_utc.astimezone(self.local_tz)
                    end_display = end_dt_local.strftime('%Y-%m-%d %H:%M')
                else: # All-day event (date string)
                    end_date_obj = datetime.datetime.fromisoformat(end).date() # This correctly gets a datetime.date object
                    end_display = (end_date_obj - datetime.timedelta(days=1)).isoformat() # Corrected to show actual end day

            except Exception as e:
                start_display = start
                end_display = end
                logging.warning(f"Failed to format event time for display: {e}. Raw: {start} to {end}")

            output += f"- {summary} ({start_display} to {end_display})\n"
        return output

    @safe_action
    def create_calendar_event(self, summary: str, start_time: str, end_time: str = None, description: str = None) -> str:
        """
        Creates a new calendar event.
        start_time and end_time are expected to be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS or INSEE-MM-DD), local time.
        """
        if not self.is_authenticated:
            return "Google Calendar API not authenticated."

        event = {
            'summary': summary,
            'description': description,
        }

        # Determine if it's an all-day event or specific time event based on 'T'
        is_all_day_start = 'T' not in start_time # Check for 'T' to signify time component

        if is_all_day_start:
            # All-day event: LLM provides INSEE-MM-DD (local date)
            start_date_obj = datetime.datetime.strptime(start_time, '%Y-%m-%d').date()
            event['start'] = {'date': start_time} # Google Calendar handles date-only events correctly
            # For all-day events, end date is exclusive, so it's the day *after* the event ends
            if end_time and 'T' not in end_time:
                end_date_obj = datetime.datetime.strptime(end_time, '%Y-%m-%d').date()
                event['end'] = {'date': (end_date_obj + datetime.timedelta(days=1)).isoformat()}
            else:
                event['end'] = {'date': (start_date_obj + datetime.timedelta(days=1)).isoformat()} # Default 1-day event
        else:
            # Specific time event: LLM provides INSEE-MM-DDTHH:MM:SS (local time)
            try:
                # --- MODIFIED: Remove 'Z' if present before parsing ---
                start_time_clean = start_time.replace('Z', '')
                # Parse as local datetime, then convert to UTC for Google Calendar
                start_dt_local = self.local_tz.localize(datetime.datetime.fromisoformat(start_time_clean))
                event['start'] = {'dateTime': start_dt_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')}
                event['start']['timeZone'] = 'UTC' # Explicitly set timezone to UTC for Google if we're sending UTC datetime

                if end_time:
                    end_time_clean = end_time.replace('Z', '') # --- MODIFIED: Remove 'Z' if present ---
                    end_dt_local = self.local_tz.localize(datetime.datetime.fromisoformat(end_time_clean))
                    event['end'] = {'dateTime': end_dt_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')}
                    event['end']['timeZone'] = 'UTC'
                else:
                    # If no end_time, assume 1-hour event. Calculate end_time in local, then convert to UTC.
                    end_dt_local = start_dt_local + datetime.timedelta(hours=1)
                    event['end'] = {'dateTime': end_dt_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')}
                    event['end']['timeZone'] = 'UTC'
            except ValueError as e:
                raise ValueError(f"Invalid start_time format for specific time event: {start_time}. Error: {e}")

        print(f"DEBUG: Calling Google Calendar API to create event (summary='{summary}', start_time='{start_time}')...")
        api_call_start_time = time.time()
        event = self.service.events().insert(calendarId='primary', body=event).execute()
        api_call_end_time = time.time()
        print(f"DEBUG: Google Calendar API create event call took {api_call_end_time - api_call_start_time:.2f} seconds.")
        return f"Event '{event.get('summary')}' created successfully. Link: {event.get('htmlLink')}"

    @safe_action
    def delete_calendar_event(self, summary: str, time_period: str = None) -> str:
        """
        Deletes a calendar event by its summary.
        It will search for events matching the summary within the specified time period.
        If multiple events match, it will delete the first one found.
        time_period is expected to be in ISO 8601 format (YYYY-MM-DD or INSEE-MM-DD/YYYY-MM-DD), local time.
        """
        if not self.is_authenticated:
            return "Google Calendar API not authenticated."

        time_min_iso = None
        time_max_iso = None

        if time_period:
            try:
                if '/' in time_period: # Handle date range
                    start_date_str, end_date_str = time_period.split('/')
                    start_dt_local = self.local_tz.localize(datetime.datetime.strptime(start_date_str, '%Y-%m-%d'))
                    end_dt_local = self.local_tz.localize(datetime.datetime.strptime(end_date_str, '%Y-%m-%d')).replace(hour=23, minute=59, second=59, microsecond=999999)
                    time_min_iso = start_dt_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
                    time_max_iso = end_dt_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
                else: # Single date
                    date_obj_local = self.local_tz.localize(datetime.datetime.strptime(time_period, '%Y-%m-%d'))
                    time_min_iso = date_obj_local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
                    time_max_iso = (date_obj_local + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc).isoformat().replace('+00:00', 'Z') # End of day for single date
            except Exception as e:
                raise ValueError(f"Invalid ISO 8601 date format for time_period: '{time_period}'. Error: {e}")
        else: # If no time_period is provided, search for events from now onwards (local now converted to UTC)
            now_local = datetime.datetime.now(self.local_tz)
            time_min_iso = now_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
            # No time_max_iso means search indefinitely into the future

        print(f"DEBUG: Calling Google Calendar API to list events for deletion search (timeMin={time_min_iso}, timeMax={time_max_iso})...")
        api_call_start_time = time.time()
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=time_min_iso,
            timeMax=time_max_iso, # Will be None if no time_period specified
            q=summary, # Query for events matching the summary
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        api_call_end_time = time.time()
        print(f"DEBUG: Google Calendar API list events for deletion search took {api_call_end_time - api_call_start_time:.2f} seconds.")

        events = events_result.get('items', [])

        # Filter events by summary (case-insensitive and partial match for forgiveness)
        matching_events = [
            event for event in events 
            if summary.lower() in event.get('summary', '').lower()
        ]

        if not matching_events:
            return f"No event found with summary matching '{summary}' for the period: {time_period if time_period else 'any upcoming time'}."
        
        if len(matching_events) > 1:
            logging.warning(f"Multiple events found matching '{summary}'. Deleting the first one: '{matching_events[0].get('summary')}'")
            
        event_to_delete = matching_events[0]
        event_id = event_to_delete['id']
        event_summary = event_to_delete['summary']

        print(f"DEBUG: Calling Google Calendar API to delete event (ID={event_id}, Summary='{event_summary}')...")
        api_call_start_time = time.time()
        self.service.events().delete(calendarId='primary', eventId=event_id).execute()
        api_call_end_time = time.time()
        print(f"DEBUG: Google Calendar API delete event call took {api_call_end_time - api_call_start_time:.2f} seconds.")
        return f"Event '{event_summary}' deleted successfully."
