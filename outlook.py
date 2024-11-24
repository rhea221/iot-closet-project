import os
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Configuration for Microsoft Graph API
CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
TENANT_ID = os.getenv("MS_TENANT_ID")

# Function to authenticate and obtain an access token
def get_access_token():
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

    if "access_token" in result:
        return result["access_token"]
    else:
        print("Error obtaining access token:", result.get("error"))
        return None

# Function to fetch calendar events
def get_calendar_events():
    access_token = get_access_token()
    if not access_token:
        raise ValueError("Failed to get access token.")

    # Set up headers and endpoint for calendar events
    headers = {"Authorization": f"Bearer {access_token}"}
    calendar_url = "https://graph.microsoft.com/v1.0/users/np221/events"


    response = requests.get(calendar_url, headers=headers)
    if response.status_code == 200:
        events = response.json().get("value", [])
        # Process and return events
        event_list = [{"subject": event["subject"], "start": event["start"]["dateTime"]} for event in events]
        return event_list
    else:
        print("Failed to retrieve events:", response.status_code)
        return None

# Example usage
if __name__ == "__main__":
    events = get_calendar_events()
    print(events)
