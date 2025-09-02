# File: modules/gmail_automation.py

################################################################################################################
# IMPORTANT: Requires 'client_secret.json' from Google Calendar in the resources directory.
# Navigate to Google Cloud Console, create a project, enable Calendar API,
# add the following scope "https://mail.google.com/" in Google Auth Platform/Data access,
# https://www.googleapis.com/auth/calendar.events is also needed if google_calendar_automation.py is enabled
# and download the OAuth 2.0 credentials as 'client_secret(...).json'.
# Rename it to 'client_secret.json' and place it in the 'modules/resources' directory.
#################################################################################################################

import functools
import logging
import os
from typing import Dict, Any, Optional, List
import base64
from email.mime.text import MIMEText
import datetime # for date calculations

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from modules.base_automation import BaseAutomationModule

# Decorator for safe execution and uniform error handling
def safe_action(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logging.error(f"Error in {func.__name__}:", exc_info=True)
            return f"[FAIL] Failed to {func.__name__.replace('_', ' ')}."
    return wrapper

class GmailAutomation(BaseAutomationModule):
    """
    Provides automation for Gmail via Google Gmail API.
    Requires Google Cloud project setup and OAuth 2.0 authentication.
    """

    # If modifying these scopes, delete the file token.json.
    # COMBINED SCOPES for both Gmail and Google Calendar (if using the same client_secret.json)
    SCOPES = [
        'https://mail.google.com/',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    # Construct full paths relative to the current module file
    MODULE_DIR = os.path.dirname(__file__)
    RESOURCES_DIR = os.path.join(MODULE_DIR, '..', 'resources')
    CLIENT_SECRET_FILE = os.path.join(RESOURCES_DIR, 'client_secret.json') # Using the common client_secret.json for both services
    TOKEN_FILE = os.path.join(RESOURCES_DIR, 'token.json') # Using the common token.json for both services
    MODULE_DIR = os.path.dirname(__file__)

    def __init__(self):
        self.service = self._authenticate_gmail()
        if self.service:
            print("GmailAutomation module initialized and authenticated.")
        else:
            print("GmailAutomation module failed to authenticate.")

    def _authenticate_gmail(self):
        """
        Authenticates with Google APIs (Gmail and Calendar) using OAuth 2.0.
        The first time, it will open a browser for user consent.
        Subsequent runs will use the saved token.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(self.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)
        
        # If there are no (valid) credentials available, or if they are expired and refresh fails,
        # let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}. Re-authenticating...")
                    creds = None # Force re-authentication if refresh fails
            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.CLIENT_SECRET_FILE, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Error during Google API authentication flow: {e}")
                    print(f"Please ensure '{os.path.basename(self.CLIENT_SECRET_FILE)}' is in the '{os.path.basename(self.MODULE_DIR)}' directory and correctly configured in Google Cloud Console with all necessary scopes enabled.")
                    return None
            # Save the credentials for the next run
            with open(self.TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        try:
            # Build the Gmail service client with the obtained credentials
            service = build('gmail', 'v1', credentials=creds)
            return service
        except HttpError as error:
            print(f"An error occurred building Gmail service: {error}")
            return None

    def get_description(self) -> str:
        """
        Returns a brief description of the module's capabilities.
        """
        return "Manages emails in Gmail (list, send, read, mark as read, delete)."

    def get_supported_actions(self) -> Dict[str, Dict[str, Any]]:
        return {
            "list_emails": {
                "method_name": "list_emails",
                "description": "Lists emails from a specified label (e.g., 'INBOX', 'UNREAD', 'SENT'), optionally filtered by sender, date period, and unread status. Use 'all_results: true' if user asks for all emails.",
                "example_json": '{"action":"list_emails","label":"INBOX","sender":"john.doe@example.com","date_period":"2025-07-28","max_results":5,"is_unread":true}' 
            },
            "send_email": {
                "method_name": "send_email",
                "description": "Sends an email to a recipient with a subject and body.",
                "example_json": '{"action":"send_email","to":"recipient@example.com","subject":"Meeting Reminder","body":"Don\'t forget our meeting tomorrow."}'
            },
            "read_email": {
                "method_name": "read_email",
                "description": "Reads the content of a specific email by its ID.",
                "example_json": '{"action":"read_email","email_id":"<email_id>"}'
            },
            "mark_email_as_read": {
                "method_name": "mark_email_as_read",
                "description": "Marks one or more emails as read by their IDs or by specified criteria (sender, date, unread status).",
                "example_json": '{"action":"mark_email_as_read","email_ids":["<email_id_1>", "<email_id_2>"],"sender":"john.doe@example.com","date_period":"2025-07-28","is_unread":true}'
            },
            "delete_email": {
                "method_name": "delete_email",
                "description": "Deletes one or more emails by their IDs or by specified criteria (sender, date, unread status).",
                "example_json": '{"action":"delete_email","email_ids":["<email_id_1>", "<email_id_2>"],"sender":"old.spam@example.com","date_period":"2024-01-01/2024-01-31"}'
            },
        }

    def _get_email_ids_by_criteria(self, label: str = 'INBOX', sender: Optional[str] = None, date_period: Optional[str] = None, is_unread: Optional[bool] = False) -> List[str]:
        """
        Helper function to get a list of email IDs based on specified criteria.
        This is used internally by mark_email_as_read and delete_email when criteria are provided.
        """
        if not self.service:
            return []

        query_parts = []
        if sender:
            query_parts.append(f"from:{sender}")
        
        if date_period:
            try:
                if '/' in date_period:
                    start_date_str, end_date_str = date_period.split('/')
                    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    end_date_plus_one = end_date + datetime.timedelta(days=1)
                    query_parts.append(f"after:{start_date.strftime('%Y/%m/%d')}")
                    query_parts.append(f"before:{end_date_plus_one.strftime('%Y/%m/%d')}")
                else:
                    single_date = datetime.datetime.strptime(date_period, '%Y-%m-%d').date()
                    single_date_plus_one = single_date + datetime.timedelta(days=1)
                    query_parts.append(f"after:{single_date.strftime('%Y/%m/%d')}")
                    query_parts.append(f"before:{single_date_plus_one.strftime('%Y/%m/%d')}")
            except ValueError:
                logging.error(f"Invalid date format for _get_email_ids_by_criteria: {date_period}")
                return []
        
        if is_unread:
            query_parts.append("is:unread")

        full_query = " ".join(query_parts) if query_parts else None

        try:
            # Fetch a reasonable number of emails for bulk operations (e.g., up to 500)
            results = self.service.users().messages().list(
                userId='me', 
                labelIds=[label.upper()], 
                maxResults=500, # Max results for internal ID fetching
                q=full_query
            ).execute()
            messages = results.get('messages', [])
            return [msg['id'] for msg in messages]
        except HttpError as error:
            logging.error(f"Gmail: An error occurred fetching email IDs by criteria: {error}")
            return []
        except Exception as e:
            logging.error(f"Gmail: An unexpected error occurred fetching email IDs by criteria: {e}")
            return []


    @safe_action
    def list_emails(self, label: str = 'INBOX', max_results: int = 5, sender: Optional[str] = None, date_period: Optional[str] = None, all_results: Optional[bool] = False, is_unread: Optional[bool] = False) -> str:
        """
        Lists emails from a specified label, optionally filtered by sender, date period, and unread status.
        Date period can be a single date (YYYY-MM-DD) or a range (YYYY-MM-DD/YYYY-MM-DD).
        If 'all_results' is True, it overrides max_results to fetch up to 500 emails.
        """
        if not self.service:
            return "Gmail: Service not authenticated. Please check setup."

        effective_max_results = max_results # Start with the default or user-provided max_results

        if all_results:
            effective_max_results = 500 # If all_results is true, override to 500

        query_parts = []
        if sender:
            query_parts.append(f"from:{sender}")
        
        if date_period:
            try:
                if '/' in date_period:
                    # Handle date range: YYYY-MM-DD/YYYY-MM-DD
                    start_date_str, end_date_str = date_period.split('/')
                    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    
                    # Gmail API 'before' is exclusive, so add one day to the end date
                    end_date_plus_one = end_date + datetime.timedelta(days=1)

                    query_parts.append(f"after:{start_date.strftime('%Y/%m/%d')}")
                    query_parts.append(f"before:{end_date_plus_one.strftime('%Y/%m/%d')}")
                else:
                    # Handle single date: YYYY-MM-DD
                    single_date = datetime.datetime.strptime(date_period, '%Y-%m-%d').date()
                    
                    # For a single day, search after the start of the day and before the start of the next day
                    single_date_plus_one = single_date + datetime.timedelta(days=1)

                    query_parts.append(f"after:{single_date.strftime('%Y/%m/%d')}")
                    query_parts.append(f"before:{single_date_plus_one.strftime('%Y/%m/%d')}")
            except ValueError:
                return f"Gmail: Invalid date format provided for date_period: {date_period}. Expected YYYY-MM-DD or YYYY-MM-DD/YYYY-MM-DD."
            except Exception as e:
                return f"Gmail: An error occurred processing date period: {e}"

        if is_unread:
            query_parts.append("is:unread")

        full_query = " ".join(query_parts) if query_parts else None

        try:
            # Use the 'q' parameter for search queries
            results = self.service.users().messages().list(
                userId='me', 
                labelIds=[label.upper()], 
                maxResults=effective_max_results, # Use the effective max_results
                q=full_query # Pass the constructed query here
            ).execute()
            messages = results.get('messages', [])

            if not messages:
                if full_query:
                    return f"No emails found in '{label}' matching the criteria: '{full_query}'."
                return f"No emails found in '{label}'."
            
            email_list = []
            for i, msg in enumerate(messages):
                msg_id = msg['id']
                # Get full message to extract subject, sender, date, and snippet
                # Use format='metadata' to get headers and snippet efficiently
                full_msg = self.service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['From', 'Subject', 'Date']).execute()
                headers = full_msg['payload']['headers']
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date_header = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                snippet = full_msg.get('snippet', 'No snippet available.') # Get the snippet

                email_list.append(
                    f"{i+1}. ID: {msg_id}\n"
                    f"   From: {sender_header}\n"
                    f"   Subject: {subject}\n"
                    f"   Date: {date_header}\n"
                    f"   Snippet: {snippet}\n"
                    f"----------------------------------------------------\n"
                )
            
            return f"Emails in '{label}':\n\n" + "\n".join(email_list)

        except HttpError as error:
            return f"Gmail: An error occurred listing emails: {error}"
        except Exception as e:
            return f"Gmail: An unexpected error occurred: {e}"

    @safe_action
    def send_email(self, to: str, subject: str, body: str) -> str:
        """
        Sends an email.
        """
        if not self.service:
            return "Gmail: Service not authenticated. Please check setup."

        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            sent_message = self.service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
            return f"Gmail: Email sent successfully to '{to}' with subject '{subject}'. Message ID: {sent_message['id']}"
        except HttpError as error:
            return f"Gmail: An error occurred sending email: {error}"
        except Exception as e:
            return f"Gmail: An unexpected error occurred: {e}"

    @safe_action
    def read_email(self, email_id: str) -> str:
        """
        Reads the content of a specific email by ID.
        """
        if not self.service:
            return "Gmail: Service not authenticated. Please check setup."

        try:
            message = self.service.users().messages().get(userId='me', id=email_id, format='full').execute()
            payload = message['payload']
            headers = payload['headers']

            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'N/A')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'N/A')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'N/A')

            parts = payload.get('parts', [])
            body_content = ""

            # Extract plain text body
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body_content = base64.urlsafe_b64decode(data).decode('utf-8')
                    break # Found plain text, stop looking

            if not body_content and payload.get('body', {}).get('data'):
                # Fallback for simple messages without parts
                data = payload['body']['data']
                body_content = base64.urlsafe_b64decode(data).decode('utf-8')

            return (f"Gmail: Reading Email (ID: {email_id})\n"
                    f"From: {sender}\n"
                    f"Subject: {subject}\n"
                    f"Date: {date}\n"
                    f"Body:\n---\n{body_content}\n---")

        except HttpError as error:
            if error.resp.status == 404:
                return f"Gmail: Email with ID '{email_id}' not found."
            return f"Gmail: An error occurred reading email: {error}"
        except Exception as e:
            return f"Gmail: An unexpected error occurred: {e}"

    @safe_action
    def mark_email_as_read(self, email_ids: Optional[List[str]] = None, label: str = 'INBOX', sender: Optional[str] = None, date_period: Optional[str] = None, is_unread: Optional[bool] = False) -> str:
        """
        Marks one or more emails as read.
        Emails can be specified by a list of IDs, or by criteria (sender, date, unread status).
        If criteria are provided, it will attempt to find matching emails and mark them as read.
        """
        if not self.service:
            return "Gmail: Service not authenticated. Please check setup."

        target_email_ids = []
        if email_ids:
            target_email_ids.extend(email_ids)
        elif sender or date_period or is_unread:
            # If criteria are provided, use the helper to get IDs
            fetched_ids = self._get_email_ids_by_criteria(label=label, sender=sender, date_period=date_period, is_unread=is_unread)
            if not fetched_ids:
                return f"No emails found matching the specified criteria to mark as read."
            target_email_ids.extend(fetched_ids)
        else:
            return "Please provide either 'email_ids' or criteria (sender, date_period, is_unread) to mark emails as read."

        if not target_email_ids:
            return "No email IDs provided or found to mark as read."

        results = []
        for email_id in target_email_ids:
            try:
                self.service.users().messages().modify(
                    userId='me', 
                    id=email_id, 
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                results.append(f"Gmail: Email with ID '{email_id}' marked as read successfully.")
            except HttpError as error:
                if error.resp.status == 404:
                    results.append(f"Gmail: Email with ID '{email_id}' not found.")
                else:
                    results.append(f"Gmail: An error occurred marking email ID '{email_id}' as read: {error}")
            except Exception as e:
                results.append(f"Gmail: An unexpected error occurred marking email ID '{email_id}' as read: {e}")
        
        return "\n".join(results)

    @safe_action
    def delete_email(self, email_ids: Optional[List[str]] = None, label: str = 'INBOX', sender: Optional[str] = None, date_period: Optional[str] = None, is_unread: Optional[bool] = False) -> str:
        """
        Deletes one or more emails.
        Emails can be specified by a list of IDs, or by criteria (sender, date, unread status).
        If criteria are provided, it will attempt to find matching emails and delete them.
        """
        if not self.service:
            return "Gmail: Service not authenticated. Please check setup."

        target_email_ids = []
        if email_ids:
            target_email_ids.extend(email_ids)
        elif sender or date_period or is_unread:
            # If criteria are provided, use the helper to get IDs
            fetched_ids = self._get_email_ids_by_criteria(label=label, sender=sender, date_period=date_period, is_unread=is_unread)
            if not fetched_ids:
                return f"No emails found matching the specified criteria to delete."
            target_email_ids.extend(fetched_ids)
        else:
            return "Please provide either 'email_ids' or criteria (sender, date_period, is_unread) to delete emails."

        if not target_email_ids:
            return "No email IDs provided or found to delete."

        results = []
        for email_id in target_email_ids:
            try:
                self.service.users().messages().delete(userId='me', id=email_id).execute()
                results.append(f"Gmail: Email with ID '{email_id}' deleted successfully.")
            except HttpError as error:
                if error.resp.status == 404:
                    results.append(f"Gmail: Email with ID '{email_id}' not found.")
                else:
                    results.append(f"Gmail: An error occurred deleting email ID '{email_id}': {error}")
            except Exception as e:
                results.append(f"Gmail: An unexpected error occurred deleting email ID '{email_id}' as read: {e}")
        
        return "\n".join(results)

