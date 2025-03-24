import time
import json
import os
from atproto import Client
from dotenv import load_dotenv
import logging
from datetime import datetime

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
load_dotenv('disasterwebf.env')

# Bluesky Client Setup
client = Client()
client.login(os.getenv('BLUESKY_H'), os.getenv('BLUESKY_PW'))

# Define the feed URI
FEED_URI = 'at://did:plc:qiknc4t5rq7yngvz7g4aezq7/app.bsky.feed.generator/aaaelfwqlfugs'

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
            uri = post.post.uri
            handle = post.post.author.handle
            display_name = post.post.author.display_name
            text = post.post.record.text
            created_at = post.post.record.created_at
            avatar = post.post.author.avatar

            # Check for media
            media_urls = []
            if hasattr(post.post.record, 'embed') and hasattr(post.post.record.embed, 'images'):
                for image in post.post.record.embed.images:
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
    json_file_path = "disaster_posts_feed.json"
    last_cursor = None

    while True:
        try:
            response = client.app.bsky.feed.get_feed(
                params={
                    'feed': FEED_URI,
                    'limit': 100,
                    'cursor': last_cursor
                }
            )

            if not response.feed:
                logger.info("No more posts to process.")
                break

            posts_to_process = []
            for post in response.feed:
                posts_to_process.append(post)

            if posts_to_process:
                process_posts_to_json(posts_to_process, json_file_path)
                logger.info(f"Processed {len(posts_to_process)} posts.")
            else:
                logger.info("No new posts found in this batch.")

            # Update the cursor for the next batch of posts
            last_cursor = response.cursor if hasattr(response, 'cursor') else None

            if not last_cursor:
                logger.info("No more posts to fetch.")
                break

        except Exception as e:
            logger.error(f"Error fetching or processing feed: {e}")
            time.sleep(600)  # Wait 10 minutes before trying again
            continue

        logger.info("Waiting for next batch...")
        time.sleep(60)  # 10 minutes between batches

if __name__ == "__main__":
    run_search_continuously()