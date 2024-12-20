import sqlite3
import datetime
from weather import get_weather_data
from gcalendar import get_upcoming_events_today

# Connect to the database in the 'data/' folder
conn = sqlite3.connect("data/iot_wardrobe.db")
cursor = conn.cursor()

# Create table for logging data
cursor.execute('''
CREATE TABLE IF NOT EXISTS data_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    feels_like REAL,
    temp_min REAL,
    temp_max REAL,
    description TEXT,
    event_title TEXT,
    event_time TEXT
)
''')
conn.commit()

def log_data():
    """Fetch weather and calendar data, and log into the database."""
    # Get weather data
    weather = get_weather_data()
    if weather:
        feels_like = weather.get("feels_like")
        temp_min = weather.get("temp_min")
        temp_max = weather.get("temp_max")
        description = weather.get("description")
    else:
        feels_like = temp_min = temp_max = description = None

    # Get calendar data
    events = get_upcoming_events_today()  # Returns a list of upcoming events
    event_title = events[0]['title'] if events else None
    event_time = events[0]['start_time'] if events else None

    # Log data into the database
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute('''
    INSERT INTO data_log (timestamp, feels_like, temp_min, temp_max, description, event_title, event_time)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, feels_like, temp_min, temp_max, description, event_title, event_time))
    conn.commit()
    print(f"Logged data at {timestamp}")

if __name__ == "__main__":
    log_data()
