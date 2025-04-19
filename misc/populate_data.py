import boto3
import time
import datetime
import random
import string
import uuid
import os
import re
import logging
from decimal import Decimal
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("synthetic_disaster_feed.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env')


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


# Define table names
USERS_TABLE = 'DisasterFeed_Users'
POSTS_TABLE = 'DisasterFeed_Posts'

# Define disaster types
DISASTER_TYPES = [
    "avalanche", "blizzard", "bush_fire", "cyclone", "dust_storm",
    "earthquake", "flood", "forest_fire", "haze", "hurricane",
    "landslide", "meteor", "storm", "tornado", "tsunami",
    "typhoon", "volcano", "wild_fire", "unknown"
]

# Locations for each disaster type
LOCATIONS = {
    "avalanche": ["Rocky Mountains", "Alps", "Himalayas", "Andes", "Cascades", "Sierra Nevada"],
    "blizzard": ["Minnesota", "North Dakota", "Montana", "Wyoming", "Colorado", "Nebraska"],
    "bush_fire": ["California", "Australia", "Portugal", "Greece", "Spain", "South Africa"],
    "cyclone": ["Bay of Bengal", "Arabian Sea", "Indian Ocean", "South Pacific", "Madagascar"],
    "dust_storm": ["Arizona", "Texas", "New Mexico", "Nevada", "Sahara Desert", "Gobi Desert"],
    "earthquake": ["California", "Japan", "Mexico", "Turkey", "Indonesia", "Chile"],
    "flood": ["Mississippi River", "Ganges", "Yangtze", "Thames", "Queensland", "Louisiana"],
    "forest_fire": ["California", "Oregon", "Washington", "Colorado", "Canada", "Australia"],
    "haze": ["Singapore", "Malaysia", "Indonesia", "Thailand", "Philippines", "California"],
    "hurricane": ["Florida", "Texas", "Louisiana", "North Carolina", "Caribbean", "Gulf of Mexico"],
    "landslide": ["Washington", "California", "Oregon", "Colombia", "Brazil", "Philippines"],
    "meteor": ["Russia", "Arizona", "Australia", "Atlantic Ocean", "Mexico", "Antarctic"],
    "storm": ["Midwest US", "East Coast US", "UK", "Northern Europe", "Japan", "Philippines"],
    "tornado": ["Oklahoma", "Kansas", "Texas", "Nebraska", "Iowa", "Missouri", "Alabama"],
    "tsunami": ["Japan", "Indonesia", "Thailand", "Sri Lanka", "India", "Chile"],
    "typhoon": ["Philippines", "Japan", "Taiwan", "China", "Vietnam", "South Korea"],
    "volcano": ["Hawaii", "Indonesia", "Philippines", "Italy", "Iceland", "Japan", "Mexico"],
    "wild_fire": ["California", "Oregon", "Washington", "Colorado", "Canada", "Australia"],
    "unknown": ["Various Locations", "Remote Area", "Unspecified Region", "Multiple Regions"]
}

# Templates for disaster posts
DISASTER_TEMPLATES = {
    "avalanche": [
        "Massive avalanche reported near {location}. Emergency services responding. #Avalanche",
        "BREAKING: Avalanche in {location} has blocked roads and trapped hikers. Rescue underway.",
        "Heavy snowfall has triggered an avalanche in {location}. Several ski resorts evacuated.",
        "Watching the aftermath of a devastating avalanche that just hit {location}. Stay safe everyone.",
        "Avalanche warning issued for {location} after recent heavy snowfall. Avoid backcountry travel."
    ],
    "blizzard": [
        "Severe blizzard conditions in {location} with zero visibility. All roads closed. #WinterStorm",
        "Blizzard update: Over 2 feet of snow in {location} with more coming. Power outages reported.",
        "ALERT: Blizzard has shut down all transportation in {location}. Residents urged to stay indoors.",
        "Currently experiencing whiteout conditions in {location}. This blizzard is unlike anything I've seen before.",
        "Blizzard warning extended for {location} through tomorrow. Wind chills reaching -30F."
    ],
    "bush_fire": [
        "Major bush fire spreading rapidly near {location}. Evacuations underway. #Bushfire",
        "Bush fire has jumped containment lines in {location}. Air quality at dangerous levels.",
        "Watching the bush fire approach {location}. Firefighters working tirelessly to protect homes.",
        "The sky is orange from the bush fire in {location}. Ash falling everywhere.",
        "Bush fire update: 10,000 hectares burned near {location}. Wind change expected tonight."
    ],
    "cyclone": [
        "Cyclone approaching {location} with winds of 120mph. Coastal evacuations ordered. #CycloneAlert",
        "Cyclone has made landfall in {location}. Significant flooding and structural damage reported.",
        "Sitting through this cyclone in {location} is terrifying. The sound of the wind is deafening.",
        "Cyclone update: Storm surge of 15ft expected in {location}. All residents must evacuate immediately.",
        "Aftermath of cyclone in {location} reveals extensive damage. Relief efforts beginning."
    ],
    "dust_storm": [
        "Massive dust storm has enveloped {location}. Visibility reduced to near zero. #DustStorm",
        "Dust storm moving through {location} at alarming speed. Take shelter immediately.",
        "The dust storm in {location} has turned day into night. Roads closed due to poor visibility.",
        "Unprecedented dust storm currently hitting {location}. Air quality hazardous.",
        "Watching the wall of dust approach {location}. This is going to be a bad one."
    ],
    "earthquake": [
        "Strong earthquake just hit {location}. Buildings swaying. #Earthquake",
        "Magnitude 6.7 earthquake reported in {location}. Tsunami warning issued for coastal areas.",
        "Earthquake aftermath in {location} - collapsed buildings and widespread power outages.",
        "Just experienced a major earthquake here in {location}. Everyone please check on your neighbors.",
        "Aftershocks continue to rock {location} following this morning's major earthquake."
    ],
    "flood": [
        "Record flooding in {location} has breached levees. Neighborhoods underwater. #FloodAlert",
        "Flash flood emergency declared in {location}. Water rising at 2 feet per hour.",
        "Downtown {location} completely flooded. Rescue operations ongoing by boat.",
        "The flooding situation in {location} has worsened overnight. Hundreds evacuated.",
        "Aerial views of {location} flooding show the devastating extent of this disaster."
    ],
    "forest_fire": [
        "Massive forest fire raging in {location}. Smoke visible from 100 miles away. #ForestFire",
        "Forest fire in {location} has doubled in size overnight. Containment at 5%.",
        "Evacuation orders expanded in {location} as forest fire jumps highway.",
        "The forest fire has created its own weather system over {location}. Unprecedented fire behavior.",
        "Air tankers dropping fire retardant on the {location} forest fire. Praying for the firefighters."
    ],
    "haze": [
        "Dangerous haze levels in {location}. PSI readings above 300. #HazeAlert",
        "Schools closed in {location} due to hazardous haze conditions.",
        "The haze in {location} is so thick you can't see buildings across the street.",
        "Sixth straight day of severe haze in {location}. Masks mandatory outdoors.",
        "Satellite images show the extent of haze covering {location} and surrounding regions."
    ],
    "hurricane": [
        "Hurricane approaching {location} with Category 4 strength. Mandatory evacuations in effect. #HurricaneWarning",
        "Hurricane has made landfall in {location}. Storm surge flooding coastal communities.",
        "The eye of the hurricane is passing over {location} now. Brief calm before the worst returns.",
        "Hurricane damage assessment beginning in {location}. Infrastructure severely impacted.",
        "Riding out this hurricane in {location} was the most terrifying experience of my life."
    ],
    "landslide": [
        "Major landslide has buried portions of {location}. Search and rescue underway. #Landslide",
        "Heavy rains have triggered multiple landslides around {location}. Roads impassable.",
        "Hillside collapsed in {location} after days of rain. Several homes destroyed.",
        "Watching the mountain literally slide down in {location}. Never seen anything like it.",
        "Landslide warning remains in effect for {location} as soil continues to saturate."
    ],
    "meteor": [
        "Meteor spotted over {location}! Bright flash and sonic boom reported. #Meteor",
        "Confirmed: Meteor impact near {location}. Scientists en route to study the site.",
        "Dashcam footage shows amazing meteor streaking across the sky above {location}.",
        "The meteor that passed over {location} last night was estimated to be the size of a car.",
        "Meteor shower visibility exceptional tonight in {location}. Best viewing in decades."
    ],
    "storm": [
        "Severe storm battering {location} with tennis ball sized hail and 70mph winds. #StormAlert",
        "Storm has knocked out power to over 100,000 residents in {location}.",
        "Lightning strikes from this storm have started multiple fires around {location}.",
        "This storm passing through {location} is one of the most intense I've ever witnessed.",
        "Storm damage assessment underway in {location}. Significant structural damage reported."
    ],
    "tornado": [
        "Tornado on the ground in {location}! Take shelter immediately! #TornadoWarning",
        "Multiple tornadoes reported around {location}. Extensive damage in rural communities.",
        "Tornado has carved a path of destruction through {location}. Emergency services overwhelmed.",
        "The tornado that hit {location} has been rated EF4 with winds over 170mph.",
        "Watching this tornado form right outside {location} is both terrifying and mesmerizing."
    ],
    "tsunami": [
        "Tsunami warning issued for {location} following offshore earthquake. Move to higher ground immediately. #TsunamiAlert",
        "First tsunami waves hitting {location} now. Water rising rapidly in coastal areas.",
        "Tsunami has caused catastrophic damage along the coast of {location}. Many missing.",
        "Witnessed the ocean recede drastically at {location} beach - clear tsunami warning sign.",
        "Tsunami sirens sounding throughout {location}. Evacuation centers are open."
    ],
    "typhoon": [
        "Super typhoon approaching {location} with sustained winds of 150mph. #TyphoonAlert",
        "Typhoon has made landfall in {location}. Extreme wind and rain affecting millions.",
        "This typhoon in {location} is the strongest in recorded history for the region.",
        "Storm surge from typhoon has inundated coastal areas of {location}. Navy assisting with evacuations.",
        "Typhoon aftermath in {location} shows widespread devastation. International aid requested."
    ],
    "volcano": [
        "Volcano near {location} has begun erupting! Ash cloud rising to 30,000ft. #VolcanoAlert",
        "Volcanic eruption intensifying at {location}. Lava flows threatening communities.",
        "Evacuation zone expanded around {location} volcano as eruption grows more explosive.",
        "The ash from the {location} volcano has turned day into night. Breathing difficult.",
        "Volcanic activity at {location} showing signs of decreasing after three days of eruption."
    ],
    "wild_fire": [
        "Wildfire exploding in size near {location}. Zero containment. #WildfireAlert",
        "Wildfire smoke creating hazardous air quality across {location} and surrounding counties.",
        "The wildfire has jumped the highway and is now threatening {location}. Evacuations ordered.",
        "Night sky glowing orange from the wildfire approaching {location}. Firefighters working around the clock.",
        "Satellite imagery shows the massive spread of the wildfire threatening {location}."
    ],
    "unknown": [
        "Unusual natural event reported near {location}. Authorities investigating. #Alert",
        "Unidentified environmental incident in {location}. Stay tuned for updates.",
        "Strange atmospheric conditions observed around {location}. Scientists puzzled.",
        "Possible disaster situation developing in {location}. Details still unclear.",
        "Monitoring an unusual phenomenon near {location}. Will update as more information becomes available."
    ]
}

# Define synthetic users with profiles
USERS = [
    {"user_id": "did:plc:505be4aba41345689ce3a44c0b44c612", "handle": "meteorologist_mike",
     "display_name": "Meteorologist Mike", "avatar_url": "https://example.com/avatar1.jpg"},
    {"user_id": "did:plc:c06287fe0b9f487f8e9343af74edba2c", "handle": "storm_chaser", "display_name": "Storm Chaser",
     "avatar_url": "https://example.com/avatar2.jpg"},
    {"user_id": "did:plc:a2cb85ab7dd94c81bbefd47fd36a5af1", "handle": "disaster_reporter",
     "display_name": "Disaster Reporter", "avatar_url": "https://example.com/avatar3.jpg"},
    {"user_id": "did:plc:0eb9f73e7de14987bd63f49d7c8c28e7", "handle": "emergency_updates",
     "display_name": "Emergency Updates", "avatar_url": "https://example.com/avatar4.jpg"},
    {"user_id": "did:plc:dfd5eac1d5b84a0688b1bc126c1d62f7", "handle": "weather_news",
     "display_name": "Weather News Network", "avatar_url": "https://example.com/avatar5.jpg"},
    {"user_id": "did:plc:3da9ec9e74f94dcb9c5721620d71e5b9", "handle": "climate_watch", "display_name": "Climate Watch",
     "avatar_url": "https://example.com/avatar6.jpg"},
    {"user_id": "did:plc:b6e6fe8f296841158e4638965dcc01dd", "handle": "weather_watcher",
     "display_name": "Weather Watcher", "avatar_url": "https://example.com/avatar7.jpg"},
    {"user_id": "did:plc:8c7a71c5ef3c4bffad3c4f67982e7a05", "handle": "nature_alerts", "display_name": "Nature Alerts",
     "avatar_url": "https://example.com/avatar8.jpg"},
    {"user_id": "did:plc:24f94619698f40a29e93d35c64a8b9fc", "handle": "earth_monitor", "display_name": "Earth Monitor",
     "avatar_url": "https://example.com/avatar9.jpg"},
    {"user_id": "did:plc:e0ef5b27ce704c6abbab3cfb9642ae83", "handle": "science_reporter",
     "display_name": "Science Reporter", "avatar_url": "https://example.com/avatar10.jpg"},
    {"user_id": "did:plc:3b36d9931c1f4a3aaa99fad842146806", "handle": "local_eyewitness",
     "display_name": "Local Eyewitness", "avatar_url": "https://example.com/avatar11.jpg"},
    {"user_id": "did:plc:fd15a4bfaef14c8d9a148fa2b9c8f053", "handle": "first_responder",
     "display_name": "First Responder", "avatar_url": "https://example.com/avatar12.jpg"},
    {"user_id": "did:plc:a9dfd71ff1544ee1b55b94efd7f05b02", "handle": "community_alerts",
     "display_name": "Community Alerts", "avatar_url": "https://example.com/avatar13.jpg"},
    {"user_id": "did:plc:827b247be7014ee596b4dab251cf00bd", "handle": "weather_station",
     "display_name": "Weather Station", "avatar_url": "https://example.com/avatar14.jpg"},
    {"user_id": "did:plc:d14c7c3e89764a9c81ca64c53d72a22b", "handle": "disaster_relief",
     "display_name": "Disaster Relief", "avatar_url": "https://example.com/avatar15.jpg"}
]


# Function to store users in DynamoDB
def store_users(dynamodb):
    """Store all predefined users in DynamoDB"""
    try:
        users_table = dynamodb.Table(USERS_TABLE)

        for user in USERS:
            # Add timestamp
            user_data = user.copy()
            user_data['created_at'] = datetime.datetime.now().isoformat()

            # Store user
            users_table.put_item(Item=user_data)
            logger.info(f"Stored user: {user['handle']}")

        return True
    except Exception as e:
        logger.error(f"Error storing users: {e}")
        return False


# Function to generate a synthetic post
def generate_synthetic_post(date, disaster_type=None):
    """Generate a synthetic disaster-related post for a specific date"""
    # Randomly select a disaster type if none provided
    if not disaster_type:
        disaster_type = random.choice(DISASTER_TYPES)

    # Get location appropriate for this disaster type
    location = random.choice(LOCATIONS.get(disaster_type, ["Unknown Location"]))

    # Select a random user
    user = random.choice(USERS)

    # Generate post text using template
    templates = DISASTER_TEMPLATES.get(disaster_type, ["Disaster reported in {location}. #Disaster"])
    text_template = random.choice(templates)
    text = text_template.format(location=location)

    # Clean version of text
    clean_text = re.sub(r'#\w+', '', text).strip()

    # Add some randomness to the time
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    # Create datetime object with the random time
    created_at = datetime.datetime(date.year, date.month, date.day, hour, minute, second)

    # Add a random offset (0-3 minutes) to indexed_at
    indexed_at = created_at + datetime.timedelta(minutes=random.randint(0, 3))

    # Generate confidence score based on disaster type
    # Unknown has lower confidence, known disaster types have higher confidence
    if disaster_type == "unknown":
        # Even for unknown, keep confidence high for display purposes
        confidence_score = random.uniform(0.95, 0.96)
    else:
        # Always generate high confidence scores (0.95-0.99)
        confidence_score = random.uniform(0.95, 0.99)

    # Small chance of having media
    has_media = random.random() < 0.4  # 40% chance of having media
    media_urls = []
    if has_media:
        num_media = random.randint(1, 3)
        for i in range(num_media):
            # Generate a plausible media URL
            media_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            media_urls.append(f"https://cdn.bsky.app/img/feed_fullsize/{disaster_type}_{media_id}.jpg")

    # Generate a unique post ID for ATProto format
    post_id = f"at://did:plc:{uuid.uuid4().hex}/app.bsky.feed.post/{uuid.uuid4().hex[:10]}"

    # Create the post data structure matching expected schema exactly
    post_data = {
        'post_id': post_id,
        'indexed_at': indexed_at.isoformat(),
        'user_id': user['user_id'],
        'handle': user['handle'],
        'display_name': user['display_name'],
        'avatar_url': user['avatar_url'],
        'original_text': text,
        'clean_text': clean_text,
        'created_at': created_at.isoformat(),
        'location_name': location,
        'disaster_type': disaster_type,
        'confidence_score': Decimal(str(confidence_score)),
        'is_disaster': True,
        'is_disaster_str': 'true',
        'media_urls': media_urls if media_urls else None,  # Use None if empty for consistency
        'has_media': has_media,
        'language': 'en'
    }

    return post_data


# Store post in DynamoDB
def store_post(dynamodb, post_data):
    """Store post data in DynamoDB"""
    try:
        posts_table = dynamodb.Table(POSTS_TABLE)
        posts_table.put_item(Item=post_data)
        logger.info(f"Stored post: {post_data['post_id'][:15]}... disaster type: {post_data['disaster_type']}")
        return True
    except Exception as e:
        logger.error(f"Error storing post: {e}")
        return False


# Generate monthly distribution of disaster types based on season
def get_monthly_disaster_distribution(month):
    """Return weighted distribution of disaster types based on month/season"""
    # Base weights
    base_weights = {
        "avalanche": 5, "blizzard": 5, "bush_fire": 5, "cyclone": 5,
        "dust_storm": 5, "earthquake": 5, "flood": 5, "forest_fire": 5,
        "haze": 5, "hurricane": 5, "landslide": 5, "meteor": 2,
        "storm": 10, "tornado": 5, "tsunami": 3, "typhoon": 5,
        "volcano": 3, "wild_fire": 5, "unknown": 3
    }

    # Seasonal adjustments
    # Winter: Dec (12), Jan (1), Feb (2)
    if month in [12, 1, 2]:
        seasonal_weights = {
            "avalanche": 15, "blizzard": 15, "storm": 12,
            "bush_fire": 1, "forest_fire": 1, "wild_fire": 1,
            "hurricane": 1, "tornado": 2, "typhoon": 1,
            "haze": 3, "dust_storm": 2
        }
    # Spring: Mar (3), Apr (4), May (5)
    elif month in [3, 4, 5]:
        seasonal_weights = {
            "flood": 15, "tornado": 15, "storm": 12, "landslide": 10,
            "avalanche": 3, "blizzard": 3,
            "forest_fire": 3, "bush_fire": 3, "wild_fire": 3,
            "dust_storm": 8
        }
    # Summer: Jun (6), Jul (7), Aug (8)
    elif month in [6, 7, 8]:
        seasonal_weights = {
            "wild_fire": 15, "forest_fire": 15, "bush_fire": 12,
            "hurricane": 10, "typhoon": 10, "storm": 8, "tornado": 8,
            "dust_storm": 10, "haze": 10, "flood": 8,
            "avalanche": 1, "blizzard": 1
        }
    # Fall: Sep (9), Oct (10), Nov (11)
    else:
        seasonal_weights = {
            "hurricane": 15, "typhoon": 15, "storm": 10,
            "flood": 8, "landslide": 8,
            "forest_fire": 5, "wild_fire": 5,
            "blizzard": 3, "avalanche": 1,
            "dust_storm": 5, "haze": 5
        }

    # Apply seasonal adjustments to base weights
    adjusted_weights = base_weights.copy()
    for disaster_type, weight in seasonal_weights.items():
        adjusted_weights[disaster_type] = weight

    return adjusted_weights


# Generate posts for a specific date
def generate_posts_for_date(dynamodb, date, min_posts=50, max_posts=100):
    """Generate synthetic posts for a specific date"""
    # Determine number of posts to generate
    num_posts = random.randint(min_posts, max_posts)
    logger.info(f"Generating {num_posts} posts for {date.strftime('%Y-%m-%d')}")

    # Get monthly distribution
    month = date.month
    weights_dict = get_monthly_disaster_distribution(month)

    # Convert to lists for random.choices
    disaster_types = list(weights_dict.keys())
    weights = list(weights_dict.values())

    # Generate disaster types with appropriate seasonal distribution
    selected_disaster_types = random.choices(
        disaster_types,
        weights=weights,
        k=num_posts
    )

    # Generate and store posts
    posts_created = 0
    for disaster_type in selected_disaster_types:
        # Generate post data
        post_data = generate_synthetic_post(date, disaster_type)

        # Store post
        if store_post(dynamodb, post_data):
            posts_created += 1

    logger.info(f"Successfully created {posts_created} posts for {date.strftime('%Y-%m-%d')}")
    return posts_created


# Main function to generate data for a date range
def generate_data_for_date_range(start_date, end_date, dynamodb, min_posts=10, max_posts=50):
    """Generate posts for each day in a date range"""
    # Store users first
    logger.info("Storing user data...")
    store_users(dynamodb)

    # Calculate date range
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    day_count = 0
    total_posts = 0

    # Process each day
    while current_date <= end_date:
        day_count += 1
        logger.info(f"Processing day {day_count} of {total_days}: {current_date.strftime('%Y-%m-%d')}")

        # Generate posts for this day
        posts_created = generate_posts_for_date(dynamodb, current_date, min_posts, max_posts)
        total_posts += posts_created

        # Move to next day
        current_date += datetime.timedelta(days=1)

        # Calculate progress
        progress = (day_count / total_days) * 100
        logger.info(f"Progress: {progress:.1f}% - {total_posts} total posts created")

    logger.info(f"Data generation complete. Created {total_posts} posts across {day_count} days.")
    return total_posts


# Main function
def main():
    """Main entry point for the script"""
    try:
        # Define date range (April 1, 2024 to February 12, 2025)
        start_date = datetime.datetime(2024, 4, 1)
        end_date = datetime.datetime(2025, 2, 12)

        # Check for command line arguments for custom date range
        import sys
        if len(sys.argv) >= 3:
            try:
                # Format expected: python populate_disaster_data.py YYYY-MM-DD YYYY-MM-DD
                start_date = datetime.datetime.fromisoformat(sys.argv[1])
                end_date = datetime.datetime.fromisoformat(sys.argv[2])
                logger.info(
                    f"Using command line date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            except ValueError:
                logger.error("Invalid date format in command line arguments. Using default date range.")

        # Initialize DynamoDB
        dynamodb = init_dynamodb()

        # Generate data for the date range
        logger.info(
            f"Starting data generation from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        total_posts = generate_data_for_date_range(start_date, end_date, dynamodb)

        logger.info(f"Data generation completed successfully. {total_posts} posts created.")

    except KeyboardInterrupt:
        logger.info("Data generation interrupted by user")
    except Exception as e:
        logger.error(f"Error in data generation: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()