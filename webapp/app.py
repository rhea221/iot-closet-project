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

def save_image_data(image_url: str, tags: str):
    """
    Save image data and tags to Supabase.
    :param image_url: URL of the image.
    :param tags: Tags associated with the image.
    """
    try:
        # Prepare data payload
        data = {
            "image_url": image_url,
            "tags": tags,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        # Insert data into Supabase
        logging.info("Sending data to Supabase: %s", data)
        response = supabase.table("closet-items").insert(data).execute()

        # Check the response structure
        if response and hasattr(response, 'data'):
            logging.info("Data saved successfully: %s", response.data)
            return response.data
        elif response and hasattr(response, 'error'):
            logging.error("Error from Supabase: %s", response.error)
            return None
        else:
            logging.warning("Unexpected response structure: %s", response)
            return None

    except Exception as e:
        logging.exception("Unexpected error occurred while saving image data: %s", e)
        return None

if __name__ == "__main__":
    # Example data
    image_url = "https://mbqcfqpgipmtmipuvzlc.supabase.co/storage/v1/object/public/closet-images/5029cd8e-99e9-4f49-81b8-df781387c6ab.jpg"
    tags = "#pink, #sweatshirt, #cotton, #solid"

    # Save image data
    result = save_image_data(image_url, tags)
    if result:
        print("Image data saved successfully:", result)
    else:
        print("Failed to save image data.")
