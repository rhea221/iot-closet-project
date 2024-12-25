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

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.outfit_rec import main as fetch_recommendation

# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Supabase Data Storage ----------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")


if not supabase_url or not supabase_key:
    st.error("Supabase credentials are missing. Check your environment variables.")
    st.stop()
supabase: Client = create_client(supabase_url, supabase_key)

# Helper functions
def generate_unique_filename(extension):
    """Generate a unique filename using UUID."""
    return f"{uuid.uuid4()}.{extension}"

# My Closet --------------------------------------
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

def save_image_metadata_to_supabase(image_url, tags):
    """Save image metadata to Supabase database."""
    try:
        data = {
            "image_url": image_url,
            "tags": tags,  # Save tags as a JSON array
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        # Insert data into Supabase table
        response = supabase.table("closet-items").insert(data).execute()

        # Check for errors in the response
        if hasattr(response, "status_code") and response.status_code != 201:
            raise Exception(f"Error: {response.json()}")

        # Log success
        st.info(f"Supabase response: {response.data}")
        return True
    except Exception as e:
        st.error(f"Error saving metadata to Supabase: {e}")
        return False


# Weather Data ------------------------------------------
def fetch_weather_data():
    """Fetch current weather data from the Supabase table."""
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

# Streamlit App ------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------

st.title("IoT Closet Manager")

tab1, tab2, tab3 = st.tabs(["Recommendations", "My Closet", "My Database"])

# Recommendations --------------------------------
with tab1:
    st.header("Recommendations")

    # Trigger Recommendation System
    if st.button("Get Outfit Recommendation"):
        with st.spinner("Fetching recommendation..."):
            try:
                # Fetch recommendations and outfit images
                recommendations = fetch_recommendation()

                if recommendations:
                    st.success("Recommendation Generated!")
                    st.subheader("Your Outfit Recommendation:")
                    
                    # Display images with rounded corners and cleaner captions
                    for category, item in recommendations.items():
                        image_html = f"""
                        <div style="text-align: center; margin-bottom: 20px;">
                            <img src="{item['image_url']}" style="width: 200px; height: auto; border-radius: 15px; box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);"/>
                            <p style="margin-top: 10px; font-size: 16px; font-weight: bold; color: #333;">{category.capitalize()}</p>
                            <p style="font-size: 14px; color: #555;">{', '.join(item['tags'])}</p>
                        </div>
                        """
                        st.markdown(image_html, unsafe_allow_html=True)
                else:
                    st.warning("No recommendation generated. Please check your data.")
            except Exception as e:
                st.error(f"Error generating recommendation: {e}")
                
# My Closet --------------------------------------
with tab2:
    st.header("My Closet")

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
        st.subheader("Add Tags to Your Item")

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
            if save_image_metadata_to_supabase(st.session_state["image_url"], tags):
                st.success("Tags saved successfully!")
                # Clear session state after saving
                del st.session_state["image_url"]
            else:
                st.error("Failed to save tags.")

            #"Start Over" button
            if st.button("Start Over"):
                st.session_state.clear()  # Clear all session state to reset the app
                st.experimental_rerun()  # Rerun the app to start fresh

# Database ------------------------------------------
with tab3:
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