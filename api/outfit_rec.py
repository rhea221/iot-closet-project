# Logic for outfit recommendations, interacting with uploaded database

from supabase import create_client, Client
from datetime import datetime, timezone
from dotenv import load_dotenv
from dateutil import parser
import os
import random

# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Supabase credentials are missing. Check your environment variables.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    """Classify an event based on its title and location."""
    event_title = event.get("title", "").lower()
    event_location = event.get("location", "").lower()

    for category, keywords in EVENT_CATEGORIES.items():
        for keyword in keywords["title_keywords"]:
            if keyword.lower() in event_title:
                return category
        for keyword in keywords["location_keywords"]:
            if keyword.lower() in event_location:
                return category

    return "Uncategorized"

def fetch_events():
    """Fetch events stored in the Supabase calendar-events table."""
    response = supabase.table("calendar-events").select("*").execute()
    return response.data or []

def fetch_weather():
    """Fetch the most recent weather data from Supabase."""
    response = supabase.table("weather-data").select("*").order("created_at", desc=True).limit(1).execute()
    return response.data[0] if response.data else None

def fetch_outfit_items():
    """Fetch clothing items stored in the Supabase closet-items table."""
    response = supabase.table("closet-items").select("*").execute()
    return response.data or []

def match_clothing(tags, clothing_items):
    """
    Match clothing items to the given tags.
    Returns a random match if multiple items fit.
    """
    matched_items = [item for item in clothing_items if all(tag in item["tags"] for tag in tags)]
    return random.choice(matched_items) if matched_items else None

def recommend_outfits():
    """Generate outfit recommendations by matching clothing items (including shoes) to weather and events."""
    events = fetch_events()
    weather = fetch_weather()
    outfit_items = fetch_outfit_items()
    now = datetime.now(timezone.utc)

    if not events:
        return {"recommendation": "No events for the rest of the day."}

    # Filter events to only include those happening after the current time
    remaining_events = [
        event for event in events
        if parser.isoparse(event["start_time"]).replace(tzinfo=timezone.utc) > now
    ]

    if not remaining_events:
        return {"recommendation": "No remaining events for today."}

    # Count the frequency of each event category
    category_counts = {}
    for event in remaining_events:
        category = classify_event(event)
        if category in category_counts:
            category_counts[category] += 1
        else:
            category_counts[category] = 1

    # Determine the dominant event category
    dominant_category = max(category_counts, key=category_counts.get)

    # Weather data
    avg_temp = weather["temp"]
    weather_description = weather["weather"]

    # Select tags based on dominant category and weather
    tags = []
    if dominant_category == "Fitness":
        tags = ["#athletic"]
    elif dominant_category == "Meeting":
        tags = ["#formal"]
    elif dominant_category == "Dining":
        tags = ["#smart-casual"]
    elif dominant_category == "University":
        tags = ["#casual"]
    elif dominant_category == "Leisure":
        tags = ["#comfortable"]
    elif dominant_category == "Social Event":
        tags = ["#dressy"]
    else:
        tags = ["#neutral"]

    # Adjust tags based on weather
    if avg_temp < 10:
        tags.append("#warm")
    elif avg_temp > 25:
        tags.append("#light")
    if "rain" in weather_description:
        tags.append("#waterproof")

    # Match clothing items
    top = match_clothing(tags + ["#tshirt", "#sweatshirt"], outfit_items)
    jacket = match_clothing(tags + ["#jacket"], outfit_items)
    bottom = match_clothing(tags + ["#pants", "#skirt", "#shorts"], outfit_items)
    shoes = match_clothing(tags + ["#shoes"], outfit_items)

    # Generate the outfit recommendation
    recommendation = {
        "top": top["image_url"] if top else "No matching top found",
        "jacket": jacket["image_url"] if jacket else "No matching jacket found",
        "bottom": bottom["image_url"] if bottom else "No matching bottom found",
        "shoes": shoes["image_url"] if shoes else "No matching shoes found",
        "details": {
            "tags": tags,
            "events_considered": len(remaining_events),
            "dominant_category": dominant_category,
            "weather": {
                "temp": avg_temp,
                "description": weather_description,
            }
        }
    }

    return recommendation

if __name__ == "__main__":
    result = recommend_outfits()
    print("Outfit Recommendation:")
    print(f"Top: {result['top']}")
    print(f"Jacket: {result['jacket']}")
    print(f"Bottom: {result['bottom']}")
    print(f"Shoes: {result['shoes']}")
    print("Details:")
    print(result["details"])


