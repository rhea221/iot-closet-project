import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from supabase import create_client, Client

# Loads environment variables from .env
load_dotenv(dotenv_path="config/.env")
API_KEY = os.getenv("WEATHER_API_KEY") 

# Initialises Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    st.error("Supabase credentials are missing. Check your environment variables.")
    st.stop()
supabase: Client = create_client(supabase_url, supabase_key)

# Location coordinates for London
LAT = "52.240755"  
LON = "-0.896876"  

# Fetches current weather data from OpenWeather API
def get_weather_data():
    """Fetch current weather data from OpenWeatherMap API."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": LAT,
        "lon": LON,
        "appid": API_KEY,
        "units": "metric",  
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching weather data: {response.status_code}")
        return None

# Parses relevant weather information (feels like, temperature, description)
def parse_weather_data(data):
    """Parse and return relevant weather information."""
    if not data:
        return None

    return {
        "feels_like": data["main"].get("feels_like"),
        "temp": data["main"].get("temp"),
        "weather": data["weather"][0].get("description"),
        "pop": data.get("rain", {}).get("1h", 0),  # Rain volume in the last hour
    }

# Saves current weather data to Supabase
def save_weather_to_supabase(data):
    """Save current weather data to the Supabase database."""
    table_name = "weather-data"
    try:
        supabase.table(table_name).insert({
            "created_at": datetime.now(timezone.utc).isoformat(),  # Log current time in UTC
            "temp": data["temp"],
            "feels_like": data["feels_like"],
            "weather": data["weather"],
            "pop": data["pop"],
        }).execute()
        print("Weather data saved to Supabase!")
    except Exception as e:
        print(f"Error saving data to Supabase: {e}")

# Fetch and store current weather
if __name__ == "__main__":
    current_weather = get_weather_data()
    if current_weather:
        weather_info = parse_weather_data(current_weather)
        if weather_info:
            print("Current Weather Information:")
            print(f"- Temperature: {weather_info['temp']}°C")
            print(f"- Feels Like: {weather_info['feels_like']}°C")
            print(f"- Weather: {weather_info['weather'].capitalize()}")
            print(f"- Precipitation (last hour): {weather_info['pop']} mm")
            save_weather_to_supabase(weather_info)
        else:
            print("Failed to parse weather data.")
    else:
        print("Failed to retrieve weather data.")
