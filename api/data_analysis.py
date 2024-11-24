import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# Connect to the database
conn = sqlite3.connect("data/iot_wardrobe.db")

# Load data into a pandas DataFrame
query = "SELECT * FROM data_log"
df = pd.read_sql_query(query, conn)

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Plot temperature trends
plt.figure(figsize=(10, 5))
plt.plot(df['timestamp'], df['feels_like'], label="Feels Like Temp (°C)")
plt.plot(df['timestamp'], df['temp_min'], label="Min Temp (°C)", linestyle='--')
plt.plot(df['timestamp'], df['temp_max'], label="Max Temp (°C)", linestyle='--')
plt.xlabel("Timestamp")
plt.ylabel("Temperature (°C)")
plt.title("Temperature Trends Over Time")
plt.legend()
plt.show()

# Analyze weather conditions
weather_counts = df['description'].value_counts()
plt.figure(figsize=(8, 4))
weather_counts.plot(kind='bar')
plt.title("Weather Conditions Frequency")
plt.xlabel("Condition")
plt.ylabel("Frequency")
plt.show()

# Example: Event correlation analysis
if 'event_title' in df.columns:
    event_weather = df[['event_title', 'description']].dropna()
    print("Weather conditions during events:")
    print(event_weather.groupby('event_title')['description'].value_counts())
