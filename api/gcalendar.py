# Handles Google Calendar API integration, to fetch upcoming events and upload to database

import os
import pytz
from dotenv import load_dotenv
from datetime import datetime, timezone
from supabase import create_client, Client
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dateutil import parser

# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Supabase credentials are missing. Check your environment variables.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# service account JSON key
SERVICE_ACCOUNT_FILE = 'service_account_key.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def authenticate_google_calendar():
    """Authenticate and build the Google Calendar service object."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    return service

def get_upcoming_events_today(calendar_id='rhea.p3rk@gmail.com'):
    #Fetches all upcoming events for the remainder of the current day from Google Calendar.
    service = authenticate_google_calendar()
    now = datetime.now(pytz.UTC)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now.isoformat(),
        timeMax=end_of_day.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    if not events:
        print("No upcoming events found for today.")
        return []

    event_details = []
    for event in events:
        details = {
            "google-event-id": event.get("id", ""),
            "title": event.get("summary", "No Title"),
            "start_time": event["start"].get("dateTime", event["start"].get("date")),
            "location": event.get("location", "Unknown"),
            "duration": calculate_duration(event.get("start"), event.get("end"))
        }
        event_details.append(details)

    return event_details

def calculate_duration(start, end):
    # Calculates the duration of an event.
    # dateutil.parser is used to handle various datetime formats
    start_time = parser.isoparse(start.get("dateTime", start.get("date")))
    end_time = parser.isoparse(end.get("dateTime", end.get("date")))

    return (end_time - start_time).total_seconds() / 3600  # Return duration in hours

def fetch_existing_events():
    # Fetch existing calendar events from Supabase for today
    now = datetime.now(pytz.UTC)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        response = supabase.table("calendar-events").select("*").gte("start_time", start_of_day.isoformat()).execute()
        if response.data:
            # Normalize timestamps for comparison
            for event in response.data:
                event["start_time"] = str(parser.isoparse(event["start_time"]).astimezone(pytz.UTC).isoformat())
            return response.data
        else:
            print("No existing events found for today.")
            return []
    except Exception as e:
        print(f"Error fetching existing events: {e}")
        return []



def filter_new_events(events, existing_events):
    # Filters out events that are already in the database

    # Creating a set of existing event keys (normalized)
    existing_event_keys = {
        (event["google-event-id"], event["start_time"], event["title"])
        for event in existing_events
    }

    new_events = []
    for event in events:
        # Normalize event keys for comparison
        event_key = (
            event["google-event-id"],
            str(parser.isoparse(event["start_time"]).astimezone(pytz.UTC).isoformat()),
            event["title"]
        )
        if event_key not in existing_event_keys:
            new_events.append(event)

    return new_events



def save_events_to_supabase(events):
    # Saves today's events to Supabase
    table_name = "calendar-events"
    try:
        for event in events:
            # Insert each event into the Supabase table
            supabase.table(table_name).insert({
                "google-event-id": event["google-event-id"],
                "title": event["title"],
                "start_time": event["start_time"],
                "location": event["location"],
                "duration": event["duration"],
                "created_at": datetime.now(pytz.UTC).isoformat()
            }).execute()
        print("Events saved to Supabase successfully!")
    except Exception as e:
        print(f"Error saving events to Supabase: {e}")

if __name__ == "__main__":
    events_today = get_upcoming_events_today()
    if events_today:
        existing_events = fetch_existing_events()
        new_events = filter_new_events(events_today, existing_events)

        if new_events:
            print("New Events to Insert:")
            for event in new_events:
                print(f"- {event['title']} at {event['start_time']}")
            save_events_to_supabase(new_events)
        else:
            print("No new events to add. All events are up to date.")
    else:
        print("No upcoming events found for today.")
