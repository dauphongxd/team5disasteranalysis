import time
import json
import os
from atproto import Client
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta

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

def search_bluesky_for_keywords(client, keyword):
    try:
        since_time = (datetime.utcnow() - timedelta(hours=1)).isoformat() + 'Z'
        
        response = client.app.bsky.feed.search_posts(
            params={
                'q': keyword,
                'limit': 100,
                'since': since_time
            }
        )
        
        logger.info(f"Fetched {len(response.posts)} posts for keyword: {keyword} since {since_time}")
        
        disaster_posts = []
        for post in response.posts:
            try:
                if hasattr(post, 'record') and hasattr(post.record, 'text'):
                    text = post.record.text
                    if any(kw in text.lower() for kw in DISASTER_KEYWORDS):
                        disaster_posts.append(post)
            except Exception as e:
                logger.error(f"Error processing post in search: {e}")
        
        logger.info(f"Found {len(disaster_posts)} posts with disaster keywords for keyword: {keyword}")
        
        return disaster_posts
    
    except Exception as e:
        logger.error(f"Error searching Bluesky for keyword {keyword}: {e}")
        return []

def load_existing_posts(json_file_path):
    if os.path.exists(json_file_path):
        with open(json_file_path, "r", encoding="utf-8") as json_file:
            try:
                return json.load(json_file)
            except json.JSONDecodeError:
                return []
    return []

def process_posts_to_json(posts, json_file_path):
    existing_posts = load_existing_posts(json_file_path)
    total_posts = len(existing_posts)  # Get current total before adding new posts
    new_posts = []

    for post in posts:
        try:
            uri = post.uri
            handle = post.author.handle
            display_name = post.author.display_name
            text = post.record.text
            created_at = post.record.created_at
            avatar = post.author.avatar

            media_urls = []
            if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images'):
                for image in post.record.embed.images:
                    if hasattr(image, 'image') and hasattr(image.image, 'ref') and hasattr(image.image.ref, 'link'):
                        image_url = f"https://cdn.bsky.app/img/feed_fullsize/{image.image.ref.link}"
                        media_urls.append(image_url)

            json_post_data = {
                "uri": uri,
                "handle": handle,
                "display_name": display_name,
                "text": text,
                "timestamp": created_at,
                "avatar": avatar,
                "media": media_urls
            }

            if not any(p["uri"] == uri for p in existing_posts):
                new_posts.append(json_post_data)

        except Exception as e:
            logger.error(f"Error processing post: {e}")
            continue

    if new_posts:
        existing_posts.extend(new_posts)
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(existing_posts, json_file, indent=4, ensure_ascii=False)
        logger.info(f"Appended {len(new_posts)} new posts to {json_file_path}")
        logger.info(f"TOTAL POSTS STORED: {len(existing_posts)}")  # Display total count
    else:
        logger.info("No new posts to append.")
        logger.info(f"TOTAL POSTS STORED: {total_posts}")  # Display unchanged total

def run_search_for_recent_posts():
    json_file_path = "disaster_posts_keyword.json"
    hours_to_search = 1

    # Display initial total count
    initial_posts = load_existing_posts(json_file_path)
    logger.info(f"Initial total posts in storage: {len(initial_posts)}")

    while True:
        for keyword in DISASTER_KEYWORDS:
            try:
                disaster_posts = search_bluesky_for_keywords(client, keyword)
                
                if disaster_posts:
                    process_posts_to_json(disaster_posts, json_file_path)
                    logger.info(f"Processed {len(disaster_posts)} posts for keyword: {keyword}")
                else:
                    logger.info(f"No new posts found for keyword: {keyword}")

            except Exception as e:
                logger.error(f"Error processing keyword {keyword}: {e}")
                time.sleep(600)
                continue

        # Display total count at the end of each full keyword cycle
        current_posts = load_existing_posts(json_file_path)
        logger.info(f"Current total posts in storage: {len(current_posts)}")
        logger.info(f"Waiting for next batch (checking for new posts in last {hours_to_search} hour(s))...")
        time.sleep(600)

if __name__ == "__main__":
    run_search_for_recent_posts()