import boto3
import time
from datetime import datetime, timedelta, timezone
import json
import os
from atproto import Client, models
from transformers import AutoTokenizer, AutoModelForSequenceClassification, RobertaConfig
import torch.nn.functional as F
from dotenv import load_dotenv
import re
import logging
import uuid
from decimal import Decimal
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("disaster_feed.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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


# Extract location from text - placeholder for future NLP implementation
def extract_location(text):
    """
    Extract location name from text. Returns empty string if not found.

    Note: This is a placeholder. In the future, this should be replaced with
    a more sophisticated NLP-based location extraction model.
    """
    # Currently not implemented - will return empty string
    return ""


# Safe date parsing function to handle problematic ISO formats
def safe_parse_date(date_string):
    """
    Safely parse date strings into datetime objects, handling various formats.
    """
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


# Function to delete a table if it exists
def delete_table_if_exists(dynamodb, table_name):
    """Delete a table if it exists"""
    try:
        if table_exists(dynamodb, table_name):
            table = dynamodb.Table(table_name)
            table.delete()
            logger.info(f"Deleting table {table_name}...")

            # Wait for table to be deleted with timeout
            for attempt in range(1, 13):  # Try for up to 1 minute
                try:
                    dynamodb.meta.client.describe_table(TableName=table_name)
                    logger.info(f"Waiting for table {table_name} to be deleted... Attempt {attempt}/12")
                    time.sleep(5)
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        logger.info(f"Table {table_name} deleted")
                        return True

            logger.error(f"Table {table_name} did not delete within the timeout period")
            return False
        return False
    except Exception as e:
        logger.error(f"Error deleting table {table_name}: {e}")
        return False


# Function to create all required tables
def create_tables(dynamodb, force_recreate=False):
    """Create all required tables"""
    created_tables = []

    # Optionally force recreation of tables
    if force_recreate:
        for table_name in [POSTS_TABLE, USERS_TABLE, WEATHER_TABLE]:
            delete_table_if_exists(dynamodb, table_name)

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
                        'created_at': datetime.now().isoformat()  # Fixed here
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
            'is_disaster_str': is_disaster_str  # Add string version for GSI
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

        return post_data['post_id']

    except Exception as e:
        logger.error(f"Error storing post: {e}")
        return None


# Function to insert weather data into DynamoDB
def put_weather_data(dynamodb, weather_data):
    """Store weather data in DynamoDB"""
    try:
        weather_table = dynamodb.Table(WEATHER_TABLE)

        # Generate a UUID for the weather data
        weather_id = str(uuid.uuid4())

        # Convert numeric values to Decimal for DynamoDB
        for field in ['temperature', 'humidity', 'wind_speed', 'latitude', 'longitude']:
            if field in weather_data and weather_data[field] is not None:
                weather_data[field] = Decimal(str(weather_data[field]))

        # Format the collected_at as ISO string
        collected_at = datetime.now().isoformat()
        if 'collected_at' in weather_data:
            if isinstance(weather_data['collected_at'], datetime):
                collected_at = weather_data['collected_at'].isoformat()
            else:
                collected_at = weather_data['collected_at']

        # Build the item
        item = {
            'weather_id': weather_id,
            'post_id': weather_data['post_id'],
            'location_name': weather_data.get('location_name', ''),
            'latitude': weather_data.get('latitude', Decimal('0')),
            'longitude': weather_data.get('longitude', Decimal('0')),
            'weather_condition': weather_data.get('weather_condition', ''),
            'temperature': weather_data.get('temperature', Decimal('0')),
            'humidity': weather_data.get('humidity', Decimal('0')),
            'wind_speed': weather_data.get('wind_speed', Decimal('0')),
            'collected_at': collected_at
        }

        # Put the item in the table
        weather_table.put_item(Item=item)
        logger.info(f"Weather data stored for post: {weather_data['post_id']}")

        return weather_id

    except Exception as e:
        logger.error(f"Error storing weather data: {e}")
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

# Real-time Processing Function
def process_feed(dynamodb, tokenizer, model, id2label, client):
    """Process posts without rate limiting"""
    log_file_path = "disaster_feed.log"
    json_file_path = "posts.json"
    
    # Polling configuration
    poll_interval = 60  # Seconds between polls
    
    # Load existing posts data if file exists
    try:
        with open(json_file_path, "r", encoding="utf-8") as json_file:
            posts_data = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        posts_data = []
    
    initial_post_count = len(posts_data)
    logger.info(f"Loaded {initial_post_count} existing posts from JSON file")
    
    with open(log_file_path, "a", encoding='utf-8') as log_file:
        try:
            logger.info("Starting keyword-based post monitoring...")
            
            while True:
                try:
                    processed_in_cycle = set()
                    
                    # Search for each keyword
                    for keyword in DISASTER_KEYWORDS:                            
                        logger.info(f"Searching for posts containing: {keyword}")
                        response = search_bluesky_for_keywords(client, keyword)
                        
                        if not response or not hasattr(response, 'posts'):
                            logger.info(f"No posts found for keyword: {keyword}")
                            continue
                        
                        logger.info(f"Found {len(response.posts)} posts for keyword: {keyword}")
                        
                        # Process each post
                        for post in response.posts:                            
                            try:
                                uri = post.uri
                                if uri in processed_in_cycle:
                                    continue
                                    
                                processed_in_cycle.add(uri)

                                # Extract all needed data
                                did = post.author.did
                                handle = post.author.handle
                                display_name = post.author.display_name or ''
                                avatar_url = post.author.avatar or ''
                                text = post.record.text
                                cleaned_text = clean_text(text)
                                created_at = safe_parse_date(post.record.created_at)
                                indexed_at = safe_parse_date(post.indexed_at)

                                # For now, we're not extracting location
                                location_name = ""

                                # Check for media
                                media_urls = []
                                if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images'):
                                    for image in post.record.embed.images:
                                        if hasattr(image, 'image') and hasattr(image.image, 'ref') and hasattr(image.image.ref, 'link'):
                                            image_url = f"https://cdn.bsky.app/img/feed_fullsize/{image.image.ref.link}"
                                            media_urls.append(image_url)

                                # Predict disaster type
                                predicted_label, confidence_score = predict_disaster(tokenizer, model, id2label, cleaned_text)

                                # Two different thresholds
                                threshold = 0.1  # Lower threshold for JSON/logging
                                db_threshold = 0.8  # Higher threshold for database

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
                                    'location_name': location_name,
                                    'media_urls': media_urls,
                                    'disaster_type': predicted_label,
                                    'confidence_score': confidence_score,
                                    'is_disaster': is_disaster_db
                                }
                                put_post(dynamodb, post_data)

                                # Prepare post data for JSON (for the web interface)
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
                                    "location": location_name
                                }

                                # Add to posts data (at the beginning for newest first)
                                posts_data.insert(0, json_post_data)

                                # Log the new post
                                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                log_entry = f"[{current_time}] NEW POST: {text}\n"
                                if not is_disaster:
                                    log_entry += f"Predicted: Uncertain/Non-Disaster (Confidence: {confidence_score:.4f})\n\n"
                                else:
                                    log_entry += f"Predicted: {predicted_label} (Confidence: {confidence_score:.4f})\n\n"

                                log_file.write(log_entry)
                                log_file.flush()  # Ensure it's written immediately

                                logger.info(f"Processed new post: {uri}")

                            except Exception as e:
                                logger.error(f"Error processing post: {e}")
                                continue

                    # Report on new posts

                except Exception as e:
                    error_text = str(e)

                    # Check if this is an authentication/session error
                    if 'auth' in error_text.lower() or 'session' in error_text.lower():
                        logger.warning(f"Possible session error: {error_text}")
                        try:
                            # Try to refresh the session
                            logger.info("Attempting to refresh session...")
                            client.login(os.getenv('API_HANDLE'), os.getenv('API_PW'))
                            logger.info("Successfully refreshed session")
                        except Exception as login_error:
                            logger.error(f"Failed to refresh session: {login_error}")
                            # Wait a bit longer after session errors
                            time.sleep(30)
                    else:
                        logger.error(f"Error fetching or processing posts: {error_text}")
                        # Normal error backoff
                        time.sleep(15)

                # Use a consistent polling interval to avoid rate limits and provide predictability
                logger.info(f"Waiting {poll_interval} seconds until next check for new posts...")
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Post monitoring interrupted by user")

        except Exception as e:
            logger.error(f"Fatal error in post monitoring: {e}")

        finally:
            # Always save the latest data before exiting
            try:
                with open(json_file_path, "w", encoding="utf-8") as json_file:
                    json.dump(posts_data, json_file, indent=4, ensure_ascii=False)
                logger.info("Saved posts data before exit")
            except Exception as e:
                logger.error(f"Error saving final data: {e}")


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

# Obtains posts using a search from keywords.
def search_bluesky_for_keywords(client, keyword, hours=3, max_retries=3):
    """Search Bluesky for posts with retry logic and English language filter"""
    for attempt in range(1, max_retries + 1):
        try:
            # Calculate the time window
            since_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Format as ISO 8601 string without microseconds and with 'Z' suffix
            since_str = since_time.replace(microsecond=0).isoformat()
            if since_str.endswith('+00:00'):
                since_str = since_str.replace('+00:00', 'Z')
            
            logger.info(f"Searching for '{keyword}' since {since_str}")
            
            # Make the API request with English language filter
            response = client.app.bsky.feed.search_posts(
                params={
                    'q': keyword,
                    'limit': 100,  # Increased limit since we removed hourly limit
                    'since': since_str,
                    'lang': "en"  # Explicit English language filter
                }
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
    
def get_timeline_posts(client, tokenizer, model, id2label, dynamodb, max_posts=50):
    """
    Alternative method to get posts from the user's timeline when custom feed fails.

    Args:
        client: The Bluesky client
        tokenizer, model, id2label: ML model components
        dynamodb: DynamoDB client
        max_posts: Maximum number of posts to process

    Returns:
        List of processed posts
    """
    logger.info("Using timeline fallback method to retrieve posts")
    processed_posts = []

    try:
        # Get posts from user's timeline instead of custom feed
        response = client.app.bsky.feed.get_timeline({'limit': max_posts})

        if not response or not hasattr(response, 'feed'):
            logger.warning("No posts found in timeline")
            return []

        logger.info(f"Found {len(response.feed)} posts in timeline")

        # Process posts similar to the main feed processing
        for post in response.feed:
            try:
                # Extract post details (similar to main process)
                uri = post.post.uri
                did = post.post.author.did
                handle = post.post.author.handle
                display_name = post.post.author.display_name or ''
                avatar_url = post.post.author.avatar or ''
                text = post.post.record.text
                cleaned_text = clean_text(text)

                # Check if this is potentially a disaster-related post
                predicted_label, confidence_score = predict_disaster(tokenizer, model, id2label, cleaned_text)

                # Only process posts that might be disaster-related (saves resources)
                if confidence_score >= 0.1:
                    # Safely parse dates
                    created_at = safe_parse_date(post.post.record.created_at)
                    indexed_at = safe_parse_date(post.post.indexed_at)

                    # For now, we're not extracting location
                    location_name = ""

                    # Check for media
                    media_urls = []
                    if hasattr(post.post.record, 'embed') and hasattr(post.post.record.embed, 'images'):
                        for image in post.post.record.embed.images:
                            if hasattr(image, 'image') and hasattr(image.image, 'ref') and hasattr(image.image.ref,
                                                                                                   'link'):
                                image_url = f"https://cdn.bsky.app/img/feed_fullsize/{image.image.ref.link}"
                                media_urls.append(image_url)

                    # Two different thresholds
                    threshold = 0.1  # Lower threshold for JSON/logging
                    db_threshold = 0.7  # Higher threshold for database

                    # Determine disaster status
                    is_disaster = confidence_score >= threshold
                    is_disaster_db = confidence_score >= db_threshold

                    # Store in database if it passes the threshold
                    if is_disaster:
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
                            'location_name': location_name,
                            'media_urls': media_urls,
                            'disaster_type': predicted_label,
                            'confidence_score': confidence_score,
                            'is_disaster': is_disaster_db
                        }
                        put_post(dynamodb, post_data)

                        # Add to processed posts
                        processed_posts.append({
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
                            "location": location_name
                        })

                        logger.info(f"Processed potential disaster post from timeline: {uri}")
            except Exception as e:
                logger.error(f"Error processing timeline post: {e}")
                continue

        return processed_posts

    except Exception as e:
        logger.error(f"Error fetching timeline: {e}")
        return []
    

def process_feed_with_fallbacks(dynamodb, tokenizer, model, id2label, client):
    """
    Process feed with fallback mechanisms for greater reliability
    """
    # Set up counters and state
    main_feed_failures = 0
    last_successful_time = time.time()

    while True:
        try:
            # Try the main real-time feed approach
            process_feed(dynamodb, tokenizer, model, id2label, client)
        except Exception as e:
            logger.error(f"Error in main feed processing: {e}")
            main_feed_failures += 1

            # If we've had multiple failures or it's been a while since success
            if main_feed_failures > 3 or (time.time() - last_successful_time) > 1800:  # 30 minutes
                logger.warning("Multiple feed failures. Trying alternative approach.")

                try:
                    # Use timeline fallback approach
                    posts = get_timeline_posts(client, tokenizer, model, id2label, dynamodb)

                    if posts:
                        logger.info(f"Successfully processed {len(posts)} posts using fallback method")
                        main_feed_failures = 0  # Reset failure counter
                        last_successful_time = time.time()
                    else:
                        logger.warning("Fallback method also failed to retrieve posts")
                except Exception as fallback_error:
                    logger.error(f"Error in fallback processing: {fallback_error}")

            # Exponential backoff on repeated failures
            wait_time = min(300, 30 * (2 ** min(main_feed_failures, 5)))
            logger.info(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)




# Main function
def main(force_recreate_tables=False):
    """
    Main entry point for the application - simplified version without shutdown handling

    Args:
        force_recreate_tables (bool): If True, delete and recreate all tables.
    """
    try:
        # Initialize DynamoDB
        dynamodb = init_dynamodb()

        # Initialize AI model
        MODEL_PATH = r'D:\School Stuff\UTD\2025\Project\Model\checkpoint-1800'
        tokenizer, model, id2label = init_model(MODEL_PATH)

        # List existing tables
        logger.info("Listing existing tables...")
        list_tables(dynamodb)

        # Create tables only if needed or if force_recreate_tables is True
        logger.info("Ensuring tables exist and are active...")
        if not create_tables(dynamodb, force_recreate=force_recreate_tables):
            logger.error("Failed to create tables. Exiting.")
            return

        # List tables again to confirm creation
        logger.info("Tables after initialization:")
        list_tables(dynamodb)

        # Set up Bluesky client
        logger.info("Setting up Bluesky client...")
        client = Client()
        client.login(os.getenv('API_HANDLE'), os.getenv('API_PW'))

        # Start a simple session monitoring thread (optional but helpful)
        import threading

        def keep_session_alive():
            """Background thread to keep the Bluesky session alive"""
            while True:
                try:
                    time.sleep(600)  # Check every 10 minutes
                    logger.info("Performing session health check")
                    handle = os.getenv('API_HANDLE')
                    client.app.bsky.actor.get_profile({'actor': handle})
                    logger.info("Session is still valid")
                except Exception as e:
                    logger.warning(f"Session error in monitor thread: {e}")
                    try:
                        logger.info("Refreshing session from background thread")
                        client.login(os.getenv('API_HANDLE'), os.getenv('API_PW'))
                        logger.info("Session refreshed successfully")
                    except Exception as login_error:
                        logger.error(f"Failed to refresh session: {login_error}")

        # Start the thread as daemon so it exits when main thread exits
        session_thread = threading.Thread(target=keep_session_alive, daemon=True)
        session_thread.start()
        logger.info("Started session monitoring thread")

        # Process new posts
        logger.info("Starting new posts only mode...")
        process_feed_with_fallbacks(dynamodb, tokenizer, model, id2label, client)

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")


if __name__ == "__main__":
    main(False)