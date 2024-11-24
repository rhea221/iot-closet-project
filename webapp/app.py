import streamlit as st
from PIL import Image
import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

if not supabase_url or not supabase_key:
    st.error("Supabase credentials are missing. Check your .env file.")
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
        response = supabase.table("closet-items").insert({
            "image_url": image_url,
            "tags": tags
        }).execute()
        if response.error:
            raise Exception(response.error)
        st.success("Image metadata saved successfully!")
    except Exception as e:
        st.error(f"Error saving metadata: {e}")

def fetch_closet_items():
    """Fetch all clothes from the Supabase database."""
    try:
        response = supabase.table("closet-items").select("*").execute()
        if response.error:
            raise Exception(response.error)
        return response.data
    except Exception as e:
        st.error(f"Error fetching clothes: {e}")
        return []

# Streamlit App
st.title("IoT Closet Manager")

# Tabs for functionality
tabs = st.tabs(["Upload Image", "View Closet"])

# Tab 1: Upload Image
with tabs[0]:
    st.header("Upload a New Clothing Item")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        file_extension = uploaded_file.name.split('.')[-1]
        unique_filename = generate_unique_filename(file_extension)
        uploaded_image = Image.open(uploaded_file)
        st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)

        # Save Image to Supabase
        if st.button("Upload Image"):
            with open(unique_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())
            image_url = upload_image_to_supabase(unique_filename, unique_filename)
            if image_url:
                st.success(f"Image uploaded: {image_url}")

                # Manually enter tags
                tags = st.text_input("Enter tags (comma-separated):")
                if st.button("Save Metadata"):
                    save_image_metadata_to_supabase(image_url, tags)

# Tab 2: View Closet
with tabs[1]:
    st.header("Closet Items")
    clothes = fetch_closet_items()
    if clothes:
        for item in clothes:
            st.image(item["image_url"], caption=f"Tags: {item['tags']}", use_column_width=True)
            # Add button to update tags
            new_tags = st.text_input(f"Update tags for {item['image_url']}", value=item['tags'])
            if st.button(f"Save Tags for {item['image_url']}"):
                save_image_metadata_to_supabase(item["image_url"], new_tags)
    else:
        st.write("No items found in the closet.")
