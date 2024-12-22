import streamlit as st
import pandas as pd
from PIL import Image
from dotenv import load_dotenv
import os
import uuid
import openai
from supabase import create_client, Client
from datetime import datetime
import requests

# Loading environment variables
load_dotenv(dotenv_path="config/.env")

# Supabase Data Storage ----------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------

# Initialising Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    st.error("Supabase credentials are missing. Check your environment variables.")
    st.stop()
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    st.error("OpenAI API key is missing. Check your environment variables.")
    st.stop()

# Generating unique filenames using UUID
def generate_unique_filename(extension):
    return f"{uuid.uuid4()}.{extension}"

def generate_unique_filename(extension: str) -> str:
    """Generate a unique filename using a UUID."""
    return f"{uuid.uuid4()}.{extension}"

def upload_image_to_supabase(file, file_name: str) -> str:
    """Upload an image from Streamlit UploadedFile to Supabase Storage and return the public URL."""
    try:
        # Upload the binary content of the file
        response = supabase.storage.from_("closet-images").upload(file_name, file.read())

        # Check if the upload was successful
        if not response or not hasattr(response, 'path') or not response.path:
            raise Exception("Upload failed. No path returned.")
        
        # Construct the public URL manually
        public_url = f"{supabase_url}/storage/v1/object/public/closet-images/{file_name}"
        return public_url
    except Exception as e:
        raise Exception(f"Error uploading image to Supabase: {e}")


def get_image_tags(public_url: str) -> list:
    """Generate detailed tags for an image using OpenAI."""
    try:
        # Construct the prompt as role-based messages
        messages = [
            {"role": "system", "content": "Help me organise my closet items."},
            {
                "role": "user",
                "content": (
                    f"Analyze this clothing item image available at this URL: {public_url}. "
                    "Describe it in terms of the following attributes:\n"
                    "1. Material (e.g., cotton, polyester).\n"
                    "2. Clothing category (e.g., shirt, pants, jacket).\n"
                    "3. Style (e.g., casual, formal, sporty).\n"
                    "4. Weather suitability (e.g., suitable for hot, cold, rainy).\n"
                    "5. Event suitability (e.g., office, party, workout).\n"
                    "Return a list of tags representing these attributes."
                ),
            },
        ]

        # Call OpenAI API with updated syntax
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4",  # Use "gpt-3.5-turbo" if gpt-4 is unavailable
            messages=messages,
            max_tokens=100,
            temperature=0.7,
        )
        tags = response.choices[0].message.content
        return [tag.strip() for tag in tags.split(",") if tag.strip()]
    except Exception as e:
        raise Exception(f"Error generating image tags: {e}")




def save_clothing_item(image_url: str, tags: list) -> None:
    """Save a clothing item with tags to Supabase."""
    try:
        supabase.table("clothing_items").insert({
            "image_url": image_url,
            "tags": tags
        }).execute()
    except Exception as e:
        raise Exception(f"Error saving clothing item: {e}")

# Weather Data ------------------------------------------
# Fetching current weather data from the Supabase table
def fetch_weather_data():
    table_name = "weather-data"
    try:
        # Fetch the data from Supabase
        response = supabase.table(table_name).select("*").execute()

        # Check if the response contains data
        if response.data:
            return response.data
        else:
            st.warning("No weather data available in the table.")
            return None
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# Streamlit FrontEnd ------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------

st.title("IoT Closet Manager")

tab1, tab2 = st.tabs(["My Closet", "My Database"])

# My Closet --------------------------------------
with tab1:
    st.header("My Closet")

    # Image Upload
uploaded_file = st.file_uploader("Upload an image of your clothing item", type=["jpg", "png", "jpeg"])
if uploaded_file is not None:
    try:
        # Extract file name and extension dynamically
        file_extension = uploaded_file.name.split(".")[-1]
        file_name = generate_unique_filename(file_extension)

        # Upload the file to Supabase
        st.write("Uploading image to Supabase...")
        public_url = upload_image_to_supabase(uploaded_file, file_name)
        st.success(f"Image uploaded: {public_url}")
        st.image(public_url, caption="Uploaded Image", use_container_width=True)

        # Generate tags using OpenAI
        st.write("Generating tags using OpenAI...")
        tags = get_image_tags(public_url)
        st.success(f"Generated Tags: {', '.join(tags)}")

        # Save clothing item to Supabase
        st.write("Saving clothing item to Supabase...")
        save_clothing_item(public_url, tags)
        st.success("Clothing item saved successfully!")
    except Exception as e:
        st.error(f"Error: {e}")


# # Recommendation System
# if st.button("Get Outfit Recommendation"):
#     weather = fetch_weather()
#     events = fetch_events()

#     st.write(f"Current Weather: {weather}")
#     st.write(f"Upcoming Events: {', '.join(events)}")

#     # Fetch matching outfits
#     recommended = []  # Placeholder for recommendation logic

#     if recommended:
#         st.write("Recommended Outfits:")
#         for item in recommended:
#             st.image(item['image_url'], caption=f"Tags: {', '.join(item['tags'])}")
#     else:
#         st.write("No matching outfits found.")


# Weather Data ------------------------------------------
with tab2:
    st.header("My Database")

    # Fetch data and display
    weather_data = fetch_weather_data()

    if weather_data:
        # Convert data to DataFrame
        df = pd.DataFrame(weather_data)

        # Ensure 'created_at' is in datetime format
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df = df.dropna(subset=["created_at"])  # Remove invalid dates

        # Sort by 'created_at' for proper time-series plotting
        df = df.sort_values(by="created_at")

        # Line chart for temperature trends
        st.subheader("Temperature Trends Over Time")
        if "temp" in df and "created_at" in df:
            st.line_chart(data=df.set_index("created_at")[["temp", "feels_like"]])

        # Show the latest weather data as a table
        st.subheader("Latest Weather Data")
        st.dataframe(df[["created_at", "temp", "feels_like", "weather", "pop"]])
    else:
        st.warning("No weather data found. Please check your data source.")

 # Calendar Events Section
    st.subheader("Today's Events")

    def fetch_calendar_events():
        """Fetch today's calendar events from Supabase."""
        table_name = "calendar-events"
        try:
            response = supabase.table(table_name).select("*").execute()
            if response.data:
                return response.data
            else:
                st.warning("No calendar events available.")
                return None
        except Exception as e:
            st.error(f"Error fetching calendar events: {e}")
            return None

    # Display calendar events
    calendar_events = fetch_calendar_events()
    if calendar_events:
        # Convert data to DataFrame
        events_df = pd.DataFrame(calendar_events)
        events_df["start_time"] = pd.to_datetime(events_df["start_time"], errors="coerce")
        events_df = events_df.dropna(subset=["start_time"]).sort_values(by="start_time")

        st.write("Today's Events")
        st.dataframe(events_df[["title", "start_time"]])
    else:
        st.warning("No events to display.")