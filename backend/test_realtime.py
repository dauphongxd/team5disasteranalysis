import boto3
import uuid
import time
import random
import datetime
import os
import json
import requests
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Initialize DynamoDB client
region = os.getenv('AWS_REGION', 'us-east-1')
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

dynamodb = boto3.resource('dynamodb',
                          region_name=region,
                          aws_access_key_id=aws_access_key_id,
                          aws_secret_access_key=aws_secret_access_key)

# DynamoDB table name
POSTS_TABLE = 'DisasterFeed_Posts'
posts_table = dynamodb.Table(POSTS_TABLE)

# Flask API endpoint for WebSocket notifications
# This should match your Flask API's host and port
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
NOTIFICATION_ENDPOINT = f"{API_BASE_URL}/api/notify-new-post"

# Sample disaster types
disaster_types = [
    "flood", "earthquake", "hurricane", "tornado", "wild fire",
    "volcano", "tsunami", "blizzard", "dust storm"
]

# Sample handles
handles = [
    "weather_alert", "emergency_info", "disaster_watch", "stormchaser",
    "climate_news", "safety_first", "quake_monitor", "alert_system"
]

# Sample display names
display_names = [
    "Weather Alert", "Emergency Info", "Disaster Watch", "Storm Chaser",
    "Climate News", "Safety First", "Quake Monitor", "Alert System"
]

# Sample avatar URLs
avatar_urls = [
    "https://via.placeholder.com/150",
    "https://via.placeholder.com/150/FF0000/FFFFFF",
    "https://via.placeholder.com/150/0000FF/FFFFFF",
    "https://via.placeholder.com/150/00FF00/FFFFFF"
]

# Sample text templates
text_templates = [
    "Breaking: {disaster_type} reported in {location}. Stay safe!",
    "UPDATE: {disaster_type} conditions worsening in {location}. Evacuate if instructed.",
    "ALERT: {disaster_type} warning issued for {location}. Prepare necessary supplies.",
    "Officials responding to {disaster_type} situation in {location}. Follow local authorities' instructions.",
    "Monitoring {disaster_type} development in {location}. Updates to follow."
]

# Sample locations
locations = [
    "Miami, FL", "Los Angeles, CA", "New York, NY", "Houston, TX",
    "Chicago, IL", "Phoenix, AZ", "Seattle, WA", "Denver, CO",
    "New Orleans, LA", "San Francisco, CA"
]


def generate_random_post():
    """Generate a random post for testing"""
    disaster_type = random.choice(disaster_types)
    location = random.choice(locations)

    # Create post content
    text_template = random.choice(text_templates)
    text = text_template.format(disaster_type=disaster_type, location=location)

    # Generate random post data
    now = datetime.datetime.now()
    post_id = f"at://did:test:{uuid.uuid4()}"
    user_id = f"did:test:{uuid.uuid4().hex[:16]}"
    handle = random.choice(handles)
    display_name = random.choice(display_names)
    avatar_url = random.choice(avatar_urls)
    confidence_score = Decimal(str(random.uniform(0.7, 0.99)))

    # Format timestamps
    created_at = now.isoformat()
    indexed_at = now.isoformat()

    # Create the post item
    post = {
        'post_id': post_id,
        'indexed_at': indexed_at,
        'user_id': user_id,
        'handle': handle,
        'display_name': display_name,
        'avatar_url': avatar_url,
        'original_text': text,
        'clean_text': text.lower(),
        'created_at': created_at,
        'location_name': location,
        'disaster_type': disaster_type,
        'confidence_score': confidence_score,
        'is_disaster': True,
        'is_disaster_str': 'true'
    }

    return post


def notify_api_about_new_post(post):
    """Notify the Flask API about a new post"""
    try:
        # Create a JSON-serializable version of the post
        # Convert Decimal to float for JSON serialization
        serializable_post = {}
        for key, value in post.items():
            if isinstance(value, Decimal):
                serializable_post[key] = float(value)
            else:
                serializable_post[key] = value

        # Send notification to Flask API
        payload = {
            'post': serializable_post
        }

        response = requests.post(
            NOTIFICATION_ENDPOINT,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            print(f"Successfully notified API about new post")
        else:
            print(f"Failed to notify API: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Error notifying API: {e}")


def add_test_post():
    """Add a test post to DynamoDB"""
    post = generate_random_post()

    try:
        # First add to DynamoDB
        posts_table.put_item(Item=post)
        print(f"Added post to DynamoDB: {post['disaster_type']} - {post['post_id']}")
        print(f"Content: {post['original_text']}")

        # Then notify Flask API
        notify_api_about_new_post(post)

        return True
    except Exception as e:
        print(f"Error adding post: {e}")
        return False


def run_test(num_posts=5, delay_seconds=10):
    """Run a test that adds multiple posts with delays between them"""
    print(f"Starting test: Adding {num_posts} posts with {delay_seconds} second delays")

    for i in range(num_posts):
        print(f"\nAdding post {i + 1}/{num_posts}...")
        success = add_test_post()

        if i < num_posts - 1:
            print(f"Waiting {delay_seconds} seconds...")
            time.sleep(delay_seconds)

    print("\nTest completed!")


if __name__ == "__main__":
    # Get user input for test parameters
    try:
        num_posts = int(input("How many test posts to create? (default: 5): ") or "5")
        delay_seconds = int(input("Seconds between posts? (default: 10): ") or "10")
    except ValueError:
        print("Invalid input, using defaults")
        num_posts = 5
        delay_seconds = 10

    run_test(num_posts, delay_seconds)