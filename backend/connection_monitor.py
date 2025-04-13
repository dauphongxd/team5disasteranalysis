#!/usr/bin/env python3
"""
Disaster Feed Post Monitor

This script monitors post collection activity and notification events
for the Disaster Feed system. It shows real-time statistics on post
collection, disaster types, and API notifications.
"""

import os
import sys
import time
import json
import boto3
import logging
import datetime
import argparse
import threading
from decimal import Decimal
from dotenv import load_dotenv
from tabulate import tabulate
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("monitor.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env')

# Define constants
POSTS_TABLE = 'DisasterFeed_Posts'
LAST_PROCESSED_FILE = "last_processed.json"
POSTS_JSON_FILE = "disaster_posts.json"
REFRESH_INTERVAL = 10  # Seconds between refreshes
MAX_DISPLAYED_POSTS = 10  # Number of recent posts to display


# DynamoDB JSON encoder for Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def init_dynamodb():
    """Initialize DynamoDB client"""
    try:
        region = os.getenv('AWS_REGION', 'us-east-1')
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

        if not aws_access_key_id or not aws_secret_access_key:
            logger.error("AWS credentials not found in environment variables")
            raise ValueError("AWS credentials missing. Check your environment variables.")

        return boto3.resource('dynamodb',
                              region_name=region,
                              aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key)
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB: {e}")
        raise


def clear_screen():
    """Clear the terminal screen based on OS"""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_time_ago(timestamp_str):
    """Format time difference between now and a timestamp string"""
    try:
        timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = now - timestamp

        # Format based on how long ago
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds >= 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return f"{delta.seconds}s ago"
    except Exception:
        return "Unknown"


def get_collection_stats(dynamodb, last_check_time=None):
    """Get statistics on post collection activity"""
    try:
        posts_table = dynamodb.Table(POSTS_TABLE)

        # Get total post count
        total_count = posts_table.scan(Select='COUNT')['Count']

        # Get recent posts if we want to display them
        recent_posts = []
        try:
            response = posts_table.scan(
                Limit=MAX_DISPLAYED_POSTS
            )
            recent_posts = response.get('Items', [])
            recent_posts.sort(key=lambda x: x.get('indexed_at', ''), reverse=True)
        except Exception as e:
            logger.error(f"Error retrieving recent posts: {e}")

        # Get counts by disaster type
        disaster_counts = {}
        try:
            disaster_types = [
                "earthquake", "flood", "hurricane", "tornado", "tsunami",
                "avalanche", "landslide", "volcano", "wildfire", "storm",
                "blizzard", "cyclone", "typhoon", "unknown"
            ]

            for disaster_type in disaster_types:
                try:
                    # Query DisasterTypeIndex for this type
                    count = posts_table.query(
                        IndexName='DisasterTypeIndex',
                        KeyConditionExpression='disaster_type = :dt',
                        ExpressionAttributeValues={
                            ':dt': disaster_type
                        },
                        Select='COUNT'
                    ).get('Count', 0)

                    if count > 0:
                        disaster_counts[disaster_type] = count
                except Exception:
                    # Skip if there's an error for this type
                    pass
        except Exception as e:
            logger.error(f"Error retrieving disaster type counts: {e}")

        # Get posts since last check (if provided)
        new_posts_count = 0
        if last_check_time:
            try:
                new_posts_count = posts_table.scan(
                    FilterExpression='indexed_at > :t',
                    ExpressionAttributeValues={
                        ':t': last_check_time.isoformat()
                    },
                    Select='COUNT'
                ).get('Count', 0)
            except Exception as e:
                logger.error(f"Error retrieving new posts count: {e}")

        return {
            'total_count': total_count,
            'disaster_counts': disaster_counts,
            'recent_posts': recent_posts,
            'new_posts_count': new_posts_count
        }

    except Exception as e:
        logger.error(f"Error retrieving collection stats: {e}")
        return {
            'total_count': 0,
            'disaster_counts': {},
            'recent_posts': [],
            'new_posts_count': 0
        }


def get_notification_info():
    """Get information about notification timings"""
    try:
        # Try to find the timestamp of the last notification from logs
        last_notification_time = None
        notification_pattern = "Successfully notified API about"

        try:
            with open("disaster_feed.log", "r", encoding="utf-8") as log_file:
                lines = log_file.readlines()

                # Search backwards for the last notification
                for line in reversed(lines):
                    if notification_pattern in line:
                        # Extract timestamp from log
                        timestamp_str = line.split(" - ")[0]
                        last_notification_time = datetime.datetime.strptime(
                            timestamp_str, "%Y-%m-%d %H:%M:%S,%f"
                        )
                        break
        except Exception as e:
            logger.error(f"Error reading log file for notifications: {e}")

        # Check if there's a buffer size we can determine
        buffer_size = None
        try:
            with open("disaster_feed.log", "r", encoding="utf-8") as log_file:
                lines = log_file.readlines()

                # Search backwards for buffer info
                for line in reversed(lines):
                    if "Added post" in line and "to notification buffer" in line:
                        # Try to extract buffer size
                        import re
                        match = re.search(r"current size: (\d+)", line)
                        if match:
                            buffer_size = int(match.group(1))
                            break
        except Exception:
            pass

        # Calculate time until next notification (if we know the last time)
        next_notification_time = None
        time_until_next = None

        if last_notification_time:
            # Assuming 15-minute intervals
            next_notification_time = last_notification_time + datetime.timedelta(minutes=15)
            now = datetime.datetime.now()

            if next_notification_time > now:
                time_until_next = next_notification_time - now
            else:
                # If we've passed the expected notification time
                # Calculate when the next one should be
                minutes_since = (now - last_notification_time).total_seconds() / 60
                intervals_passed = int(minutes_since / 15) + 1
                next_notification_time = last_notification_time + datetime.timedelta(minutes=15 * intervals_passed)
                time_until_next = next_notification_time - now

        return {
            'last_notification_time': last_notification_time,
            'next_notification_time': next_notification_time,
            'time_until_next': time_until_next,
            'buffer_size': buffer_size
        }

    except Exception as e:
        logger.error(f"Error retrieving notification info: {e}")
        return {
            'last_notification_time': None,
            'next_notification_time': None,
            'time_until_next': None,
            'buffer_size': None
        }


def get_keyword_timing_info():
    """Get information about keyword search timing"""
    try:
        # Try to read the last processed timestamps
        keywords_info = {}

        if os.path.exists(LAST_PROCESSED_FILE):
            try:
                with open(LAST_PROCESSED_FILE, 'r') as f:
                    last_processed = json.load(f)

                    # Format each timestamp
                    for keyword, timestamp_str in last_processed.items():
                        try:
                            timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            time_ago = format_time_ago(timestamp_str)
                            keywords_info[keyword] = {
                                'timestamp': timestamp,
                                'time_ago': time_ago
                            }
                        except Exception:
                            keywords_info[keyword] = {
                                'timestamp': None,
                                'time_ago': 'Invalid'
                            }
            except Exception as e:
                logger.error(f"Error reading last processed file: {e}")

        return keywords_info

    except Exception as e:
        logger.error(f"Error retrieving keyword timing info: {e}")
        return {}


def display_monitor_info(stats, notification_info, keyword_info, last_check_time):
    """Display monitoring information in a formatted way"""
    clear_screen()
    print("\n" + "=" * 80)
    print("DISASTER FEED MONITORING SYSTEM".center(80))
    print("=" * 80)

    # System Status
    now = datetime.datetime.now()
    print(f"\nCurrent Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    if last_check_time:
        time_since_refresh = (now - last_check_time).total_seconds()
        print(f"Last Refresh: {time_since_refresh:.1f} seconds ago")

    new_posts = stats['new_posts_count']
    if new_posts > 0:
        print(f"New Posts Since Last Check: {new_posts}")

    # Overall statistics
    print("\n" + "-" * 80)
    print("POST STATISTICS".center(80))
    print("-" * 80)
    print(f"Total Posts Collected: {stats['total_count']}")

    # Disaster Type Breakdown
    disaster_counts = stats['disaster_counts']
    if disaster_counts:
        print("\nDisaster Type Distribution:")
        disaster_table = []
        for disaster_type, count in sorted(disaster_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / stats['total_count']) * 100 if stats['total_count'] > 0 else 0
            disaster_table.append([disaster_type.capitalize(), count, f"{percentage:.1f}%"])

        print(tabulate(disaster_table, headers=["Type", "Count", "Percentage"], tablefmt="simple"))

    # Notification Information
    print("\n" + "-" * 80)
    print("NOTIFICATION STATUS".center(80))
    print("-" * 80)

    if notification_info['last_notification_time']:
        time_since = (now - notification_info['last_notification_time']).total_seconds()
        print(
            f"Last API Notification: {notification_info['last_notification_time'].strftime('%Y-%m-%d %H:%M:%S')} ({int(time_since // 60)} min {int(time_since % 60)} sec ago)")
    else:
        print("Last API Notification: Unknown")

    if notification_info['next_notification_time']:
        print(f"Next API Notification: {notification_info['next_notification_time'].strftime('%Y-%m-%d %H:%M:%S')}")

        if notification_info['time_until_next']:
            minutes = int(notification_info['time_until_next'].total_seconds() // 60)
            seconds = int(notification_info['time_until_next'].total_seconds() % 60)
            print(f"Time Until Next Notification: {minutes} min {seconds} sec")
    else:
        print("Next API Notification: Unknown")

    if notification_info['buffer_size'] is not None:
        print(f"Current Notification Buffer Size: {notification_info['buffer_size']} posts")

    # Keyword Information
    if keyword_info:
        print("\n" + "-" * 80)
        print("KEYWORD SEARCH STATUS".center(80))
        print("-" * 80)

        keyword_table = []
        for keyword, info in sorted(keyword_info.items()):
            keyword_table.append([keyword, info.get('time_ago', 'Unknown')])

        print(tabulate(keyword_table, headers=["Keyword", "Last Search"], tablefmt="simple"))

    # Recent Posts
    if stats['recent_posts']:
        print("\n" + "-" * 80)
        print("MOST RECENT POSTS".center(80))
        print("-" * 80)

        posts_table = []
        for post in stats['recent_posts'][:MAX_DISPLAYED_POSTS]:
            # Format the post information
            handle = post.get('handle', 'Unknown')
            text = post.get('original_text', '')
            if len(text) > 60:
                text = text[:57] + '...'

            disaster_type = post.get('disaster_type', 'unknown').capitalize()
            confidence = float(post.get('confidence_score', 0))

            indexed_at = post.get('indexed_at', '')
            time_ago = format_time_ago(indexed_at) if indexed_at else 'Unknown'

            posts_table.append([
                handle,
                text,
                disaster_type,
                f"{confidence:.2f}",
                time_ago
            ])

        print(tabulate(posts_table, headers=["Handle", "Text", "Type", "Confidence", "Time"], tablefmt="simple"))

    # Footer
    print("\n" + "=" * 80)
    print(f"Auto-refreshing every {REFRESH_INTERVAL} seconds. Press Ctrl+C to exit.")
    print("=" * 80)


def monitor_loop(dynamodb):
    """Main monitoring loop"""
    last_check_time = None

    try:
        while True:
            now = datetime.datetime.now()

            # Get post statistics
            stats = get_collection_stats(dynamodb, last_check_time)

            # Get notification information
            notification_info = get_notification_info()

            # Get keyword timing information
            keyword_info = get_keyword_timing_info()

            # Display all information
            display_monitor_info(stats, notification_info, keyword_info, last_check_time)

            # Update last check time
            last_check_time = now

            # Wait for next refresh
            time.sleep(REFRESH_INTERVAL)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    except Exception as e:
        logger.error(f"Error in monitoring loop: {e}")
        print(f"\nError: {e}")


def main():
    """Main entry point"""
    global REFRESH_INTERVAL

    parser = argparse.ArgumentParser(description='Monitor Disaster Feed post collection and notifications')
    parser.add_argument('--interval', type=int, default=REFRESH_INTERVAL,
                        help=f'Refresh interval in seconds (default: {REFRESH_INTERVAL})')
    args = parser.parse_args()

    REFRESH_INTERVAL = args.interval

    try:
        print("Initializing Disaster Feed Monitor...")
        dynamodb = init_dynamodb()
        monitor_loop(dynamodb)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())