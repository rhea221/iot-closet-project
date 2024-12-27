import json
import streamlit as st
import pandas as pd
from PIL import Image
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timezone
import sys
import matplotlib.pyplot as plt  # For additional visualization
from datetime import timedelta

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.outfit_rec import main as fetch_recommendation, fetch_weather, fetch_remaining_events

# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    st.error("Supabase credentials are missing. Check your environment variables.")
    st.stop()
supabase: Client = create_client(supabase_url, supabase_key)

# -----------------------------------
# Helper Functions
# -----------------------------------

def generate_unique_filename(extension):
    """Generate a unique filename using UUID."""
    return f"{uuid.uuid4()}.{extension}"

def fetch_calendar_events():
    """Fetch all calendar events from the Supabase table."""
    try:
        table_name = "calendar-events"
        response = supabase.table(table_name).select("*").execute()
        if response.data:
            return response.data
        else:
            print("No calendar events available.")
            return None
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        return None

def fetch_all_clothes():
    """Fetch all clothing items from Supabase."""
    try:
        response = supabase.table("closet-items").select("*").execute()
        return response.data or []
    except Exception as e:
        st.error(f"Error fetching clothes: {e}")
        return []

def upload_image_to_supabase(file, file_name):
    """Upload image to Supabase and return the public URL."""
    try:
        response = supabase.storage.from_("closet-images").upload(file_name, file)
        if not response.path:
            raise Exception("Upload failed. No path returned.")
        public_url = f"{supabase_url}/storage/v1/object/public/closet-images/{file_name}"
        return public_url
    except Exception as e:
        st.error(f"Error uploading image: {e}")
        return None

def save_image_metadata_to_supabase(image_url, tags, name):
    """Save image metadata to Supabase database."""
    try:
        data = {
            "image_url": image_url,
            "tags": tags,  # Save tags as a JSON array
            "name": name,  # Save the clothing item's name
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        response = supabase.table("closet-items").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error saving metadata to Supabase: {e}")
        return False

def fetch_weather_data():
    """Fetch current weather data from the Supabase table."""
    try:
        table_name = "weather-data"
        response = supabase.table(table_name).select("*").execute()
        return response.data if response.data else None
    except Exception as e:
        st.error(f"Error fetching weather data: {e}")
        return None

def send_to_laundry(selected_items):
    """Mark selected items as 'laundry' in Supabase."""
    try:
        for item in selected_items:
            supabase.table("closet-items").update({"status": "laundry"}).match({"id": item["id"]}).execute()
        st.success("Selected items sent to laundry!")
    except Exception as e:
        st.error(f"Error sending items to laundry: {e}")

def return_from_laundry(selected_laundry_items):
    """Update the status of selected laundry items to make them available."""
    try:
        for item in selected_laundry_items:
            supabase.table("closet-items").update({"status": None}).match({"id": item["id"]}).execute()
        st.success("Selected items returned to the closet!")
    except Exception as e:
        st.error(f"Error returning items from laundry: {e}")

def plot_heatmap(dataframe, x_col, y_col, agg_col, title, xlabel, ylabel):
    """Create a heatmap from a pivot table."""
    pivot_table = dataframe.pivot_table(index=y_col, columns=x_col, values=agg_col, aggfunc='count', fill_value=0)
    plt.figure(figsize=(12, 8))
    plt.imshow(pivot_table, cmap='Blues', interpolation='nearest')
    plt.colorbar()
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(range(len(pivot_table.columns)), pivot_table.columns, rotation=90)
    plt.yticks(range(len(pivot_table.index)), pivot_table.index)
    st.pyplot(plt)

# -----------------------------------
# Streamlit Tabs
# -----------------------------------

st.title("IoT Closet Manager")

tab1, tab2, tab3, tab4 = st.tabs(["Recommendations", "My Closet", "Trends Overview", "Time-Series Analysis"])

# Recommendations --------------------------------
# Define a dark mode style
dark_mode_style = """
<style>
    body {
        background-color: #1e1e1e;
        color: #f1f1f1;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #f1f1f1;
    }
    p, div {
        color: #c1c1c1;
    }
</style>
"""

# Add the dark mode style
st.markdown(dark_mode_style, unsafe_allow_html=True)

# Recommendation Section
with tab1:
    # Add the dark mode style
    st.markdown(dark_mode_style, unsafe_allow_html=True)

    # Landing Section
    with st.container():
        try:
            # Fetch summarized data
            weather = fetch_weather()
            remaining_events = fetch_remaining_events()

            if weather:
                weather_summary = f"The current temperature is {weather['temp']}°C with {weather['weather']}."
            else:
                weather_summary = "Weather data is currently unavailable."

            if remaining_events:
                event_summary = f"You have {len(remaining_events)} event(s) left today."
            else:
                event_summary = "No events found for today."

            st.subheader(f"Hello! {weather_summary} {event_summary}")
        except Exception as e:
            st.error(f"Error fetching data: {e}")



    if st.button("Get Outfit Recommendation"):
        with st.spinner("Fetching recommendation..."):
            try:
                recommendations = fetch_recommendation()

                # Handle general recommendation
                if isinstance(recommendations, str):
                    st.success("Recommendation Generated!")
                    st.text_area("General Recommendation", recommendations, height=150)
                elif recommendations and isinstance(recommendations, dict):
                    st.success("Recommendation Generated!")
                    st.subheader("Your Outfit Recommendation:")
                    for category, item in recommendations.items():
                        image_html = f"""
                        <div style="text-align: center; margin-bottom: 20px;">
                            <img src="{item['image_url']}" style="width: 200px; height: auto; border-radius: 15px; box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);"/>
                            <p style="margin-top: 10px; font-size: 16px; font-weight: bold;">{item['name']}</p>
                            <p style="font-size: 14px;">{category.capitalize()} - {', '.join(item['tags'])}</p>
                        </div>
                        """ 
                        st.markdown(image_html, unsafe_allow_html=True)
                else:
                    st.warning("No recommendation generated. Please check your data.")
            except Exception as e:
                st.error(f"Error generating recommendation: {e}")


with tab2:
    # Upload Image Section
    uploaded_file = st.file_uploader("Upload a clothing item...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        # Display the uploaded image
        file_extension = uploaded_file.name.split('.')[-1]
        unique_filename = generate_unique_filename(file_extension)
        image = Image.open(uploaded_file)
        
        # Center and style the image with CSS
        st.markdown(
            """
            <style>
            .centered-image {
                display: flex;
                justify-content: center;
            }
            .rounded-image {
                border-radius: 13px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="centered-image">', unsafe_allow_html=True)
            st.image(image, caption="Uploaded Image", use_container_width=False, width=300, output_format="PNG", clamp=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Upload to Supabase
        if st.button("Upload Image"):
            with open(unique_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())
            image_url = upload_image_to_supabase(unique_filename, unique_filename)
            if image_url:
                st.success(f"Image uploaded successfully: {image_url}")
                st.session_state["image_url"] = image_url  # Save the URL in session state

    # Check if image URL exists in session state
    if "image_url" in st.session_state:
        st.subheader("Add Details to Your Item")

        # Name field
        item_name = st.text_input("Enter a Name for this Clothing Item", key="item_name")

        # Dropdowns for tagging
        type = st.multiselect("Select Type:", ["👕 T-shirt", "👚 Sweatshirt", "👚 Hoodie", "🧣 Sweater", "🧣 Cardigan", "🧥 Jacket", "🧥 Puffer", "🧥 Blazer", "👖 Trousers", "👖 Jeans", "👖 Joggers", "🩳 Shorts", "👗 Long Skirt", "👗 Short Skirt", "👟 Sneakers", "👢 Boots"], key="type", max_selections=1)
        color = st.multiselect("Select Color:",  ["🔴 Red", "🔵 Blue", "🟢 Green", "🟤 Brown", "🩷 Pink", "⚫ Black", "⚪ White", "💜 Purple", "🟡 Yellow", "🟠 Orange", "⚪ Silver"], key="color", max_selections=3)
        material = st.multiselect("Select Material:", ["🧵 Cotton", "👖 Denim", "👜 Leather", "🧶 Wool", "🧵 Polyester", "🎾 Mesh", "Suede"], key="material", max_selections=1)
        pattern = st.multiselect("Select Pattern:", ["⬛ Solid", "➖ Striped", "🏁 Checked", "🟫 Camo", "🌸 Festive", "🌸 Print"], key="pattern", max_selections=1)
        style = st.multiselect("Select Style:", ["🎽 Casual", "🕶 Streetwear", "👟 Sporty", "🤵 Formal", "🎉 Party", "💼 Work"], key="style", max_selections=3)
        fit = st.multiselect("Select Fit:", ["🤏 Slim Fit", "📦 Baggy", "🎯 Regular Fit"], key="fit", max_selections=3)

        # Combine tags into a proper JSON array
        tags = [
            *color,
            *type,
            *material,
            *pattern,
            *style,
            *fit
        ]

        # Final confirmation to save
        if st.button("Confirm and Save Tags"):
            if item_name:  # Ensure the user has entered a name for the item
                if save_image_metadata_to_supabase(st.session_state["image_url"], tags, item_name):
                    st.success("Tags saved successfully!")
                    # Clear session state after saving
                    del st.session_state["image_url"]
                else:
                    st.error("Failed to save tags.")
            else:
                st.error("Please provide a name for the clothing item before saving.")



    st.subheader("My Closet")

    # Fetch all clothing items
    clothes = fetch_all_clothes()

    if clothes:
        # Display clothes not in laundry
        available_clothes = [item for item in clothes if item.get("status") != "laundry"]
        selected_for_laundry = []

        st.write("Available Clothes:")
        for item in available_clothes:
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(item["image_url"], width=100, caption=" ")
            with col2:
                checkbox = st.checkbox(f"{item['name']}", key=f"checkbox_{item['id']}")
                if checkbox:
                    selected_for_laundry.append(item)

        # Send selected items to laundry
        if st.button("Send to Laundry"):
            send_to_laundry(selected_for_laundry)

    # Fetch items currently in laundry
    try:
        laundry_items = [item for item in clothes if item.get("status") == "laundry"]
        if not laundry_items:
            st.info("No items are currently in the laundry.")
        else:
            st.write("Laundry Items:")
            selected_items = []
            for item in laundry_items:
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.image(item["image_url"], width=100, caption=" ")
                with col2:
                    checkbox = st.checkbox(f"{item['name']}", key=f"laundry-{item['id']}")
                    if checkbox:
                        selected_items.append(item)

            # Button to return selected items
            if st.button("Return to Closet"):
                if selected_items:
                    return_from_laundry(selected_items)
    except Exception as e:
        st.error(f"Error fetching laundry items: {e}")


# Database ------------------------------------------

def analyze_calendar_event_additions(events_data):
    """
    Analyze how frequently new calendar events are added over time.
    """
    if not events_data:
        st.warning("No calendar event data available for analysis.")
        return

    # Convert events data to DataFrame
    events_df = pd.DataFrame(events_data)
    events_df["created_at"] = pd.to_datetime(events_df["created_at"], errors="coerce")
    events_df.dropna(subset=["created_at"], inplace=True)

    # Group by date of addition
    events_df["date_added"] = events_df["created_at"].dt.date
    grouped = events_df.groupby("date_added").size().reset_index(name="new_events")

    # Plot the data
    st.line_chart(data=grouped.set_index("date_added"), use_container_width=True)

def analyze_closet_item_totals(closet_data):
    """
    Analyze the total number of closet items over time to track spending habits.
    """

    if not closet_data:
        st.warning("No closet item data available for analysis.")
        return

    # Convert closet data to DataFrame
    closet_df = pd.DataFrame(closet_data)
    closet_df["created_at"] = pd.to_datetime(closet_df["created_at"], errors="coerce")
    closet_df.dropna(subset=["created_at"], inplace=True)

    # Group by date (only date part, exclude time) for aggregation
    closet_df["date_added"] = closet_df["created_at"].dt.date
    grouped = closet_df.groupby("date_added").size().reset_index(name="new_items")

    # Calculate cumulative total for total items over time
    grouped["total_items"] = grouped["new_items"].cumsum()

    # Plot the data
    st.line_chart(data=grouped.set_index("date_added")[["total_items"]], use_container_width=True)

# Fetch weather and calendar data once at the start to reuse across tabs
weather_data = fetch_weather_data()
calendar_events = fetch_calendar_events()
closet_items = fetch_all_clothes()

# ------------------------------------------------------

# Tab 3: Trends Overview
with tab3:
    st.header("Trends Overview")

    # Weather Trends
    if weather_data:
        st.subheader("Weather Data Trends")
        weather_df = pd.DataFrame(weather_data)

        # Show weather counts as a bar chart
        st.bar_chart(weather_df["weather"].value_counts(), use_container_width=True)

    # Calendar Event Trends
    if calendar_events:
        st.subheader("Calendar Event Trends")
        event_df = pd.DataFrame(calendar_events)

        # Ensure start_time is in datetime format
        event_df["start_time"] = pd.to_datetime(event_df["start_time"], errors="coerce")
        event_df["duration"] = event_df["duration"].astype(float)
        event_df["date"] = event_df["start_time"].dt.date

        # Extract hours for heatmap
        event_df["hour"] = event_df["start_time"].dt.hour

        # Plot heatmap for event timings
        plot_heatmap(event_df, "hour", "date", "title", "Daily Event Heatmap", "Hour of Day", "Date")
    else:
        st.warning("No calendar events found. Please check your data source.")

# Tab 4: Time-Series Analysis
with tab4:
    st.header("Time-Series Analysis")

    # Weather Time-Series Analysis
    if weather_data:
        # Convert data to DataFrame
        weather_df = pd.DataFrame(weather_data)

        # Ensure 'created_at' is in datetime format
        weather_df["created_at"] = pd.to_datetime(weather_df["created_at"], errors="coerce")
        weather_df.dropna(subset=["created_at"], inplace=True)

        # Sort by 'created_at' for proper time-series plotting
        weather_df = weather_df.sort_values(by="created_at")

        # Line chart for temperature trends
        st.subheader("Temperature Trends Over Time")
        if "temp" in weather_df and "created_at" in weather_df:
            st.line_chart(data=weather_df.set_index("created_at")[["temp", "feels_like"]])
    else:
        st.warning("No weather data found. Please check your data source.")

    # Calendar and Closet Trends
    if calendar_events:
        st.subheader("Calendar Updates Over Time")
        analyze_calendar_event_additions(calendar_events)

    if closet_items:
        st.subheader("Total Clothes Over Time")
        analyze_closet_item_totals(closet_items)

