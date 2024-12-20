import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pytz

# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Supabase credentials are missing. Check your environment variables.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Path to your service account JSON key file
SERVICE_ACCOUNT_FILE = 'config/service_account_key.json'  
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']  

def authenticate_google_calendar():
    """Authenticate and build the Google Calendar service object."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    return service

def get_upcoming_events_today(calendar_id='primary'):
    """
    Fetch all upcoming events for the remainder of the current day from Google Calendar.

    Parameters:
    - calendar_id: ID of the calendar to access (default is 'primary' for main calendar)

    Returns:
    - List of event dictionaries with titles and start times for today's remaining events.
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

    # Collect event summaries and start times
    event_details = [
        {"title": event.get("summary", "No Title"), "start_time": event["start"].get("dateTime", event["start"].get("date"))}
        for event in events
    ]
    return event_details

def save_events_to_supabase(events):
    """Save today's events to the Supabase database."""
    table_name = "calendar-events"
    try:
        for event in events:
            # Insert each event into the Supabase table
            supabase.table(table_name).insert({
                "title": event["title"],
                "start_time": event["start_time"],
                "created_at": datetime.now(pytz.UTC).isoformat()
            }).execute()
        print("Events saved to Supabase successfully!")
    except Exception as e:
        print(f"Error saving events to Supabase: {e}")

# Example usage
if __name__ == "__main__":
    events_today = get_upcoming_events_today()
    if events_today:
        print("Upcoming Events Today:")
        for event in events_today:
            print(f"- {event['title']} at {event['start_time']}")
        save_events_to_supabase(events_today)
    else:
        print("No upcoming events found for today.")
