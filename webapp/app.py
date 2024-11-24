import streamlit as st
from PIL import Image
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timezone
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG for detailed output
    format="%(asctime)s [%(levelname)s] %(message)s",  # Log format with timestamp and level
    handlers=[
        logging.StreamHandler(),  # Output logs to the console
        logging.FileHandler("debug.log", mode="w")  # Save logs to a file named debug.log
    ]
)

# Example debug log to verify configuration
logging.info("Debug logging is enabled.")



# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

if not supabase_url or not supabase_key:
    st.error("Supabase credentials are missing. Check your environment variables.")
    st.stop()

# Helper functions
def generate_unique_filename(extension):
    """Generate a unique filename using UUID."""
    return f"{uuid.uuid4()}.{extension}"

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
        # Prepare data
        data = {
            "image_url": image_url,
            "tags": tags[:255],  # Truncate if necessary
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Log data for debugging
        st.write("Data being sent to Supabase:", data)

        # Insert into Supabase
        response = supabase.table("closet-items").insert(data).execute()

        # Log response for debugging
        st.write("Supabase response:", response)

        if response.error:
            st.error(f"Supabase error: {response.error}")
            return False
        return True
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return False


# Initialize session state
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "image_url" not in st.session_state:
    st.session_state.image_url = None

# Streamlit App
st.title("IoT Closet Manager")

# Upload Image Section
uploaded_file = st.file_uploader("Upload a clothing item...", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    # Display the uploaded image
    file_extension = uploaded_file.name.split('.')[-1]
    unique_filename = generate_unique_filename(file_extension)
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_container_width=True)

    # Save the image in session state
    st.session_state.uploaded_image = image
    if st.button("Upload Image"):
        with open(unique_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())
        image_url = upload_image_to_supabase(unique_filename, unique_filename)
        if image_url:
            st.session_state.image_url = image_url
            st.success(f"Image uploaded successfully: {image_url}")

# Check if an image has been uploaded
if st.session_state.image_url:
    st.subheader("Add Tags to Your Item")
    color = st.selectbox("Select Color:", ["#red", "#blue", "#green", "#yellow", "#pink", "#black", "#white"], key="color")
    type = st.selectbox("Select Type:", ["#tshirt", "#sweatshirt", "#jacket", "#pants", "#skirt", "#dress", "#shorts"], key="type")
    material = st.selectbox("Select Material:", ["#cotton", "#denim", "#leather", "#wool", "#polyester"], key="material")
    pattern = st.selectbox("Select Pattern:", ["#solid", "#striped", "#checked", "#polka-dot", "#floral"], key="pattern")

    # Combine tags
    tags = f"{color}, {type}, {material}, {pattern}"

    if st.button("Save Tags"):
        if save_image_metadata_to_supabase(st.session_state.image_url, tags):
            st.success("Tags saved successfully!")
        else:
            st.error("Failed to save tags.")


