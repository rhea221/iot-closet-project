import json
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
openai.api_key = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not openai.api_key:
    raise Exception("Supabase or OpenAI credentials are missing. Check your environment variables.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    clothing_items = response.data or []

    for item in clothing_items:
        if isinstance(item.get("tags"), str):
            try:
                # Convert the string to a Python list
                item["tags"] = eval(item["tags"])  # Use eval cautiously for known-safe data
            except (SyntaxError, ValueError):
                item["tags"] = []  # Default to empty list if parsing fails

    return clothing_items


def calculate_dominant_event_category(events):
    """Determine the dominant category of events."""
    categories = {
        "university": [],
        "work": ["meeting", "office", "workshop"],
        "dining": ["brunch", "lunch", "dinner"],
        "social": ["party", "club", "dinner", "gathering", "games"],
        "sport": ["gym", "bouldering", "running", "exercise"],
        "leisure": ["movie", "museum", "musical", "picnic", "festival"],
        "appointment": ["appointment"]
    }

    university_locations = ["Dyson Building", "Library", "Imperial College Londong"]
    
    category_count = {key: 0 for key in categories}
    sports_priority = False  # Track if sports events should take priority

    for event in events:
        title = event.get("title", "").lower()
        location = str(event.get("location", "")).lower()  # Ensure location is a string

        if any(loc.lower() in location for loc in university_locations):
            category_count["university"] += 1

        for category, keywords in categories.items():
            if any(keyword in title for keyword in keywords):
                category_count[category] += 1
                if category == "sport":
                    sports_priority = True  # Mark if a sports event is present


    # Prioritize sports category
    if sports_priority:
        return "sport"

    # Get the dominant category
    dominant_category = max(category_count, key=category_count.get)
    return dominant_category

def calculate_average_event_time(events):
    """Calculate the average start time of events."""
    if not events:
        return None

    total_seconds = 0
    for event in events:
        start_time = event.get("start_time")
        if start_time:
            event_time = parser.isoparse(start_time).replace(tzinfo=timezone.utc)
            total_seconds += event_time.timestamp()

    avg_timestamp = total_seconds / len(events)
    avg_time = datetime.fromtimestamp(avg_timestamp, tz=timezone.utc)
    return avg_time

def get_images_from_recommendation(recommendations, clothing_items):
    selected_items = []
    for recommendation in recommendations:
        tags = recommendation.get("tags", [])
        for item in clothing_items:
            item_tags = item.get("tags", [])
            # Check if any tag matches
            if any(tag in item_tags for tag in tags):
                selected_items.append({"image_url": item["image_url"], "tags": item_tags})
    return selected_items





# OpenAI Recommendation Logic
def recommend_clothing_with_openai(weather, remaining_events, clothing_items, available_tags):
    """Use OpenAI to recommend clothing items based on weather, events, and available tags."""
    # Format weather data
    weather_context = f"The current temperature is {weather['temp']}°C with {weather['weather']}."

    # Format remaining events with fallback for missing keys
    if not remaining_events:
        # No events left for today, generate a weather-based quick statement
        prompt = (
            f"Give me a light-hearted summary of the weather and recommendation on what I should wear, and short justification on the recommendation, in a very short paragraph.:\n"
            f"- Weather: {weather_context}\n"
        )

    # Call OpenAI API
        try:
            response = openai.chat.completions.create(
                model="gpt-4",  # Replace with gpt-3.5-turbo if gpt-4 access is unavailable
                messages=[
                    {"role": "system", "content": "You are a personal assistant giving me advice."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
                temperature=0.7,
            )
            # Extract and return content from response
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error generating clothing recommendation: {str(e)}")

    # if remaining_events
    tags_context = f"Available tags are: {', '.join(available_tags)}."
    
    # Calculate dominant event category and average event time
    dominant_category = calculate_dominant_event_category(remaining_events)
    avg_event_time = calculate_average_event_time(remaining_events)

    event_context = " ".join([
            f"{event.get('title', 'Untitled Event')} at {event.get('location', 'No location specified')}"
            for event in remaining_events
    ])

    # Format clothing items
    clothing_context = "\n".join([
        f"Clothing Item {i+1}: {item['tags']} (Image: {item['image_url']})"
        for i, item in enumerate(clothing_items)
    ])

    # Create prompt for OpenAI
    prompt = (
        f"Based on the following information, recommend a top, bottom, shoes, jacket clothing item tailored to the dominant event category:\n"
        f"- Weather: {weather_context}\n"
        f"- Events: {event_context}\n"
        f"- Dominant Category: {dominant_category}\n"
        f"- Tags: {tags_context}\n"
        f"- Clothing Items:\n{clothing_context}\n\n"
        f"Provide the response strictly in this JSON format:\n"
        f"[{{\"tags\": \"[tag1], [tag2]\", \"image_url\": \"https://example.com/image1.jpg\"}}]"
    )
    # maybe for streamlit provide justification, display, don't

    # Call OpenAI API
    try:
        response = openai.chat.completions.create(
            model="gpt-4",  # Replace with gpt-3.5-turbo if gpt-4 access is unavailable
            messages=[
                {"role": "system", "content": "You are a fashion stylist and clothing analyst."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        print("OpenAI Prompt:", prompt)

        # Extract the OpenAI response content
        response_content = response.choices[0].message.content

        # Parse the content as JSON
        recommendations = json.loads(response_content)
        return recommendations
    except json.JSONDecodeError as e:
        raise Exception(f"Error parsing OpenAI response: {e}")
    except Exception as e:
        raise Exception(f"Error generating clothing recommendation: {e}")
    
# Main Logic
def main():
    weather = fetch_weather()
    remaining_events = fetch_remaining_events()
    clothing_items = fetch_clothing_items()

    if not weather:
        print("Weather data is missing.")
        return
    if not clothing_items:
        print("No clothing items available.")
        return

    available_tags = [
        "🔴 Red", "🔵 Blue", "🟢 Green", "🟤 Brown", "🩷 Pink", "⚫ Black", "⚪ White",
        "💜 Purple", "🟡 Yellow", "🟠 Orange", "⚪ Silver",
        "👕 T-shirt", "👚 Sweatshirt", "🧥 Hoodie", "🧣 Sweater", "🧣 Cardigan",
        "🧥 Jacket", "🧥 Puffer", "👖 Trousers", "👖 Jeans", "👖 Joggers",
        "🩳 Shorts", "👗 Long Skirt", "👗 Short Skirt", "👟 Sneakers", "👢 Boots",
        "🧵 Cotton", "👖 Denim", "👜 Leather", "🧶 Wool", "🧵 Polyester", "🎾 Mesh",
        "⬛ Solid", "➖ Striped", "🏁 Checked", "🟫 Camo", "🌸 Festive",
        "🎽 Casual", "🕶 Streetwear", "👟 Sporty", "🤵 Formal", "🎉 Party", "💼 Work",
        "🤏 Slim Fit", "📦 Baggy", "🎯 Regular Fit",
    ]

    try:
        recommendations = recommend_clothing_with_openai(
            weather, remaining_events, clothing_items, available_tags
        )
        if not recommendations:
            print("No recommendations generated by OpenAI.")
            return

        outfit_images = get_images_from_recommendation(recommendations, clothing_items)
        if not outfit_images:
            print("No outfit images matched the recommendations.")
            return

        print("Recommendations:", recommendations)
        print("Outfit Images:", outfit_images)
        return recommendations, outfit_images
    except Exception as e:
        print(f"Error in recommendation generation: {e}")

if __name__ == "__main__":
    main()
