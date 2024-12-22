import openai
from supabase import create_client, Client
from datetime import datetime, timezone
from dotenv import load_dotenv
from dateutil import parser
import os

# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not SUPABASE_URL or not SUPABASE_KEY or not OPENAI_API_KEY:
    raise Exception("Supabase or OpenAI credentials are missing. Check your environment variables.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

# Fetch Data from Supabase
def fetch_weather():
    """Fetch the most recent weather data from Supabase."""
    response = supabase.table("weather-data").select("*").order("created_at", desc=True).limit(1).execute()
    return response.data[0] if response.data else None

def fetch_remaining_events():
    """Fetch remaining calendar events for the day from Supabase."""
    now = datetime.now(timezone.utc)
    response = supabase.table("calendar-events").select("*").execute()
    events = response.data or []
    # Filter for events occurring later today
    remaining_events = [
        event for event in events
        if parser.isoparse(event["start_time"]).replace(tzinfo=timezone.utc) > now
    ]
    return remaining_events

def fetch_clothing_items():
    """Fetch clothing items stored in the Supabase closet-items table."""
    response = supabase.table("closet-items").select("*").execute()
    return response.data or []

# OpenAI Recommendation Logic
def recommend_clothing_with_openai(weather, remaining_events, clothing_items, available_tags):
    """Use OpenAI to recommend clothing items based on weather, events, and available tags."""
    # Format weather data
    weather_context = f"The current temperature is {weather['temp']}°C with {weather['weather']}."

    # Format remaining events with fallback for missing keys
    if remaining_events:
        event_context = " ".join([
            f"{event.get('title', 'Untitled Event')} at {event.get('location', 'No location specified')}"
            for event in remaining_events
        ])
    else:
        event_context = "There are no remaining events for the day."

    # Format available tags
    tags_context = f"Available tags are: {', '.join(available_tags)}."

    # Format clothing items
    clothing_context = "\n".join([
        f"Clothing Item {i+1}: {item['tags']} (Image: {item['image_url']})"
        for i, item in enumerate(clothing_items)
    ])

    # Create prompt for OpenAI
    prompt = (
        f"Based on the following information, recommend a top and a bottom clothing item:\n"
        f"- Weather: {weather_context}\n"
        f"- Events: {event_context}\n"
        f"- Tags: {tags_context}\n"
        f"- Clothing Items:\n{clothing_context}\n\n"
        f"Select a top and a bottom clothing item from the list and provide a short justification for your choices."
    )

    # Call OpenAI API
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Replace with gpt-3.5-turbo if gpt-4 access is unavailable
            messages=[
                {"role": "system", "content": "You are a fashion stylist and clothing analyst."},
                {"role": "user", "content": prompt},
            ]
        )
        # Extract and return content from response
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error generating clothing recommendation: {str(e)}")







# Main Logic
def main():
    weather = fetch_weather()
    remaining_events = fetch_remaining_events()
    clothing_items = fetch_clothing_items()

    if not weather or not clothing_items:
        print("Insufficient data for recommendation.")
        return

    # Define available tags (from app.py dropdowns)
    available_tags = [
        "#red", "#blue", "#green", "#yellow", "#pink", "#black", "#white",
        "#tshirt", "#sweatshirt", "#jacket", "#pants", "#skirt", "#dress", "#shorts",
        "#cotton", "#denim", "#leather", "#wool", "#polyester",
        "#solid", "#striped", "#checked", "#polka-dot", "#floral"
    ]

    # Generate recommendation
    recommendation = recommend_clothing_with_openai(weather, remaining_events, clothing_items, available_tags)
    print("Recommendation:")
    print(recommendation)

if __name__ == "__main__":
    main()
