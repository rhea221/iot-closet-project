from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timedelta
import pytz

# Path to your service account JSON key file
SERVICE_ACCOUNT_FILE = 'config/service_account_key.json'  # Update with actual path
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']  # Read-only access

def authenticate_google_calendar():
    """Authenticate and build the Google Calendar service object."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    return service

def get_upcoming_events_today(calendar_id='rhea.p3rk@gmail.com'):
    """
    Fetch all upcoming events for the remainder of the current day from Google Calendar.

    Parameters:
    - calendar_id: ID of the calendar to access (default is 'primary' for main calendar)

    Returns:
    - List of event titles (summaries) for the remaining events of the current day.
    """
    service = authenticate_google_calendar()
    
    # Set timeMin to the current time and timeMax to the end of today in UTC
    now = datetime.now(pytz.UTC)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Fetch events within this time range
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now.isoformat(),         # Start from the current time
        timeMax=end_of_day.isoformat(),  # End at the last second of the day
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    if not events:
        print("No upcoming events found for today.")
        return []

    # Collect and return only the event titles
    event_titles = [event.get("summary", "No Title") for event in events]
    return event_titles

# Example usage
if __name__ == "__main__":
    upcoming_events_today = get_upcoming_events_today()
    if upcoming_events_today:
        print("Upcoming Events Today:")
        for title in upcoming_events_today:
            print("-", title)
    else:
        print("No upcoming events found for today.")
