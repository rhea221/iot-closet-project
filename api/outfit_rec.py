from datetime import datetime, timezone
import pytz

# Define keywords for event classification
EVENT_CATEGORIES = {
    "University": {
        "title_keywords": [],
        "location_keywords": ["Dyson Building"]
    },
    "Meeting": {
        "title_keywords": ["Meeting"],
        "location_keywords": []
    },
    "Fitness": {
        "title_keywords": ["Gym", "Bouldering"],
        "location_keywords": []
    },
    "Dining": {
        "title_keywords": ["Brunch", "Lunch", "Dinner"],
        "location_keywords": []
    },
    "Leisure": {
        "title_keywords": ["Musical", "Movie", "Museum", "Crafts"],
        "location_keywords": []
    },
    "Social Event": {
        "title_keywords": ["Clubbing", "Party", "Games"],
        "location_keywords": []
    },
    "Appointments": {
        "title_keywords": ["Appointment"],
        "location_keywords": []
    }
}

def classify_event(event):
    """
    Classify an event based on its title and location.
    
    Parameters:
    - event: Dictionary containing "title" and "location".

    Returns:
    - Event category (string) or "Uncategorized" if no match is found.
    """
    event_title = event.get("title", "").lower()
    event_location = event.get("location", "").lower()

    for category, keywords in EVENT_CATEGORIES.items():
        # Check title keywords
        for keyword in keywords["title_keywords"]:
            if keyword.lower() in event_title:
                return category
        
        # Check location keywords (only applies to events like University)
        for keyword in keywords["location_keywords"]:
            if keyword.lower() in event_location:
                return category

    return "Uncategorized"

def calculate_duration(start, end):
    """
    Calculate the duration of an event.
    """
    from dateutil import parser  # For robust ISO 8601 parsing
    start_time = parser.isoparse(start.get("dateTime", start.get("date")))
    end_time = parser.isoparse(end.get("dateTime", end.get("date")))
    return (end_time - start_time).total_seconds() / 3600  # Duration in hours

def process_events(events):
    """
    Process a list of events and classify them.
    
    Parameters:
    - events: List of event dictionaries with "title" and "location".

    Returns:
    - List of classified event dictionaries.
    """
    processed_events = []
    for event in events:
        event_details = {
            "title": event.get("summary", "No Title"),
            "location": event.get("location", "Unknown"),
            "start_time": event["start"].get("dateTime", event["start"].get("date")),
            "duration": calculate_duration(event["start"], event["end"]),
            "category": classify_event({
                "title": event.get("summary", "No Title"),
                "location": event.get("location", "Unknown")
            })
        }
        processed_events.append(event_details)
    return processed_events
