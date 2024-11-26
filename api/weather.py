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
LAT = "51.509865"  
LON = "-0.118092"  

# Fetches weather data from OpenWeather (every 3 hours)
def get_weather_data():
    """Fetch weather data from OpenWeatherMap API."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": LAT,
        "lon": LON,
        "appid": API_KEY,
        "units": "metric",  
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error fetching weather data: {response.status_code}")
        return None

# Fetches 7-day weather forecast (once daily) 
def get_weather_forecast():
    url = f"http://api.openweathermap.org/data/2.5/forecast"
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
        print(f"Error fetching forecast data: {response.status_code}")
        return None

# Fetches relevant weather information (feels like, min/max temp, description)
def parse_weather_data(data):
    """Parse and return relevant weather information."""
    if not data:
        return None

    feels_like = data["main"].get("feels_like")
    temp_min = data["main"].get("temp_min")
    temp_max = data["main"].get("temp_max")
    description = data["weather"][0].get("description")

    return {
        "feels_like": feels_like,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "description": description,
    }

# Prints weather information
if __name__ == "__main__":
    weather_data = get_weather_data()
    if weather_data:
        weather_info = parse_weather_data(weather_data)
        if weather_info:
            print("Weather Information:")
            print(f"- Feels Like: {weather_info['feels_like']}°C")
            print(f"- Min Temperature: {weather_info['temp_min']}°C")
            print(f"- Max Temperature: {weather_info['temp_max']}°C")
            print(f"- Description: {weather_info['description'].capitalize()}")
        else:
            print("Could not parse weather information.")
    else:
        print("Failed to retrieve weather data.")

def save_weather_to_supabase(data, forecast=False):
    table_name = "weather-data"
    try:
        if forecast:
            # Save 5-day forecast
            for entry in data["list"]:
                forecast_day = datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S").date()
                supabase.table(table_name).insert({
                    "created_at": datetime.now(timezone.utc).isoformat(),  # Log current time in UTC
                    "temp": entry["main"]["temp"],
                    "feels_like": entry["main"]["feels_like"],
                    "weather": entry["weather"][0]["description"],
                    "pop": entry.get("pop", 0),
                    "forecast_day": forecast_day.isoformat()  # Use forecasted day
                }).execute()
        else:
            # Save current weather
            supabase.table(table_name).insert({
                "created_at": datetime.now(timezone.utc).isoformat(),  # Log current time in UTC
                "temp": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "weather": data["weather"][0]["description"],
                "pop": data.get("rain", {}).get("1h", 0),
            }).execute()
        print("Weather data saved to Supabase!")
    except Exception as e:
        print(f"Error saving data to Supabase: {e}")

# Fetches and stores current weather
current_weather = get_weather_data()
if current_weather:
    save_weather_to_supabase(current_weather)

# Fetches and stores 5-day forecast (optional)
forecast_weather = get_weather_forecast()
if forecast_weather:
    save_weather_to_supabase(forecast_weather, forecast=True)
