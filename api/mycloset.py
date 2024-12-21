from supabase import create_client, Client
from dotenv import load_dotenv
import os
import uuid
import json
from datetime import datetime
import openai

# Load environment variables
load_dotenv(dotenv_path="config/.env")

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)
openai.api_key = os.getenv("OPENAI_API_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("Supabase credentials are missing. Check your .env file.")

# Helper Functions
def generate_unique_filename(extension):
    """Generate a unique filename using a UUID."""
    return f"{uuid.uuid4()}.{extension}"

def upload_image_to_supabase(file_path, file_name):
    """Upload an image to Supabase Storage and return the public URL."""
    try:
        with open(file_path, "rb") as file:
            response = supabase.storage.from_("closet-images").upload(file_name, file)
            if not response.path:
                raise Exception("Upload failed. No path returned.")
            public_url = f"{supabase_url}/storage/v1/object/public/closet-images/{file_name}"
            return public_url
    except Exception as e:
        raise Exception(f"Error uploading image to Supabase: {e}")

def save_image_metadata_to_supabase(image_url, tags):
    """Save image metadata (URL and tags) to Supabase Database."""
    try:
        data = {
            "image_url": image_url,
            "tags": tags,
            "created_at": datetime.utcnow().isoformat()
        }
        response = supabase.table("closet-items").insert(data).execute()
        if response.error:
            raise Exception(response.error)
        return True
    except Exception as e:
        raise Exception(f"Error saving metadata to Supabase: {e}")

def fetch_closet_items():
    """Fetch all closet items from Supabase Database."""
    try:
        response = supabase.table("closet-items").select("*").execute()
        if response.error:
            raise Exception(response.error)
        return response.data
    except Exception as e:
        raise Exception(f"Error fetching closet items: {e}")

def update_item_tags(image_url, new_tags):
    """Update tags for a specific item in Supabase."""
    try:
        response = supabase.table("closet-items").update({"tags": new_tags}).eq("image_url", image_url).execute()
        if response.error:
            raise Exception(response.error)
        return True
    except Exception as e:
        raise Exception(f"Error updating tags: {e}")

def generate_tags_with_openai(image_url):
    """Generate tags for an image using OpenAI GPT."""
    prompt = f"""
    Analyze the following clothing item image and provide a list of tags based on the color, type, material, and pattern:
    Image URL: {image_url}

    Example tags: ["red", "tshirt", "cotton", "solid"]
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Use gpt-4 or gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "You are a helpful assistant for analyzing clothing items."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        tags = response['choices'][0]['message']['content'].strip()
        return eval(tags)  # Convert string to list
    except Exception as e:
        raise Exception(f"Error generating tags with OpenAI: {e}")

# Command-Line Interface (Optional)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Closet Management Script")
    parser.add_argument("--upload", help="Upload an image to Supabase", action="store_true")
    parser.add_argument("--view", help="View all closet items", action="store_true")
    parser.add_argument("--update", help="Update tags for an image", nargs=2, metavar=("URL", "TAGS"))
    parser.add_argument("--generate-tags", help="Generate tags using OpenAI for an image", nargs=1, metavar="URL")

    args = parser.parse_args()

    if args.upload:
        file_path = input("Enter the path to the image file: ").strip()
        file_extension = file_path.split(".")[-1]
        unique_filename = generate_unique_filename(file_extension)
        try:
            image_url = upload_image_to_supabase(file_path, unique_filename)
            print(f"Image uploaded successfully: {image_url}")
            tags = input("Enter tags for the image (comma-separated): ").strip()
            save_image_metadata_to_supabase(image_url, tags)
            print("Metadata saved successfully.")
        except Exception as e:
            print(f"Error: {e}")

    elif args.view:
        try:
            items = fetch_closet_items()
            if items:
                for item in items:
                    print(f"Image URL: {item['image_url']}")
                    print(f"Tags: {item['tags']}")
                    print(f"Created At: {item['created_at']}")
                    print("-" * 40)
            else:
                print("No items found in the closet.")
        except Exception as e:
            print(f"Error: {e}")

    elif args.update:
        image_url, new_tags = args.update
        try:
            if update_item_tags(image_url, new_tags):
                print("Tags updated successfully.")
        except Exception as e:
            print(f"Error: {e}")

    elif args.generate_tags:
        image_url = args.generate_tags[0]
        try:
            tags = generate_tags_with_openai(image_url)
            print(f"Generated Tags: {tags}")
            save_image_metadata_to_supabase(image_url, ", ".join(tags))
            print("Tags saved successfully.")
        except Exception as e:
            print(f"Error: {e}")

    else:
        parser.print_help()
