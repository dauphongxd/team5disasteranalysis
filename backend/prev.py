import time
import datetime
import json
import os
import mysql.connector
from mysql.connector import Error
from atproto import Client, models
from transformers import AutoTokenizer, AutoModelForSequenceClassification, RobertaConfig
import torch.nn.functional as F
from dotenv import load_dotenv
import re
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("disaster_feed.log", encoding='utf-8'),  # Add UTF-8 encoding here
        logging.StreamHandler()  # Console handler will still have issues on Windows
    ]
)
logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
# filter to handle encoding errors
class EncodingFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = record.msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        return True

console_handler.addFilter(EncodingFilter())
logger.addHandler(console_handler)


# text cleaning
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

# 1. Load environment variables
load_dotenv('disasterweb.env')

FEED_URI = 'at://did:plc:qiknc4t5rq7yngvz7g4aezq7/app.bsky.feed.generator/aaaelfwqlfugs'

# 2. Initialize AI Model with the correct configuration
MODEL_PATH = r'F:\AI SCHOOL\checkpoint-1800'

try:
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

    # Define correct label mappings (swapped from your config)
    # The key should be the integer ID and the value should be the label string
    id2label = {
        0: "avalanche",
        1: "blizzard",
        2: "bush_fire",
        3: "cyclone",
        4: "dust_storm",
        5: "earthquake",
        6: "flood",
        7: "forest_fire",
        8: "haze",
        9: "hurricane",
        10: "landslide",
        11: "meteor",
        12: "storm",
        13: "tornado",
        14: "tsunami",
        15: "typhoon",
        16: "unknown",
        17: "volcano",
        18: "wild_fire"
    }

    # Create the reversed mapping for label2id
    label2id = {v: k for k, v in id2label.items()}

    # Create a custom configuration
    config = RobertaConfig.from_pretrained(
        "roberta-base",  # Use base config
        num_labels=19,  # 19 classes based on your config
        id2label=id2label,
        label2id=label2id
    )

    # Load the model with the corrected configuration
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_PATH,
        config=config,
        ignore_mismatched_sizes=True  # Add this to handle potential size mismatches
    )

    logger.info("Model loaded successfully with corrected configuration")

except Exception as e:
    logger.error(f"Error loading model: {e}")
    raise  # Re-raise to stop execution

# 3. Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),  # Just the hostname without port
    'port': int(os.getenv('DB_PORT', '3306')),  # Separate port parameter
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'my_database'),
    'raise_on_warnings': True
}


# 4. Database Connection Function
def get_db_connection():
    try:
        # Add debug info
        logger.info(f"Attempting to connect to MySQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            db_info = connection.get_server_info()
            logger.info(f"Connected to MySQL server version {db_info}")
            logger.info(f"Connected to database: {DB_CONFIG['database']}")
            return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL database: {e}")
        return None


# 5. Function to extract location from text
# def extract_location(text):
#     # Simple regex pattern to find locations
#     location_pattern = r'(?:in|at|near|from) ([A-Z][a-z]+(?: [A-Z][a-z]+)*(?:, [A-Z][a-z]+)?)'
#     match = re.search(location_pattern, text)
#
#     # Default coordinates (0, 0) if no location found
#     lat, lon = 0, 0
#
#     if match:
#         location_name = match.group(1)
#         # In a real application, you would use a geocoding service here
#         lat, lon = 0, 0  # Replace with actual geocoding
#
#     return lat, lon


# 6. Function to insert user into database
def insert_user(connection, user_data):
    cursor = None
    try:
        cursor = connection.cursor()

        # Check if user already exists
        check_query = "SELECT user_id FROM users WHERE user_id = %s"
        cursor.execute(check_query, (user_data['user_id'],))
        result = cursor.fetchone()

        if not result:
            # Generate a fake unique email if needed
            email = user_data.get('email', '')
            if not email:
                email = f"{user_data['username']}@example.com"  # Create a fake unique email

            # Insert user if they don't exist
            insert_query = """
            INSERT INTO users (user_id, username, email, created_at)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                user_data['user_id'],
                user_data['username'],
                email,  # Use the unique email
                datetime.datetime.now()
            ))
            connection.commit()
            logger.info(f"User inserted: {user_data['username']}")
        return user_data['user_id']  # Always return the user_id
    except Error as e:
        logger.error(f"Error inserting user: {e}")
        if connection.is_connected():
            connection.rollback()
    finally:
        if cursor:
            cursor.close()

    return None


# 7. Function to insert post into database
def insert_post(connection, post_data):
    cursor = None
    try:
        cursor = connection.cursor()

        # Check if post already exists
        check_query = "SELECT post_id FROM posts WHERE post_id = %s"
        cursor.execute(check_query, (post_data['post_id'],))
        result = cursor.fetchone()

        if result:
            logger.info(f"Post already exists in database: {post_data['post_id']}")
            return post_data['post_id']  # Return the ID even if it already exists

        # Extract lat/lon for location
        lat, lon = post_data.get('lat', 0), post_data.get('lon', 0)

        try:
            # Insert post
            insert_query = """
            INSERT INTO posts (
                post_id, user_id, original_text, demojized_text, 
                created_at, indexed_at, lang, location, has_media, 
                is_deleted, disaster_type, confidence_score, is_disaster
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, ST_PointFromText(%s, 4326), %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                post_data['post_id'],
                post_data['user_id'],
                post_data['original_text'],
                post_data['demojized_text'],
                post_data['created_at'],
                post_data['indexed_at'],
                post_data.get('lang', 'en'),
                f'POINT({lon} {lat})',  # MySQL expects lon, lat order for POINT
                post_data.get('has_media', False),
                False,  # is_deleted default
                post_data.get('disaster_type', 'unknown'),
                post_data.get('confidence_score', 0.0),
                post_data.get('is_disaster', False)
            ))
            connection.commit()
            logger.info(f"Post inserted: {post_data['post_id']}")

            # Return the post_id for potential media insertion
            return post_data['post_id']
        except Error as e:
            logger.error(f"SQL Error inserting post: {e}")
            logger.error(f"Query parameters: {post_data}")
            if connection.is_connected():
                connection.rollback()
            return None

    except Error as e:
        logger.error(f"Error inserting post: {e}")
        if connection.is_connected():
            connection.rollback()
        return None
    finally:
        if cursor:
            cursor.close()

    return None


# 8. Function to insert media into database
def insert_media(connection, media_data):
    cursor = None
    try:
        cursor = connection.cursor()

        # Insert media
        insert_query = """
        INSERT INTO media (media_id, post_id, media_url, media_type, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """

        # Generate a simple media_id
        media_id = f"{media_data['post_id']}_{int(time.time())}"

        cursor.execute(insert_query, (
            media_id,
            media_data['post_id'],
            media_data['media_url'],
            media_data.get('media_type', 'image'),  # Default to image
            datetime.datetime.now()
        ))
        connection.commit()
        logger.info(f"Media inserted for post: {media_data['post_id']}")

    except Error as e:
        logger.error(f"Error inserting media: {e}")
        if connection.is_connected():
            connection.rollback()
    finally:
        if cursor:
            cursor.close()


# 10. Bluesky Client Setup
client = Client()
client.login(os.getenv('API_HANDLE'), os.getenv('API_PW'))


# 11. Real-time Processing Function
def process_feed():
    last_processed = None
    log_file_path = "disaster_feed_log_base.txt"
    json_file_path = "posts.json"

    # Get database connection
    connection = get_db_connection()
    if not connection:
        logger.error("Failed to establish database connection. Exiting.")
        return

    # Open the log file
    log_file = open(log_file_path, "a", encoding='utf-8')
    posts_data = []  # List to store post data for JSON

    try:
        # Enter the main loop to process new posts in real-time
        while True:
            response = client.app.bsky.feed.get_feed(
                params={
                    'feed': FEED_URI,
                    'limit': 100,
                    'cursor': last_processed
                }
            )
            logger.info(f"Number of posts returned from API: {len(response.feed)}")

            if not response.feed:
                logger.info("No more posts to process.")
                break

            for post in response.feed:
                try:
                    # Extract post details
                    uri = post.post.uri
                    did = post.post.author.did  # Use DID as user_id
                    handle = post.post.author.handle
                    display_name = post.post.author.display_name
                    text = post.post.record.text
                    processed_text = clean_text(text)
                    created_at = post.post.record.created_at
                    indexed_at = post.post.indexed_at
                    avatar = post.post.author.avatar

                    # Extract location from text (simplified approach)
                    lat, lon = extract_location(text)

                    # Check for media
                    has_media = False
                    media_urls = []
                    if hasattr(post.post.record, 'embed') and hasattr(post.post.record.embed, 'images'):
                        has_media = True
                        for image in post.post.record.embed.images:
                            if hasattr(image, 'image') and hasattr(image.image, 'ref') and hasattr(image.image.ref,
                                                                                                   'link'):
                                image_url = f"https://cdn.bsky.app/img/feed_fullsize/{image.image.ref.link}"
                                media_urls.append(image_url)

                    # Predict disaster type
                    inputs = tokenizer(processed_text, return_tensors="pt", truncation=True, padding=True)
                    outputs = model(**inputs)
                    probabilities = F.softmax(outputs.logits, dim=-1)
                    predicted_index = probabilities.argmax().item()
                    predicted_label = id2label[predicted_index]
                    confidence_score = probabilities[0, predicted_index].item()

                    # Two different thresholds
                    threshold = 0.1  # Lower threshold for JSON/logging
                    db_threshold = 0.7  # Higher threshold for database

                    # Determine disaster status for JSON and logging
                    #is_disaster = predicted_label != "unknown" and confidence_score >= threshold
                    is_disaster = confidence_score >= threshold

                    # Determine disaster status for database
                    #is_disaster_db = predicted_label != "unknown" and confidence_score >= db_threshold
                    is_disaster_db = confidence_score >= db_threshold

                    # Prepare user data for database
                    user_data = {
                        'user_id': did,
                        'username': handle,
                        'email': '',  # Not available from feed
                    }

                    # Insert user
                    insert_user(connection, user_data)

                    # Prepare post data for database
                    post_data = {
                        'post_id': uri,
                        'user_id': did,
                        'original_text': text,
                        'demojized_text': processed_text,
                        'created_at': datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00')),
                        'indexed_at': datetime.datetime.fromisoformat(indexed_at.replace('Z', '+00:00')),
                        'lang': 'en',  # Assuming English, you might want to detect language
                        'lat': lat,
                        'lon': lon,
                        'has_media': has_media,
                        'disaster_type': predicted_label,
                        'confidence_score': confidence_score,
                        'is_disaster': is_disaster_db  # Use the higher threshold for database
                    }

                    # Insert post
                    post_id = insert_post(connection, post_data)
                    logger.info(
                        f"Post inserted into database with ID: {post_id}, disaster type: {predicted_label}, is_disaster: {is_disaster_db}")

                    # Insert media if any
                    if post_id and media_urls:
                        for media_url in media_urls:
                            media_data = {
                                'post_id': post_id,
                                'media_url': media_url,
                                'media_type': 'image'  # Assuming image type
                            }
                            insert_media(connection, media_data)

                    # Prepare post data for JSON (for the web interface)
                    json_post_data = {
                        "uri": uri,
                        "handle": handle,
                        "display_name": display_name,
                        "text": text,
                        "demojized_text": processed_text,
                        "timestamp": created_at,
                        "avatar": avatar,
                        "media": media_urls,
                        "predicted_disaster_type": predicted_label,
                        "confidence_score": confidence_score,
                        "is_disaster": is_disaster,  # Use the original (lower) threshold for JSON
                        "location": {"lat": lat, "lon": lon}
                    }

                    # Add to posts data list
                    posts_data.append(json_post_data)

                    # Log the post
                    log_entry = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] New post: {clean_text}\n"
                    if not is_disaster:
                        log_entry += f"Predicted disaster type: Uncertain/Non-Disaster (Confidence: {confidence_score:.4f})\n\n"
                        logger.info(
                            f"New post: {text}\nPredicted: Uncertain/Non-Disaster (Confidence: {confidence_score:.4f})")
                    else:
                        log_entry += f"Predicted disaster type: {predicted_label} (Confidence: {confidence_score:.4f})\n\n"
                        logger.info(
                            f"New post: {text}\nPredicted: {predicted_label} (Confidence: {confidence_score:.4f})")

                    log_file.write(log_entry)

                    # Update last_processed
                    last_processed = post.post.indexed_at

                except Exception as e:
                    logger.error(f"Error processing post: {e}")
                    continue

            # Save the posts data to a JSON file
            with open(json_file_path, "w", encoding="utf-8") as json_file:
                json.dump(posts_data, json_file, indent=4, ensure_ascii=False)

            logger.info(f"Processed batch of posts. Waiting for next batch...")
            time.sleep(600)  # 10 minutes between batches

    except Exception as e:
        logger.error(f"Error in main process: {e}")
    finally:
        log_file.close()
        if connection and connection.is_connected():
            connection.close()
            logger.info("Database connection closed.")


if __name__ == "__main__":
    process_feed()