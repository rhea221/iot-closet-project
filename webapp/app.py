import streamlit as st
import pandas as pd
from PIL import Image
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timezone

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
def upload_image_to_supabase(file_path, file_name):
    """Upload image to Supabase and return the public URL."""
    try:
        with open(file_path, "rb") as file:
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
            "tags": tags,
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

tab1, tab2 = st.tabs(["My Closet", "My Database"])

# My Closet --------------------------------------
with tab1:
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
            st.image(image, caption="Uploaded Image", use_column_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Save uploaded image to a temporary file for Supabase upload
        temp_file_path = f"temp_{unique_filename}"
        image.save(temp_file_path)

        # Upload to Supabase
        if st.button("Upload Image"):
            image_url = upload_image_to_supabase(temp_file_path, unique_filename)
            os.remove(temp_file_path)  # Remove the temporary file
            if image_url:
                st.success(f"Image uploaded successfully: {image_url}")
                st.session_state["image_url"] = image_url  # Save the URL in session state

    # Check if image URL exists in session state
    if "image_url" in st.session_state:
        st.subheader("Add Tags to Your Item")

        # Dropdowns for tagging
        color = st.selectbox("Select Color:", ["#red", "#blue", "#green", "#yellow", "#pink", "#black", "#white"], key="color")
        type = st.selectbox("Select Type:", ["#tshirt", "#sweatshirt", "#jacket", "#pants", "#skirt", "#dress", "#shorts"], key="type")
        material = st.selectbox("Select Material:", ["#cotton", "#denim", "#leather", "#wool", "#polyester"], key="material")
        pattern = st.selectbox("Select Pattern:", ["#solid", "#striped", "#checked", "#polka-dot", "#floral"], key="pattern")

        # Combine tags and show confirmation
        tags = f"{color}, {type}, {material}, {pattern}"
        st.text(f"Your tags: {tags}")

        # Final confirmation to save
        if st.button("Confirm and Save Tags"):
            if save_image_metadata_to_supabase(st.session_state["image_url"], tags):
                st.success("Tags saved successfully!")
                # Clear session state after saving
                del st.session_state["image_url"]
            else:
                st.error("Failed to save tags.")

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
