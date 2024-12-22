from supabase import create_client, Client
from dotenv import load_dotenv
import os
import uuid
import openai

# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

if not supabase_url or not supabase_key:
    raise ValueError("Supabase credentials are missing. Check your .env file.")

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OpenAI API key is missing. Check your .env file.")

def generate_unique_filename(extension: str) -> str:
    """Generate a unique filename using a UUID."""
    return f"{uuid.uuid4()}.{extension}"

def upload_image_to_supabase(file, extension: str) -> str:
    """
    Upload an image directly from a file-like object (Streamlit) to Supabase Storage
    and return the public URL.
    """
    try:
        filename = generate_unique_filename(extension)
        response = supabase.storage.from_("closet-images").upload(filename, file)
        if not response.get("path"):
            raise Exception("Failed to upload file.")
        public_url = supabase.storage.from_("closet-images").get_public_url(filename)
        return public_url
    except Exception as e:
        raise Exception(f"Error uploading image to Supabase: {e}")

def get_image_tags(image_url: str) -> list:
    """Generate detailed tags for an image using OpenAI."""
    try:
        # Prompt for GPT-based tagging
        prompt = (
            f"Analyze this clothing item image available at {image_url}. "
            "Describe it in terms of the following attributes:\n"
            "1. Material (e.g., cotton, polyester).\n"
            "2. Clothing category (e.g., shirt, pants, jacket).\n"
            "3. Style (e.g., casual, formal, sporty).\n"
            "4. Weather suitability (e.g., suitable for hot, cold, rainy).\n"
            "5. Event suitability (e.g., office, party, workout).\n"
            "Return a list of tags representing these attributes."
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert fashion stylist and clothing analyst."},
                {"role": "user", "content": prompt},
            ]
        )
        tags = response['choices'][0]['message']['content']
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

if __name__ == "__main__":
    import streamlit as st

    st.title("Test Closet System")

    uploaded_file = st.file_uploader("Upload an image of your clothing item", type=["jpg", "png", "jpeg"])
    if uploaded_file is not None:
        try:
            # Upload the file and get the public URL
            st.write("Uploading image to Supabase...")
            public_url = upload_image_to_supabase(uploaded_file, "jpg")
            st.success(f"Image uploaded: {public_url}")
            st.image(public_url, caption="Uploaded Image", use_column_width=True)

            # Generate tags using the public URL
            st.write("Generating tags using OpenAI...")
            tags = get_image_tags(public_url)
            st.success(f"Generated Tags: {', '.join(tags)}")

            # Save the clothing item
            st.write("Saving clothing item to Supabase...")
            save_clothing_item(public_url, tags)
            st.success("Clothing item saved successfully!")

        except Exception as e:
            st.error(f"Error: {e}")
