import time
import datetime
import json
import os
import threading
from atproto import Client
from transformers import AutoTokenizer, AutoModelForSequenceClassification, RobertaConfig
import torch.nn.functional as F
from dotenv import load_dotenv
import re
import logging
import uuid
from decimal import Decimal

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("disaster_keyword_search.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define disaster keywords - we'll search for each of these
DISASTER_KEYWORDS = [
    "earthquake", "flood", "hurricane", "tornado", "tsunami",
    "wildfire", "avalanche", "landslide", "volcano", "eruption",
    "typhoon", "cyclone", "blizzard", "drought", "storm",
    "fire", "disaster", "emergency", "evacuation", "damage",
    "collapsed", "destroyed", "devastation", "casualties"
]


# Text cleaning
def clean_text(text):
    """Clean text by removing URLs, mentions, special chars, etc."""
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove mentions
    text = re.sub(r'@\w+', '', text)
    # Remove hashtags (keep the text after #)
    text = re.sub(r'#(\w+)', r'\1', text)
    # Remove special characters and numbers
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\d+', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Convert to lowercase
    text = text.lower()
    return text


# Safe date parsing function to handle problematic ISO formats
def safe_parse_date(date_string):
    """
    Safely parse date strings into datetime objects, handling various formats.
    """
    try:
        # For standard ISO format
        return datetime.datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except ValueError:
        try:
            # For ISO format with too many decimal places
            # First, simplify the format by taking only up to 6 decimal places for microseconds
            match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d{1,6})(\d*)([+-].+|Z)?', date_string)
            if match:
                base, micros, _, timezone = match.groups()
                # Pad micros to 6 digits if necessary
                micros = micros.ljust(6, '0')[:6]
                # Reconstruct the date string
                clean_date = f"{base}.{micros}" + (timezone or '+00:00').replace('Z', '+00:00')
                return datetime.datetime.fromisoformat(clean_date)
        except (ValueError, AttributeError):
            pass

        # If all else fails, use current time and log warning
        logger.warning(f"Could not parse date string: {date_string}, using current time instead.")
        return datetime.datetime.now()


# Load environment variables
load_dotenv('.env')


# Initialize AI Model
def init_model(model_path):
    """Initialize AI model with proper error handling"""
    try:
        logger.info(f"Loading model from {model_path}")

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        # Define label mappings
        id2label = {
            0: "avalanche", 1: "blizzard", 2: "bush_fire", 3: "cyclone",
            4: "dust_storm", 5: "earthquake", 6: "flood", 7: "forest_fire",
            8: "haze", 9: "hurricane", 10: "landslide", 11: "meteor",
            12: "storm", 13: "tornado", 14: "tsunami", 15: "typhoon",
            16: "unknown", 17: "volcano", 18: "wild_fire"
        }

        # Create the reversed mapping
        label2id = {v: k for k, v in id2label.items()}

        # Create configuration
        config = RobertaConfig.from_pretrained(
            "roberta-base",
            num_labels=19,
            id2label=id2label,
            label2id=label2id
        )

        # Load model
        model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            config=config,
            ignore_mismatched_sizes=True
        )

        logger.info("Model loaded successfully")
        return tokenizer, model, id2label
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise


# Predict disaster type from text
def predict_disaster(tokenizer, model, id2label, text):
    """Predict disaster type from text"""
    try:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        outputs = model(**inputs)
        probabilities = F.softmax(outputs.logits, dim=-1)
        predicted_index = probabilities.argmax().item()
        predicted_label = id2label[predicted_index]
        confidence_score = probabilities[0, predicted_index].item()

        return predicted_label, confidence_score
    except Exception as e:
        logger.error(f"Error predicting disaster: {e}")
        return "unknown", 0.0


# Ensure Bluesky session is valid
def ensure_bluesky_session(client, max_retries=3):
    """
    Ensure the Bluesky client session is valid by refreshing it if needed.
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Try a simple profile request to test if session is valid
            handle = os.getenv('API_HANDLE')
            client.app.bsky.actor.get_profile({'actor': handle})
            logger.info("Bluesky session is valid")
            return True
        except Exception as e:
            logger.warning(f"Session validation failed (attempt {attempt}/{max_retries}): {e}")

            # Try to create a new session
            try:
                logger.info("Attempting to refresh Bluesky session...")
                client.login(os.getenv('API_HANDLE'), os.getenv('API_PW'))
                logger.info("Successfully refreshed Bluesky session")
                return True
            except Exception as login_error:
                logger.error(f"Failed to refresh session (attempt {attempt}/{max_retries}): {login_error}")
                if attempt < max_retries:
                    # Exponential backoff between retries
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)

    logger.error("All session refresh attempts failed")
    return False


# Search Bluesky for keywords with a specified date range
def search_bluesky_for_keywords(client, keyword, months=12, max_retries=3):
    """Search Bluesky for posts with retry logic"""
    for attempt in range(1, max_retries + 1):
        try:
            # Calculate the time window - starting from April 2024
            current_date = datetime.datetime.now(datetime.timezone.utc)

            # Set the since date to April 1, 2024 (or 12 months ago, whichever is more recent)
            april_2024 = datetime.datetime(2024, 4, 1, tzinfo=datetime.timezone.utc)
            months_ago = current_date - datetime.timedelta(days=30 * months)
            since_time = max(april_2024, months_ago)

            # Format as ISO 8601 string without microseconds and with 'Z' suffix
            since_str = since_time.replace(microsecond=0).isoformat()
            if since_str.endswith('+00:00'):
                since_str = since_str.replace('+00:00', 'Z')

            logger.info(f"Searching for '{keyword}' since {since_str}")

            # Make the API request - use limit=100 to get more posts, adjust as needed
            response = client.app.bsky.feed.search_posts(
                params={'q': keyword, 'limit': 50, 'since': since_str}
            )

            if response and hasattr(response, 'posts'):
                logger.info(f"Found {len(response.posts)} posts for '{keyword}'")
                return response

            return None

        except Exception as e:
            logger.error(f"Error searching Bluesky for keyword {keyword} (attempt {attempt}/{max_retries}): {str(e)}")
            if attempt < max_retries:
                wait_time = min(30, 2 ** attempt)  # Cap at 30 seconds
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

    logger.error(f"All {max_retries} attempts failed for keyword '{keyword}'")
    return None


# Process keywords and extract posts to JSON
def process_keywords_to_json(tokenizer, model, id2label, client, output_file="disaster_posts.json"):
    """Process keywords and save results to JSON file"""
    # Load existing posts if the file exists
    try:
        with open(output_file, "r", encoding="utf-8") as json_file:
            all_posts = json.load(json_file)
            logger.info(f"Loaded {len(all_posts)} existing posts from JSON file")
    except (FileNotFoundError, json.JSONDecodeError):
        all_posts = []
        logger.info("Started new JSON posts collection")

    # Track post IDs we've already seen
    seen_post_ids = {post["uri"] for post in all_posts}
    initial_post_count = len(all_posts)

    # Set confidence thresholds
    threshold = 0.1  # Minimum threshold to consider for JSON storage

    # Process each keyword
    total_new_posts = 0
    total_searches = 0

    try:
        for keyword in DISASTER_KEYWORDS:
            total_searches += 1
            logger.info(f"Searching for keyword: {keyword} ({total_searches}/{len(DISASTER_KEYWORDS)})")

            # Make sure session is valid before each search
            if total_searches % 5 == 0:  # Check every 5 searches
                if not ensure_bluesky_session(client):
                    logger.error("Could not maintain valid session, stopping searches")
                    break

            # Search for posts with this keyword
            response = search_bluesky_for_keywords(client, keyword)
            if not response or not hasattr(response, 'posts') or not response.posts:
                logger.info(f"No posts found for keyword: {keyword}")
                continue

            # Process each post
            keyword_new_posts = 0
            for post in response.posts:
                try:
                    # Extract the post ID
                    uri = post.uri

                    # Skip if we've already processed this post
                    if uri in seen_post_ids:
                        continue

                    # Add to seen posts
                    seen_post_ids.add(uri)

                    # Extract all needed data
                    did = post.author.did
                    handle = post.author.handle
                    display_name = post.author.display_name or ''
                    avatar_url = post.author.avatar or ''
                    text = post.record.text
                    cleaned_text = clean_text(text)
                    created_at = safe_parse_date(post.record.created_at)
                    indexed_at = safe_parse_date(post.indexed_at)

                    # Check the date is within our range
                    # Skip posts before April 2024
                    apr_2024 = datetime.datetime(2024, 4, 1, tzinfo=datetime.timezone.utc)
                    if created_at.replace(tzinfo=datetime.timezone.utc) < apr_2024:
                        logger.debug(f"Skipping post from before April 2024: {created_at}")
                        continue

                    # Extract location (currently returns empty string)
                    location_name = ""

                    # Check for media
                    media_urls = []
                    if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images'):
                        for image in post.record.embed.images:
                            if hasattr(image, 'image') and hasattr(image.image, 'ref') and hasattr(image.image.ref,
                                                                                                   'link'):
                                image_url = f"https://cdn.bsky.app/img/feed_fullsize/{image.image.ref.link}"
                                media_urls.append(image_url)

                    # Predict disaster type
                    predicted_label, confidence_score = predict_disaster(tokenizer, model, id2label, cleaned_text)

                    # Skip posts with low confidence
                    if confidence_score < threshold:
                        continue

                    # Prepare post data for JSON
                    post_data = {
                        "uri": uri,
                        "user_id": did,
                        "handle": handle,
                        "display_name": display_name,
                        "text": text,
                        "clean_text": cleaned_text,
                        "timestamp": created_at.isoformat(),
                        "indexed_at": indexed_at.isoformat(),
                        "avatar": avatar_url,
                        "media": media_urls,
                        "predicted_disaster_type": predicted_label,
                        "confidence_score": confidence_score,
                        "is_disaster": confidence_score >= threshold,
                        "location": location_name,
                        "keyword_match": keyword
                    }

                    # Add to posts collection (at the beginning for newest first)
                    all_posts.insert(0, post_data)

                    keyword_new_posts += 1
                    total_new_posts += 1

                    # Log progress periodically
                    if total_new_posts % 10 == 0:
                        logger.info(f"Processed {total_new_posts} new posts so far")

                        # Save progress periodically
                        with open(output_file, "w", encoding="utf-8") as json_file:
                            json.dump(all_posts, json_file, indent=2, ensure_ascii=False)

                except Exception as e:
                    logger.error(f"Error processing post: {e}")
                    continue

            logger.info(f"Found {keyword_new_posts} new posts for keyword: {keyword}")

            # Add a short delay between keywords to avoid rate limiting
            if keyword != DISASTER_KEYWORDS[-1]:  # Don't sleep after the last keyword
                time.sleep(2)

        # Final save of all posts
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(all_posts, json_file, indent=2, ensure_ascii=False)

        logger.info(f"Completed keyword search. Added {total_new_posts} new posts (total: {len(all_posts)})")
        return total_new_posts

    except KeyboardInterrupt:
        logger.info("Keyword search interrupted by user")
        # Save current progress before exiting
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(all_posts, json_file, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(all_posts)} posts before exit")
        return total_new_posts

    except Exception as e:
        logger.error(f"Fatal error in keyword processing: {e}")
        # Try to save current progress
        try:
            with open(output_file, "w", encoding="utf-8") as json_file:
                json.dump(all_posts, json_file, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(all_posts)} posts after error")
        except Exception as save_error:
            logger.error(f"Error saving posts after fatal error: {save_error}")
        return total_new_posts


# Main function
def main():
    """Main entry point for the application"""
    try:
        # Initialize AI model
        MODEL_PATH = os.getenv('MODEL_PATH', './model/checkpoint-1800')
        tokenizer, model, id2label = init_model(MODEL_PATH)

        # Set up Bluesky client
        logger.info("Setting up Bluesky client...")
        client = Client()
        api_handle = os.getenv('API_HANDLE')
        api_pw = os.getenv('API_PW')

        if not api_handle or not api_pw:
            logger.error("Bluesky API credentials not found in environment variables")
            raise ValueError("Bluesky credentials missing. Check your .env file.")

        client.login(api_handle, api_pw)

        # Start a session monitoring thread to keep the session alive
        def keep_session_alive():
            """Background thread to keep the Bluesky session alive"""
            while True:
                try:
                    time.sleep(600)  # Check every 10 minutes
                    logger.info("Performing session health check")
                    client.app.bsky.actor.get_profile({'actor': api_handle})
                    logger.info("Session is still valid")
                except Exception as e:
                    logger.warning(f"Session error in monitor thread: {e}")
                    try:
                        logger.info("Refreshing session from background thread")
                        client.login(api_handle, api_pw)
                        logger.info("Session refreshed successfully")
                    except Exception as login_error:
                        logger.error(f"Failed to refresh session: {login_error}")

        # Start the thread as daemon so it exits when main thread exits
        session_thread = threading.Thread(target=keep_session_alive, daemon=True)
        session_thread.daemon = True
        session_thread.start()
        logger.info("Started session monitoring thread")

        # Process keywords and save to JSON
        output_file = os.getenv('OUTPUT_FILE', 'disaster_posts.json')
        logger.info(f"Starting keyword search, saving results to {output_file}")

        # Initial processing
        new_posts = process_keywords_to_json(tokenizer, model, id2label, client, output_file)
        logger.info(f"Initial processing complete, found {new_posts} new posts")

        # Optional: Set up a loop to periodically search for new posts
        run_continuous = os.getenv('RUN_CONTINUOUS', 'false').lower() == 'true'

        if run_continuous:
            logger.info("Running in continuous mode, will search periodically")
            interval_hours = int(os.getenv('SEARCH_INTERVAL_HOURS', '12'))

            try:
                while True:
                    # Wait for the specified interval
                    interval_seconds = interval_hours * 3600
                    logger.info(f"Waiting {interval_hours} hours until next search...")
                    time.sleep(interval_seconds)

                    # Make sure session is valid before continuing
                    if not ensure_bluesky_session(client):
                        logger.error("Could not maintain valid session, will try again next cycle")
                        continue

                    # Run the search again
                    logger.info("Starting periodic keyword search...")
                    new_posts = process_keywords_to_json(tokenizer, model, id2label, client, output_file)
                    logger.info(f"Periodic search complete, found {new_posts} new posts")

            except KeyboardInterrupt:
                logger.info("Continuous mode interrupted by user")
            except Exception as e:
                logger.error(f"Error in continuous mode: {e}")
        else:
            logger.info("Completed one-time keyword search")

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")


if __name__ == "__main__":
    main()