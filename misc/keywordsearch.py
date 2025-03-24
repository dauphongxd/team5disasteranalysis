import time
import json
import os
from atproto import Client
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bluesky_disaster_search.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('disasterweb.env')

# Define disaster-related keywords to search for
DISASTER_KEYWORDS = [
    "earthquake", "flood", "hurricane", "tornado", "tsunami", 
    "wildfire", "avalanche", "landslide", "volcano", "eruption",
    "typhoon", "cyclone", "blizzard", "drought", "storm", 
    "fire", "disaster", "emergency", "evacuation", "damage",
    "collapsed", "destroyed", "devastation", "casualties"
]

# Bluesky Client Setup
client = Client()
client.login(os.getenv('BLUESKY_HANDLE'), os.getenv('BLUESKY_PASSWORD'))

# Function to search Bluesky for posts with disaster keywords
def search_bluesky_for_keywords(client, keyword, last_cursor=None):
    try:
        response = client.app.bsky.feed.search_posts(
            params={
                'q': keyword,
                'limit': 100,
                'cursor': last_cursor
            }
        )
        
        logger.info(f"Fetched {len(response.posts)} posts for keyword: {keyword}")
        
        # Filter posts that contain disaster keywords
        disaster_posts = []
        for post in response.posts:
            try:
                if hasattr(post, 'record') and hasattr(post.record, 'text'):
                    text = post.record.text
                    if any(keyword in text.lower() for keyword in DISASTER_KEYWORDS):
                        disaster_posts.append(post)
            except Exception as e:
                logger.error(f"Error processing post in search: {e}")
        
        logger.info(f"Found {len(disaster_posts)} posts with disaster keywords for keyword: {keyword}")
        
        # Return filtered posts and the cursor for pagination
        new_cursor = response.cursor if hasattr(response, 'cursor') else None
        return disaster_posts, new_cursor
    
    except Exception as e:
        logger.error(f"Error searching Bluesky for keyword {keyword}: {e}")
        return [], None

# Function to load existing posts from JSON file
def load_existing_posts(json_file_path):
    if os.path.exists(json_file_path):
        with open(json_file_path, "r", encoding="utf-8") as json_file:
            try:
                return json.load(json_file)
            except json.JSONDecodeError:
                return []
    return []

# Function to process posts and append to JSON
def process_posts_to_json(posts, json_file_path):
    existing_posts = load_existing_posts(json_file_path)
    new_posts = []

    for post in posts:
        try:
            uri = post.uri
            handle = post.author.handle
            display_name = post.author.display_name
            text = post.record.text
            created_at = post.record.created_at
            avatar = post.author.avatar

            # Check for media
            media_urls = []
            if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images'):
                for image in post.record.embed.images:
                    if hasattr(image, 'image') and hasattr(image.image, 'ref') and hasattr(image.image.ref, 'link'):
                        image_url = f"https://cdn.bsky.app/img/feed_fullsize/{image.image.ref.link}"
                        media_urls.append(image_url)

            # Prepare post data for JSON
            json_post_data = {
                "uri": uri,
                "handle": handle,
                "display_name": display_name,
                "text": text,
                "timestamp": created_at,
                "avatar": avatar,
                "media": media_urls
            }

            # Check if the post already exists in the JSON file
            if not any(p["uri"] == uri for p in existing_posts):
                new_posts.append(json_post_data)

        except Exception as e:
            logger.error(f"Error processing post: {e}")
            continue

    # Append new posts to existing posts and save to JSON file
    if new_posts:
        existing_posts.extend(new_posts)
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(existing_posts, json_file, indent=4, ensure_ascii=False)
        logger.info(f"Appended {len(new_posts)} new posts to {json_file_path}")
    else:
        logger.info("No new posts to append.")

# Main function to run the search continuously
def run_search_continuously():
    json_file_path = "disaster_posts_keyword.json"
    last_cursor = None

    while True:
        for keyword in DISASTER_KEYWORDS:
            try:
                disaster_posts, new_cursor = search_bluesky_for_keywords(client, keyword, last_cursor)
                if new_cursor is not None:
                    last_cursor = new_cursor
                
                if disaster_posts:
                    process_posts_to_json(disaster_posts, json_file_path)
                    logger.info(f"Processed {len(disaster_posts)} posts for keyword: {keyword}")
                else:
                    logger.info(f"No more posts to process for keyword: {keyword}")

            except Exception as e:
                logger.error(f"Error processing keyword {keyword}: {e}")
                time.sleep(600)  # Wait 10 minutes before trying again
                continue

        logger.info("Waiting for next batch...")
        time.sleep(600)  # 10 minutes between batches

if __name__ == "__main__":
    run_search_continuously()