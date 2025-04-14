import boto3
import time
from datetime import datetime, timedelta, timezone
import json
import os
import requests
from atproto import Client
from transformers import AutoTokenizer, AutoModelForSequenceClassification, RobertaConfig
import torch.nn.functional as F
from dotenv import load_dotenv
import re
import logging
import uuid
from decimal import Decimal
from botocore.exceptions import ClientError
from langdetect import detect, DetectorFactory
import threading

# Set seed for langdetect to ensure consistent results
DetectorFactory.seed = 0

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # logging.FileHandler("disaster_feed.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask API endpoint for WebSocket notifications
# This should match your Flask API's host and port
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
NOTIFICATION_ENDPOINT = f"{API_BASE_URL}/api/notify-new-post"

# Notification buffer and timer
NOTIFICATION_BUFFER = []
NOTIFICATION_MUTEX = threading.Lock()
LAST_NOTIFICATION_TIME = time.time()
NOTIFICATION_INTERVAL = 15 * 60  # 15 minutes in seconds

# API Rate Limit Parameters
MAX_REQUESTS_PER_WINDOW = 3000  # Maximum requests in a 5-minute window
RATE_LIMIT_WINDOW = 300  # 5 minutes in seconds
REQUEST_TOKENS = MAX_REQUESTS_PER_WINDOW  # Start with full tokens
LAST_TOKEN_REFILL = time.time()  # Last time tokens were refilled
TOKEN_MUTEX = threading.Lock()  # Mutex for thread-safe token updates

# Define disaster-related keywords for search
DISASTER_KEYWORDS = [
    "earthquake", "flood", "hurricane", "tornado", "tsunami",
    "wildfire", "avalanche", "landslide", "volcano", "eruption",
    "typhoon", "cyclone", "blizzard", "drought", "storm",
    "fire", "disaster", "emergency", "evacuation", "damage",
    "collapsed", "destroyed", "devastation", "casualties"
]

# File to store last processed timestamp
LAST_PROCESSED_FILE = "last_processed.json"


# Initialize last processed timestamps for each keyword
def init_last_processed_times():
    """Initialize or load last processed timestamps"""
    try:
        with open(LAST_PROCESSED_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Create default with all keywords set to current time
        now = datetime.now(timezone.utc).isoformat()
        return {keyword: now for keyword in DISASTER_KEYWORDS}


# Save last processed timestamps
def save_last_processed_times(timestamp_dict):
    """Save the last processed timestamps to file"""
    with open(LAST_PROCESSED_FILE, 'w') as f:
        json.dump(timestamp_dict, f)


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


# Check if text is in English
def is_english(text):
    """Detect if text is in English"""
    try:
        return detect(text) == 'en'
    except:
        # If detection fails, assume it's not English
        return False


# Safe date parsing function to handle problematic ISO formats
def safe_parse_date(date_string):
    """Safely parse date strings into datetime objects, handling various formats."""
    try:
        # For standard ISO format
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
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
                return datetime.fromisoformat(clean_date)
        except (ValueError, AttributeError):
            pass

        # If all else fails, use current time and log warning
        logger.warning(f"Could not parse date string: {date_string}, using current time instead.")
        return datetime.now()


# Token bucket rate limiter function
def consume_token():
    """
    Consume a token from the rate limiter.
    Returns True if a token was consumed, False if we need to wait.
    """
    global REQUEST_TOKENS, LAST_TOKEN_REFILL

    with TOKEN_MUTEX:
        # Refill tokens based on elapsed time
        now = time.time()
        elapsed = now - LAST_TOKEN_REFILL

        if elapsed > 0:
            # Calculate tokens to add: (elapsed seconds / window) * max tokens
            new_tokens = int((elapsed / RATE_LIMIT_WINDOW) * MAX_REQUESTS_PER_WINDOW)

            if new_tokens > 0:
                REQUEST_TOKENS = min(REQUEST_TOKENS + new_tokens, MAX_REQUESTS_PER_WINDOW)
                LAST_TOKEN_REFILL = now

        # Try to consume a token
        if REQUEST_TOKENS > 0:
            REQUEST_TOKENS -= 1
            remaining_percentage = (REQUEST_TOKENS / MAX_REQUESTS_PER_WINDOW) * 100
            if remaining_percentage < 20:  # Log warning when tokens are running low
                logger.warning(
                    f"API rate limit tokens running low: {REQUEST_TOKENS}/{MAX_REQUESTS_PER_WINDOW} ({remaining_percentage:.1f}%)")
            return True
        else:
            # Calculate time until next token will be available
            time_to_next_token = RATE_LIMIT_WINDOW / MAX_REQUESTS_PER_WINDOW
            logger.warning(f"Rate limit reached, need to wait {time_to_next_token:.2f} seconds")
            return False


# Load environment variables
load_dotenv('.env')

# Define table names
USERS_TABLE = 'DisasterFeed_Users'
POSTS_TABLE = 'DisasterFeed_Posts'
WEATHER_TABLE = 'DisasterFeed_WeatherData'


# Initialize DynamoDB client
def init_dynamodb():
    """Initialize DynamoDB client with appropriate error handling"""
    try:
        region = os.getenv('AWS_REGION', 'us-east-1')
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

        if not aws_access_key_id or not aws_secret_access_key:
            logger.error("AWS credentials not found in environment variables")
            raise ValueError("AWS credentials missing. Check your environment variables.")

        logger.info(f"Initializing DynamoDB in region {region}")
        return boto3.resource('dynamodb',
                              region_name=region,
                              aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key)
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB: {e}")
        raise


# Initialize AI Model with error handling
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


# Function to check if a table exists
def table_exists(dynamodb, table_name):
    """Check if a table exists"""
    try:
        dynamodb.meta.client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise


# Function to wait until table is active
def wait_for_table_active(dynamodb, table_name):
    """Wait until the table exists and is active"""
    try:
        table = dynamodb.Table(table_name)
        table.wait_until_exists()

        # Now wait until the table is active
        for attempt in range(1, 13):  # Try for up to 1 minute (12 * 5 seconds)
            response = dynamodb.meta.client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            if status == 'ACTIVE':
                logger.info(f"Table {table_name} is ACTIVE and ready to use")
                return True
            logger.info(
                f"Waiting for table {table_name} to be ACTIVE (current status: {status})... Attempt {attempt}/12")
            time.sleep(5)  # Wait 5 seconds before checking again

        logger.error(f"Table {table_name} did not become active within the timeout period")
        return False
    except Exception as e:
        logger.error(f"Error waiting for table {table_name}: {e}")
        return False


# Function to create all required tables
def create_tables(dynamodb, force_recreate=False):
    """Create all required tables"""
    created_tables = []

    # Create Users table if it doesn't exist
    if not table_exists(dynamodb, USERS_TABLE):
        try:
            dynamodb.create_table(
                TableName=USERS_TABLE,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'}  # Partition key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            logger.info(f"Created {USERS_TABLE} table")
            created_tables.append(USERS_TABLE)
        except Exception as e:
            logger.error(f"Error creating {USERS_TABLE} table: {e}")
    else:
        logger.info(f"Table {USERS_TABLE} already exists")

    # Create Posts table if it doesn't exist
    if not table_exists(dynamodb, POSTS_TABLE):
        try:
            dynamodb.create_table(
                TableName=POSTS_TABLE,
                KeySchema=[
                    {'AttributeName': 'post_id', 'KeyType': 'HASH'},  # Partition key
                    {'AttributeName': 'indexed_at', 'KeyType': 'RANGE'}  # Sort key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'post_id', 'AttributeType': 'S'},
                    {'AttributeName': 'indexed_at', 'AttributeType': 'S'},
                    {'AttributeName': 'disaster_type', 'AttributeType': 'S'},
                    {'AttributeName': 'is_disaster_str', 'AttributeType': 'S'}  # String representation of boolean
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'DisasterTypeIndex',
                        'KeySchema': [
                            {'AttributeName': 'disaster_type', 'KeyType': 'HASH'},
                            {'AttributeName': 'indexed_at', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'}
                    },
                    {
                        'IndexName': 'IsDisasterIndex',
                        'KeySchema': [
                            {'AttributeName': 'is_disaster_str', 'KeyType': 'HASH'},  # String field
                            {'AttributeName': 'indexed_at', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'}
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            logger.info(f"Created {POSTS_TABLE} table")
            created_tables.append(POSTS_TABLE)
        except Exception as e:
            logger.error(f"Error creating {POSTS_TABLE} table: {e}")
    else:
        logger.info(f"Table {POSTS_TABLE} already exists")

    # Create Weather Data table if it doesn't exist
    if not table_exists(dynamodb, WEATHER_TABLE):
        try:
            dynamodb.create_table(
                TableName=WEATHER_TABLE,
                KeySchema=[
                    {'AttributeName': 'weather_id', 'KeyType': 'HASH'}  # Partition key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'weather_id', 'AttributeType': 'S'},
                    {'AttributeName': 'post_id', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'PostWeatherIndex',
                        'KeySchema': [
                            {'AttributeName': 'post_id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'}
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            logger.info(f"Created {WEATHER_TABLE} table")
            created_tables.append(WEATHER_TABLE)
        except Exception as e:
            logger.error(f"Error creating {WEATHER_TABLE} table: {e}")
    else:
        logger.info(f"Table {WEATHER_TABLE} already exists")

    # Wait for all created tables to be active
    for table_name in created_tables:
        if not wait_for_table_active(dynamodb, table_name):
            logger.error(f"Failed to wait for table {table_name} to be active")
            return False

    return True


# Function to list all tables
def list_tables(dynamodb):
    """List all tables in DynamoDB"""
    try:
        tables = list(dynamodb.tables.all())
        logger.info(f"Found {len(tables)} tables:")
        for table in tables:
            logger.info(f"- {table.name}")
        return tables
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return []


# Function to insert/update user in DynamoDB
def put_user(dynamodb, user_data):
    """Store user data in DynamoDB"""
    try:
        users_table = dynamodb.Table(USERS_TABLE)

        # Check if user exists first (optional - you can skip this to save on read capacity)
        try:
            response = users_table.get_item(Key={'user_id': user_data['user_id']})

            # If user doesn't exist or we want to update, put the item
            if 'Item' not in response or user_data.get('update_existing', False):
                users_table.put_item(
                    Item={
                        'user_id': user_data['user_id'],
                        'handle': user_data['handle'],
                        'display_name': user_data.get('display_name', ''),
                        'avatar_url': user_data.get('avatar_url', ''),
                        'created_at': datetime.now().isoformat()
                    }
                )
                logger.info(f"User stored: {user_data['handle']}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, log error
                logger.error(f"Table {USERS_TABLE} does not exist")
            else:
                # Some other error
                raise

        return user_data['user_id']

    except Exception as e:
        logger.error(f"Error storing user: {e}")
        return None


# Function to notify the Flask API about new posts (batched every 15 minutes)
def notify_api_about_new_post(post):
    """Add post to notification buffer, to be sent at 15-minute intervals"""
    try:
        with NOTIFICATION_MUTEX:
            # Add post to buffer
            NOTIFICATION_BUFFER.append(post)
            logger.debug(
                f"Added post {post['post_id']} to notification buffer (current size: {len(NOTIFICATION_BUFFER)})")
    except Exception as e:
        logger.error(f"Error adding post to notification buffer: {e}")


# Function to send all buffered notifications
def send_buffered_notifications():
    """Send all buffered notifications to the API"""
    global LAST_NOTIFICATION_TIME

    with NOTIFICATION_MUTEX:
        if not NOTIFICATION_BUFFER:
            return  # Nothing to send

        posts_to_send = NOTIFICATION_BUFFER.copy()
        NOTIFICATION_BUFFER.clear()

    try:
        # Create a serializable version of the posts
        serializable_posts = []
        for post in posts_to_send:
            # Convert Decimal to float for JSON serialization
            serializable_post = {}
            for key, value in post.items():
                if isinstance(value, Decimal):
                    serializable_post[key] = float(value)
                else:
                    serializable_post[key] = value
            serializable_posts.append(serializable_post)

        # Send notification to Flask API
        payload = {
            'posts': serializable_posts
        }

        response = requests.post(
            NOTIFICATION_ENDPOINT,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            logger.info(f"Successfully notified API about {len(serializable_posts)} new posts")
        else:
            logger.warning(f"Failed to notify API: {response.status_code} - {response.text}")

        # Update last notification time
        LAST_NOTIFICATION_TIME = time.time()

    except Exception as e:
        logger.error(f"Error sending notifications to API: {e}")
        # Put the posts back in buffer
        with NOTIFICATION_MUTEX:
            NOTIFICATION_BUFFER.extend(posts_to_send)


# Function to check if it's time to send notifications
def check_notification_timer():
    """Check if it's time to send notifications (15-minute interval)"""
    current_time = time.time()
    if current_time - LAST_NOTIFICATION_TIME >= NOTIFICATION_INTERVAL:
        logger.info("Notification interval reached - sending buffered posts")
        send_buffered_notifications()
        return True
    return False


# Function to insert post into DynamoDB
def put_post(dynamodb, post_data):
    """Store post data in DynamoDB"""
    try:
        posts_table = dynamodb.Table(POSTS_TABLE)

        # DynamoDB doesn't support native float type, convert to Decimal
        confidence_score = Decimal(str(post_data.get('confidence_score', 0.0)))

        # Format the created_at and indexed_at as ISO strings safely
        if isinstance(post_data['created_at'], str):
            created_at = post_data['created_at']
        else:
            created_at = post_data['created_at'].isoformat()

        if isinstance(post_data['indexed_at'], str):
            indexed_at = post_data['indexed_at']
        else:
            indexed_at = post_data['indexed_at'].isoformat()

        # Get is_disaster value and convert to string for indexing
        is_disaster = post_data.get('is_disaster', False)
        is_disaster_str = 'true' if is_disaster else 'false'

        # Build the item
        item = {
            'post_id': post_data['post_id'],
            'indexed_at': indexed_at,  # Use as sort key
            'user_id': post_data['user_id'],
            'handle': post_data['handle'],
            'display_name': post_data.get('display_name', ''),
            'avatar_url': post_data.get('avatar_url', ''),
            'original_text': post_data['original_text'],
            'clean_text': post_data['clean_text'],
            'created_at': created_at,
            'location_name': post_data.get('location_name', ''),
            'disaster_type': post_data.get('disaster_type', 'unknown'),
            'confidence_score': confidence_score,
            'is_disaster': is_disaster,
            'is_disaster_str': is_disaster_str,  # Add string version for GSI
            'language': post_data.get('language', 'en')  # Store detected language
        }

        # Add media_urls if present (and set has_media based on media_urls)
        if 'media_urls' in post_data and post_data['media_urls']:
            item['media_urls'] = post_data['media_urls']
            item['has_media'] = True
        else:
            item['has_media'] = False

        # Put the item in the table
        posts_table.put_item(Item=item)
        logger.info(f"Post stored: {post_data['post_id']}")

        # Add to notification buffer (will be sent at 15-minute intervals)
        notify_api_about_new_post(item)

        return post_data['post_id']

    except Exception as e:
        logger.error(f"Error storing post: {e}")
        return None


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

    Args:
        client: The Bluesky client
        max_retries: Maximum number of login retries

    Returns:
        bool: True if session is valid, False if all retries failed
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Try a simple profile request to test if session is valid
            handle = os.getenv('API_HANDLE')

            # Use token for this request
            if not consume_token():
                # Wait for token to become available
                time.sleep(1)
                continue

            client.app.bsky.actor.get_profile({'actor': handle})
            logger.info("Bluesky session is valid")
            return True
        except Exception as e:
            logger.warning(f"Session validation failed (attempt {attempt}/{max_retries}): {e}")

            # Try to create a new session
            try:
                logger.info("Attempting to refresh Bluesky session...")

                # Use token for this request
                if not consume_token():
                    # Wait for token to become available
                    time.sleep(1)
                    continue

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


# Search Bluesky for posts with keywords
def search_bluesky_for_keywords(client, keyword, since_time, max_posts=10, max_retries=3):
    """
    Search Bluesky for posts containing a keyword since a specific time

    Args:
        client: The Bluesky client
        keyword: Keyword to search for
        since_time: ISO-formatted time string to search from
        max_posts: Maximum number of posts to return
        max_retries: Maximum number of retry attempts

    Returns:
        Response object or None if failed
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Check if we have a token available
            if not consume_token():
                # If no token available, wait a bit before continuing
                token_wait = RATE_LIMIT_WINDOW / MAX_REQUESTS_PER_WINDOW
                logger.warning(f"Rate limit reached, waiting {token_wait:.2f}s for next token")
                time.sleep(token_wait + 0.1)  # Add a small buffer
                continue

            # Format the since_time correctly for the API
            if isinstance(since_time, datetime):
                since_str = since_time.replace(microsecond=0).isoformat()
                if since_str.endswith('+00:00'):
                    since_str = since_str.replace('+00:00', 'Z')
            else:
                # If it's already a string, ensure it's in the correct format
                since_str = since_time
                if since_str.endswith('+00:00'):
                    since_str = since_str.replace('+00:00', 'Z')

            logger.info(f"Searching for '{keyword}' since {since_str}")

            # Make the API request with rate limiting
            response = client.app.bsky.feed.search_posts(
                params={'q': keyword, 'limit': max_posts, 'cursor': None, 'since': since_str}
            )

            return response

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error searching for '{keyword}' (attempt {attempt}/{max_retries}): {error_msg}")

            # Check if this looks like a rate limit error
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                logger.warning(f"Rate limit detected. Waiting longer for retry.")
                time.sleep(30)  # Wait longer for rate limit errors
            elif attempt < max_retries:
                # For other errors, use exponential backoff
                wait_time = min(30, 2 ** attempt)
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

            # Check if we need to refresh the session
            if "auth" in error_msg.lower() or "unauthorized" in error_msg.lower():
                if ensure_bluesky_session(client):
                    logger.info("Session refreshed, retrying search")
                    continue

    logger.error(f"All {max_retries} attempts failed for keyword '{keyword}'")
    return None


# Process new posts with rate limiting
def process_keyword_feed(dynamodb, tokenizer, model, id2label, client):
    """
    Process posts containing keywords with proper rate limiting
    """
    json_file_path = "disaster_posts.json"
    processed_ids = set()  # Track processed post IDs to avoid duplicates

    # Load or initialize last processed timestamps
    last_processed_times = init_last_processed_times()

    # Load existing posts data if file exists
    try:
        with open(json_file_path, "r", encoding="utf-8") as json_file:
            posts_data = json.load(json_file)
            # Add existing post IDs to processed set
            for post in posts_data:
                processed_ids.add(post.get("uri", ""))
    except (FileNotFoundError, json.JSONDecodeError):
        posts_data = []

    initial_post_count = len(posts_data)
    logger.info(f"Loaded {initial_post_count} existing posts from JSON file")

    try:
        # Round-robin through keywords
        while True:
            for keyword in DISASTER_KEYWORDS:
                try:
                    # Get the last processed time for this keyword
                    since_time = last_processed_times.get(keyword)

                    # Convert string to datetime if needed
                    if isinstance(since_time, str):
                        since_time = datetime.fromisoformat(since_time.replace('Z', '+00:00'))

                    # Search for posts with this keyword
                    response = search_bluesky_for_keywords(client, keyword, since_time)

                    if not response or not hasattr(response, 'posts') or not response.posts:
                        logger.info(f"No new posts found for keyword: {keyword}")
                        continue

                    logger.info(f"Found {len(response.posts)} posts for keyword: {keyword}")

                    # Track newest post time to update last_processed_times
                    newest_time = since_time
                    new_post_count = 0

                    # Process each post
                    for post in response.posts:
                        try:
                            uri = post.uri

                            # Skip if we've already processed this post
                            if uri in processed_ids:
                                continue

                            # Extract post data
                            text = post.record.text

                            # Check if post is in English
                            if not is_english(text):
                                logger.info(f"Skipping non-English post: {uri}")
                                continue

                            # Add to processed set to avoid duplication
                            processed_ids.add(uri)

                            # Extract other fields
                            did = post.author.did
                            handle = post.author.handle
                            display_name = post.author.display_name or ''
                            avatar_url = post.author.avatar or ''
                            cleaned_text = clean_text(text)
                            created_at = safe_parse_date(post.record.created_at)
                            indexed_at = safe_parse_date(post.indexed_at)

                            # Update newest time if needed
                            if indexed_at > newest_time:
                                newest_time = indexed_at

                            # Check for media
                            media_urls = []
                            if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images'):
                                for image in post.record.embed.images:
                                    if hasattr(image, 'image') and hasattr(image.image, 'ref') and hasattr(
                                            image.image.ref, 'link'):
                                        image_url = f"https://cdn.bsky.app/img/feed_fullsize/{image.image.ref.link}"
                                        media_urls.append(image_url)

                            # Predict disaster type
                            predicted_label, confidence_score = predict_disaster(tokenizer, model, id2label,
                                                                                 cleaned_text)

                            # Two different thresholds
                            threshold = 0.1  # Lower threshold for JSON/logging
                            db_threshold = 0.95  # Higher threshold for database

                            # Determine disaster status
                            is_disaster = confidence_score >= threshold
                            is_disaster_db = confidence_score >= db_threshold

                            # Store user
                            user_data = {
                                'user_id': did,
                                'handle': handle,
                                'display_name': display_name,
                                'avatar_url': avatar_url
                            }
                            put_user(dynamodb, user_data)

                            # Store post
                            post_data = {
                                'post_id': uri,
                                'user_id': did,
                                'handle': handle,
                                'display_name': display_name,
                                'avatar_url': avatar_url,
                                'original_text': text,
                                'clean_text': cleaned_text,
                                'created_at': created_at,
                                'indexed_at': indexed_at,
                                'location_name': "",
                                'media_urls': media_urls,
                                'disaster_type': predicted_label,
                                'confidence_score': confidence_score,
                                'is_disaster': is_disaster_db,
                                'language': 'en'  # We've verified it's English
                            }
                            put_post(dynamodb, post_data)

                            # Prepare post data for JSON
                            json_post_data = {
                                "uri": uri,
                                "handle": handle,
                                "display_name": display_name,
                                "text": text,
                                "clean_text": cleaned_text,
                                "timestamp": created_at.isoformat(),
                                "avatar": avatar_url,
                                "media": media_urls,
                                "predicted_disaster_type": predicted_label,
                                "confidence_score": confidence_score,
                                "is_disaster": is_disaster,
                                "location": ""
                            }

                            # Add to posts data (at the beginning for newest first)
                            posts_data.insert(0, json_post_data)
                            new_post_count += 1

                            logger.info(f"Processed new post: {uri}")

                        except Exception as e:
                            logger.error(f"Error processing individual post: {e}")
                            continue

                    # Update last processed time for this keyword
                    if newest_time > since_time:
                        last_processed_times[keyword] = newest_time.isoformat()
                        save_last_processed_times(last_processed_times)
                        logger.info(f"Updated last processed time for '{keyword}' to {newest_time.isoformat()}")

                    # Report on new posts
                    if new_post_count > 0:
                        logger.info(f"Processed {new_post_count} new posts for keyword: {keyword}")

                        # Limit the number of posts we keep in the JSON file
                        max_json_posts = 1000
                        if len(posts_data) > max_json_posts:
                            posts_data = posts_data[:max_json_posts]

                        # Save posts to JSON
                        with open(json_file_path, "w", encoding="utf-8") as json_file:
                            json.dump(posts_data, json_file, indent=4, ensure_ascii=False)

                        logger.info(f"Saved {len(posts_data)} posts to JSON")

                except Exception as e:
                    error_text = str(e)
                    logger.error(f"Error in keyword search for '{keyword}': {error_text}")

                    # Check if this is an authentication/session error
                    if 'auth' in error_text.lower() or 'session' in error_text.lower():
                        ensure_bluesky_session(client)

                    continue  # Move to next keyword

                # Brief delay between keywords to help with rate limiting
                time.sleep(1)

            # Check if it's time to send notifications
            check_notification_timer()

            # After processing all keywords, wait before next round
            # This time is adjustable based on how aggressive you want to be
            wait_time = 60  # 1 minute between full cycles
            logger.info(f"Completed full keyword cycle. Waiting {wait_time} seconds until next cycle...")
            time.sleep(wait_time)

    except KeyboardInterrupt:
        logger.info("Post monitoring interrupted by user")

    except Exception as e:
        logger.error(f"Fatal error in post monitoring: {e}")

    finally:
        # Send any remaining notifications
        if NOTIFICATION_BUFFER:
            logger.info(f"Sending {len(NOTIFICATION_BUFFER)} buffered notifications before exit")
            send_buffered_notifications()

        # Always save the latest data before exiting
        try:
            with open(json_file_path, "w", encoding="utf-8") as json_file:
                json.dump(posts_data, json_file, indent=4, ensure_ascii=False)
            logger.info("Saved posts data before exit")

            # Save last processed times
            save_last_processed_times(last_processed_times)
            logger.info("Saved last processed times before exit")
        except Exception as e:
            logger.error(f"Error saving final data: {e}")


# Notification thread function
def notification_thread_func():
    """Background thread to send notifications at regular intervals"""
    while True:
        try:
            # Sleep for a shorter time to check more frequently
            time.sleep(60)  # Check every minute

            # Check if it's time to send notifications
            if check_notification_timer():
                logger.info("Notification interval reached (checked from notification thread)")
        except Exception as e:
            logger.error(f"Error in notification thread: {e}")


# Session monitoring thread
def session_monitor_thread(client):
    """Background thread to keep the Bluesky session alive"""
    while True:
        try:
            time.sleep(600)  # Check every 10 minutes
            logger.info("Performing session health check")

            # Check if we have a token available
            if consume_token():
                handle = os.getenv('API_HANDLE')
                client.app.bsky.actor.get_profile({'actor': handle})
                logger.info("Session is still valid")
            else:
                logger.info("Token not available for session check, will try later")
        except Exception as e:
            logger.warning(f"Session error in monitor thread: {e}")
            try:
                if consume_token():
                    logger.info("Refreshing session from background thread")
                    client.login(os.getenv('API_HANDLE'), os.getenv('API_PW'))
                    logger.info("Session refreshed successfully")
            except Exception as login_error:
                logger.error(f"Failed to refresh session: {login_error}")


# Main function
def main(force_recreate_tables=False):
    """
    Main entry point for the application

    Args:
        force_recreate_tables (bool): If True, delete and recreate all tables.
    """
    try:
        # Initialize DynamoDB
        dynamodb = init_dynamodb()

        # Initialize AI model
        MODEL_PATH = os.getenv('MODEL_PATH', 'checkpoint-1800')  # Get from env var or use default
        tokenizer, model, id2label = init_model(MODEL_PATH)

        # Create tables if needed
        logger.info("Ensuring tables exist and are active...")
        if not create_tables(dynamodb, force_recreate=force_recreate_tables):
            logger.error("Failed to create tables. Exiting.")
            return

        # Set up Bluesky client
        logger.info("Setting up Bluesky client...")
        client = Client()
        client.login(os.getenv('API_HANDLE'), os.getenv('API_PW'))

        # Start session monitoring thread
        session_thread = threading.Thread(target=session_monitor_thread, args=(client,), daemon=True)
        session_thread.start()
        logger.info("Started session monitoring thread")

        # Start notification thread
        notification_thread = threading.Thread(target=notification_thread_func, daemon=True)
        notification_thread.start()
        logger.info("Started notification thread (15-minute intervals)")

        # Process posts with keywords
        logger.info("Starting keyword-based post monitoring...")
        process_keyword_feed(dynamodb, tokenizer, model, id2label, client)

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")


if __name__ == "__main__":
    main(False)