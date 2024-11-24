import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path="config/.env")
API_KEY = os.getenv("WEATHER_API_KEY")  # Replace with your API key if not using .env

# Set your location coordinates
LAT = "40.7128"  # Example: Latitude for New York
LON = "-74.0060"  # Example: Longitude for New York

def get_weather_data():
    """Fetch weather data from OpenWeatherMap API."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": LAT,
        "lon": LON,
        "appid": API_KEY,
        "units": "metric",  # Use 'imperial' for Fahrenheit
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error fetching weather data: {response.status_code}")
        return None

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
