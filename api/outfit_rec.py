import json
import openai
from supabase import create_client, Client
from datetime import datetime, timezone
from dotenv import load_dotenv
from dateutil import parser
import os
import re

# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not openai.api_key:
    raise Exception("Supabase or OpenAI credentials are missing. Check your environment variables.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Organize tags into categories
category_keywords = {
    "top": ["👕 T-shirt", "👚 Sweatshirt", "👚 Hoodie", "🧣 Sweater", "🧣 Cardigan"],
    "bottom": ["👖 Trousers", "👖 Jeans", "👖 Joggers", "🩳 Shorts", "👗 Long Skirt", "👗 Short Skirt"],
    "jacket": ["🧥 Jacket", "🧥 Puffer", "🧥 Blazer"],
    "shoes": ["👟 Sneakers", "👢 Boots"],
}

# Additional attributes
attributes = {
    "color": ["🔵 Blue", "🟢 Green", "🟤 Brown", "⚫ Black", "⚪ Silver", "🔴 Red"],
    "material": ["🧵 Polyester", "Suede", "🎾 Mesh"],
    "pattern": ["⬛ Solid", "➖ Striped"],
    "style": ["🎽 Casual", "🤵 Formal", "💼 Work"],
    "fit": ["🎯 Regular Fit"],
}

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


def calculate_dominant_event_category(events):
    """Determine the dominant category of events."""
    categories = {
        "university": [],
        "work": ["meeting", "office", "work"],
        "dining": ["brunch", "lunch", "dinner"],
        "social": ["party", "club", "dinner", "gathering", "games"],
        "sport": ["gym", "bouldering", "running", "exercise"],
        "leisure": ["movie", "museum", "musical", "picnic", "festival"],
        "appointment": ["appointment"],
        "festive": ["christmas", "birthday", "new years"]
    }
    
    university_locations = ["Dyson Building", "Library", "Imperial College London"]

    category_count = {key: 0 for key in categories}
    sports_priority = False  # Track if sports events should take priority

    for event in events:
        title = event.get("title", "").lower()
        location = str(event.get("location", "")).lower()  # Ensure location is a string
        duration = event.get("duration", 0)  # Duration in hours (default 0 if missing)

        if any(loc.lower() in location for loc in university_locations):
            category_count["university"] += duration

        for category, keywords in categories.items():
            if any(keyword in title for keyword in keywords):
                category_count[category] += duration
                if category == "sport":
                    sports_priority = True  # Mark if a sports event is present

    # Prioritize sports category
    if sports_priority:
        return "sport"

    # Get the dominant category
    dominant_category = max(category_count, key=category_count.get)
    return dominant_category


def get_images_from_recommendation(recommendations, clothing_items):
    """Retrieve clothing items from Supabase matching recommended tags and categories."""
    selected_items = {}
    used_items = set()  # Track already selected items to avoid duplicates

    for recommendation in recommendations:
        category = recommendation.get("category")
        recommendation_tags = recommendation.get("tags", "").split(", ")
        best_match = None
        best_match_score = 0

        # Filter clothing items strictly by category
        category_specific_items = [
            item for item in clothing_items if category in category_keywords
            and any(tag in category_keywords[category] for tag in item.get("tags", []))
        ]

        for item in category_specific_items:
            if item["image_url"] in used_items:
                continue  # Skip already used items

            item_tags = item.get("tags", [])
            if category == "top" and not any(tag in ["👕 T-shirt", "👚 Sweatshirt", "👚 Hoodie", "🧣 Sweater", "🧣 Cardigan"] for tag in item_tags):
                continue  # Ensure item matches the "top" category
            if category == "bottom" and not any(tag in ["👖 Trousers", "👖 Jeans", "👖 Joggers", "🩳 Shorts", "👗 Long Skirt", "👗 Short Skirt"] for tag in item_tags):
                continue  # Ensure item matches the "bottom" category
            if category == "jacket" and not any(tag in ["🧥 Jacket", "🧥 Puffer", "🧥 Blazer"] for tag in item_tags):
                continue  # Ensure item matches the "jacket" category
            if category == "shoes" and not any(tag in ["👟 Sneakers", "👢 Boots"] for tag in item_tags):
                continue  # Ensure item matches the "shoes" category

            # Match with additional attributes
            attribute_score = sum(
                1 for attr_list in attributes.values() for attr in attr_list if attr in item_tags
            )

            # Calculate total match score
            match_score = len(set(recommendation_tags) & set(item_tags)) + attribute_score

            if match_score > best_match_score:
                best_match = {"image_url": item["image_url"], "tags": item_tags}
                best_match_score = match_score

        if best_match:
            selected_items[category] = best_match
            used_items.add(best_match["image_url"])  # Mark item as used
        

    return selected_items




# OpenAI Recommendation Logic
def recommend_clothing_with_openai(weather, remaining_events, clothing_items):
    
    """Use OpenAI to recommend clothing items based on weather, events, and available tags."""
    # Format weather data
    weather_context = f"The current temperature is {weather['temp']}°C with {weather['weather']}."

    # Format remaining events with fallback for missing keys
    if not remaining_events:
        # No events left for today, generate a weather-based quick statement
        prompt = (
            f"Give me a light-hearted general recommendation based on the weather, in a very short paragraph (maximum 3 lines).:\n"
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
            # Extract general recommendation text
            general_recommendation = response.choices[0].message.content.strip()
            # print("Raw OpenAI Response:", general_recommendation)

            # Return a structured format for compatibility
            return {
                "general_recommendation": general_recommendation,
                "outfit_recommendation": None
            }

        except Exception as e:
            raise Exception(f"Error generating clothing recommendation: {str(e)}")
    
    # For cases with remaining events, process outfit recommendations
    try:
        # Calculate dominant event category and average event time
        dominant_category = calculate_dominant_event_category(remaining_events)
        available_tags_by_category = {key: [] for key in category_keywords}

        # Categorize clothing items
        for item in clothing_items:
            item_tags = item.get("tags", [])
            for category, keywords in category_keywords.items():
                if any(keyword in item_tags for keyword in keywords):
                    available_tags_by_category[category].extend(item_tags)
    
        # Remove duplicates and normalize tags
        available_tags_by_category = {key: list(set(tags)) for key, tags in available_tags_by_category.items()}

        # Debugging: Print available tags by category
        # print("Available Tags by Category:", available_tags_by_category)

        # Create prompt for OpenAI
        prompt = (
            f"The weather is {weather['temp']}°C with {weather['weather']}.\n"
            f"The dominant event category is '{dominant_category}'.\n"
            f"Available clothing item tags by category are:\n"
            f"- Tops: {available_tags_by_category['top']}\n"
            f"- Bottoms: {available_tags_by_category['bottom']}\n"
            f"- Jackets: {available_tags_by_category['jacket']}\n"
            f"- Shoes: {available_tags_by_category['shoes']}\n"
            f"Available attributes:\n"
            f"- Colors: {attributes['color']}\n"
            f"- Materials: {attributes['material']}\n"
            f"- Patterns: {attributes['pattern']}\n"
            f"- Styles: {attributes['style']}\n"
            f"- Fits: {attributes['fit']}\n"
            f"Recommend one top, one bottom, one jacket, and one pair of shoes, ensuring they align with the weather, the dominant event category, and these attributes.\n"
            f"Output the recommendation in JSON format like this:\n"
            f"["
            f"  {{\"tags\": \"[tag1], [tag2]\", \"category\": \"top\"}},"
            f"  {{\"tags\": \"[tag3], [tag4]\", \"category\": \"bottom\"}},"
            f"  {{\"tags\": \"[tag5], [tag6]\", \"category\": \"jacket\"}},"
            f"  {{\"tags\": \"[tag7], [tag8]\", \"category\": \"shoes\"}}"
            f"]"
        )

        # print("OpenAI Prompt:", prompt) # Debugging

        # maybe for streamlit provide justification, display, don't

        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4",  # Replace with gpt-3.5-turbo if gpt-4 access is unavailable
            messages=[
                {"role": "system", "content": "You are a fashion stylist and clothing analyst."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0.7,
        )

        raw_response = response.choices[0].message.content
        # print("Raw OpenAI Response:", raw_response) # Debugging

        # Extract JSON content from response using regex
        json_match = re.search(r"\[.*\]", raw_response, re.DOTALL)
        if not json_match:
            raise ValueError("JSON content not found in OpenAI response.")
        json_content = json_match.group(0)

        # print("Extracted JSON Content:", json_content)  # Debugging: Print extracted JSON

        # Parse JSON content
        recommended_tags = json.loads(json_content)

        if not isinstance(recommended_tags, list):
            raise ValueError("OpenAI response is not a list of recommendations.")
        
        return {
            "general_recommendation": None,
            "outfit_recommendation": recommended_tags
        }
    
    except Exception as e:
        raise Exception(f"Error generating recommendation: {str(e)}")
    
# Main Logic
def main():
    weather = fetch_weather()
    # print("Weather Data:", weather)

    remaining_events = fetch_remaining_events()
    # print("Remaining Events:", remaining_events)

    clothing_items = fetch_clothing_items()
    # print("Clothing Items:", clothing_items)

    if not weather:
        print("Weather data is missing.")
        return None  # Return None

    if not clothing_items:
        print("No clothing items available.")
        return None  # Return None

    try:
        recommendations = recommend_clothing_with_openai(weather, remaining_events, clothing_items)
        # Handle general recommendation
        if recommendations["general_recommendation"]:
            print(recommendations["general_recommendation"])
            return recommendations["general_recommendation"]

        # Handle outfit recommendation
        if recommendations["outfit_recommendation"]:
            matched_items = get_images_from_recommendation(recommendations["outfit_recommendation"], clothing_items)
            print("Outfit Recommendation:", matched_items)
            return matched_items

    except Exception as e:
        print(f"Error generating recommendation: {e}")


if __name__ == "__main__":
    main()
