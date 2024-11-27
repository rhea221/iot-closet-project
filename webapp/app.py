import streamlit as st
import pandas as pd
from PIL import Image
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timezone
import matplotlib.pyplot as plt

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
            "tags": tags,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        # Insert data into Supabase table
        response = supabase.table("closet-items").insert(data).execute()
        
        # Check for errors in the response
        if hasattr(response, 'status_code') and response.status_code != 201:
            raise Exception(f"Error: {response.json()}")

        # Log success
        st.info(f"Supabase response: {response.data}")
        return True
    except Exception as e:
        st.error(f"Error saving metadata to Supabase: {e}")
        return False
    
# Weather Data ------------------------------------------
def fetch_weather_data():
    """Fetch weather data from the Supabase table."""
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

tab1, tab2 = st.tabs(["My Closet", "Weather Data"])

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
        st.image(image, caption="Uploaded Image", use_container_width=True)

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
import matplotlib.pyplot as plt

with tab2:
    # Weather Data Section
    st.header("Weather Data")

    # Fetch data and display
    weather_data = fetch_weather_data()

    if weather_data:
        # Convert data to DataFrame for better display
        df = pd.DataFrame(weather_data)

        # Ensure 'created_at' is in datetime format with error handling
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df = df.dropna(subset=["created_at"])  # Remove invalid dates

        # Sort data by timestamp for proper time-series plotting
        df = df.sort_values(by="created_at")

        # Display relevant columns
        st.write("Latest Weather Data:")
        st.dataframe(df[["created_at", "temp", "feels_like", "weather", "pop"]])

        # Time-Series Temperature Trends
        st.write("Temperature Trends Over Time:")
        plt.figure(figsize=(10, 6))
        plt.plot(df["created_at"], df["temp"], label="Temperature (°C)", marker="o")
        plt.xlabel("Time")
        plt.ylabel("Temperature (°C)")
        plt.title("Temperature Trends Over Time")
        plt.grid(True)
        plt.xticks(rotation=45)

        # Annotate Weather Conditions
        for i, row in df.iterrows():
            plt.text(row["created_at"], row["temp"], row["weather"], fontsize=8, rotation=45, ha="right")

        plt.legend()
        st.pyplot(plt)

        # Aggregated Statistics
        st.write("Summary Statistics:")
        stats = df[["temp", "feels_like", "pop"]].describe()
        st.table(stats)
    else:
        st.warning("No weather data found. Please check your data source.")
