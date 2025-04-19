# api.py with improved DynamoDB connection handling
from flask import Flask, jsonify, request
from flask_cors import CORS
import boto3
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
import logging
from flask_socketio import SocketIO, emit
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

# Initialize SocketIO with CORS support
socketio = SocketIO(app, cors_allowed_origins="*")

# Load environment variables
load_dotenv('.env')

# DynamoDB table names
POSTS_TABLE = 'DisasterFeed_Posts'
USERS_TABLE = 'DisasterFeed_Users'
WEATHER_TABLE = 'DisasterFeed_WeatherData'

connected_clients = {}

# Singleton DynamoDB client
_dynamodb_instance = None
_last_initialization_time = 0
_initialization_lock = False


# Get DynamoDB client with connection reuse
def get_dynamodb():
    global _dynamodb_instance, _last_initialization_time, _initialization_lock

    # If already initializing, wait a bit and return existing instance
    if _initialization_lock:
        logger.info("Another thread is initializing DynamoDB, waiting...")
        time.sleep(0.1)
        return _dynamodb_instance

    # If we have an instance and it's recent (less than 15 minutes old), reuse it
    current_time = time.time()
    if _dynamodb_instance and (current_time - _last_initialization_time < 900):  # 15 minutes
        return _dynamodb_instance

    try:
        _initialization_lock = True

        region = os.getenv('AWS_REGION', 'us-east-1')
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

        if not aws_access_key_id or not aws_secret_access_key:
            logger.error("AWS credentials not found in environment variables")
            raise ValueError("AWS credentials missing. Check your environment variables.")

        logger.info(f"Initializing DynamoDB in region {region}")
        _dynamodb_instance = boto3.resource('dynamodb',
                                            region_name=region,
                                            aws_access_key_id=aws_access_key_id,
                                            aws_secret_access_key=aws_secret_access_key)

        # Update last initialization time
        _last_initialization_time = current_time

        return _dynamodb_instance
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB: {e}")
        raise
    finally:
        _initialization_lock = False


# Simple response cache
response_cache = {}
CACHE_EXPIRATION = 30  # seconds


def get_cached_response(cache_key):
    """Get a cached response if valid"""
    if cache_key in response_cache:
        entry = response_cache[cache_key]
        # Check if cache entry is still valid
        if time.time() - entry['timestamp'] < CACHE_EXPIRATION:
            logger.info(f"Using cached response for: {cache_key}")
            return entry['data']
    return None


def set_cached_response(cache_key, data):
    """Cache a response"""
    response_cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }


# Helper function to convert Decimal to float for JSON serialization
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    connected_clients[request.sid] = {'disaster_type': 'all'}


@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")
    if request.sid in connected_clients:
        del connected_clients[request.sid]


@socketio.on('subscribe')
def handle_subscribe(data):
    disaster_type = data.get('disasterType', 'all')
    logger.info(f"Client {request.sid} subscribed to disaster type: {disaster_type}")
    connected_clients[request.sid] = {'disaster_type': disaster_type}


# Endpoint to broadcast a new post
@app.route('/api/notify-new-post', methods=['POST'])
def notify_new_post():
    try:
        post_data = request.json

        if not post_data:
            return jsonify({"error": "Invalid post data"}), 400

        # Handle both singular 'post' and plural 'posts' formats
        if 'post' in post_data:
            # Single post format
            broadcast_post(post_data['post'])
            logger.info(f"Broadcasted single post to clients")
        elif 'posts' in post_data:
            # Multiple posts format
            posts = post_data['posts']
            for post in posts:
                broadcast_post(post)
            logger.info(f"Broadcasted {len(posts)} posts to clients")
        else:
            return jsonify({"error": "Missing 'post' or 'posts' field"}), 400

        return jsonify({"status": "success", "message": "Post(s) broadcasted to clients"}), 200
    except Exception as e:
        logger.error(f"Error in notify_new_post: {e}")
        return jsonify({"error": str(e)}), 500


# Function to broadcast a post to connected clients
def broadcast_post(post):
    post_disaster_type = post.get('disaster_type', 'unknown')

    logger.info(f"Broadcasting post of type {post_disaster_type} to {len(connected_clients)} clients")

    # Format post for client (if needed)
    formatted_post = {
        "post_id": post.get('post_id'),
        "handle": post.get('handle'),
        "display_name": post.get('display_name', ''),
        "text": post.get('original_text'),
        "timestamp": post.get('created_at'),
        "avatar_url": post.get('avatar_url'),
        "disaster_type": post_disaster_type,
        "confidence_score": post.get('confidence_score', 0),
    }

    # Send to all relevant clients
    for sid, subscription in connected_clients.items():
        client_disaster_type = subscription.get('disaster_type')

        # Check if client is subscribed to this post's disaster type
        if client_disaster_type == 'all' or client_disaster_type == post_disaster_type:
            socketio.emit('new_post', {"type": "new_post", "post": formatted_post}, room=sid)


@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        # Get query parameters for filtering
        disaster_type = request.args.get('type', 'all')
        limit = int(request.args.get('limit', 50))
        next_token = request.args.get('next_token')  # For pagination
        language = request.args.get('language', 'en')  # Default to English

        # Generate cache key including language
        cache_key = f"posts_{disaster_type}_{limit}_{next_token}_{language}"

        # Check cache first
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return cached_response

        logger.info(f"Getting posts with type={disaster_type}, limit={limit}, language={language}")

        dynamodb = get_dynamodb()
        posts_table = dynamodb.Table(POSTS_TABLE)

        # Define category mappings for filtering
        disaster_categories = {
            "fire": ["wild_fire", "bush_fire", "forest_fire"],
            "storm": ["storm", "blizzard", "cyclone", "dust_storm", "hurricane", "tornado", "typhoon"],
            "earthquake": ["earthquake"],
            "tsunami": ["tsunami"],
            "volcano": ["volcano"],
            "flood": ["flood"],
            "landslide": ["landslide", "avalanche"],
            "other": ["haze", "meteor", "unknown"]
        }

        # Function to process items to posts with filtering
        def process_items(items, already_applied_disaster_filter=False):
            processed_posts = []
            for item in items:
                try:
                    # Skip items without text
                    if 'original_text' not in item or not item['original_text']:
                        continue

                    text = item['original_text']

                    # Skip very short texts
                    if len(text.strip()) < 5:
                        continue

                    # Check stored language field
                    if language != 'all':
                        stored_lang = item.get('language', '')
                        if stored_lang != language:
                            continue

                    # Apply disaster type filtering if not already applied at the DB level
                    # IMPORTANT: For 'all' category, we should NOT apply additional filtering
                    # since 'all' means all disaster posts, and we've already filtered by is_disaster_str
                    if not already_applied_disaster_filter and disaster_type != 'all':
                        item_disaster_type = item.get('disaster_type', '').lower()

                        # Check if the item's disaster type matches any in the selected category
                        if disaster_type in disaster_categories:
                            subcategories = disaster_categories[disaster_type]
                            match_found = False
                            normalized_item_type = item_disaster_type.replace('_', ' ')

                            for subcategory in subcategories:
                                normalized_subcategory = subcategory.replace('_', ' ')
                                if normalized_item_type == normalized_subcategory or normalized_subcategory in normalized_item_type:
                                    match_found = True
                                    break

                            if not match_found:
                                continue
                        # For direct matching if not a super-category
                        elif not (disaster_type.lower() in item_disaster_type or
                                  item_disaster_type in disaster_type.lower() or
                                  disaster_type.lower().replace('_', ' ') in item_disaster_type.replace('_', ' ') or
                                  item_disaster_type.replace('_', ' ') in disaster_type.lower().replace('_', ' ')):
                            continue

                    # If we get here, the post matches our criteria - transform and add it
                    post = {
                        'post_id': item.get('post_id'),
                        'original_text': item.get('original_text'),
                        'created_at': item.get('created_at'),
                        'disaster_type': item.get('disaster_type'),
                        'confidence_score': item.get('confidence_score'),
                        'username': item.get('handle'),  # Using handle as username
                        'handle': item.get('handle'),  # Also include handle explicitly
                        'user_id': item.get('user_id'),
                        'display_name': item.get('display_name'),
                        'avatar_url': item.get('avatar_url'),
                        'location_name': item.get('location_name', ''),
                        'media': item.get('media_urls', [])
                    }
                    processed_posts.append(post)

                except Exception as e:
                    logger.error(f"Error processing post {item.get('post_id')}: {str(e)}")
                    continue

            return processed_posts

        posts = []
        last_evaluated_key = None

        # Check if we can use a dedicated index for a specific type
        use_dedicated_index = False
        if disaster_type != 'all':
            # Add other types here if you create dedicated indexes for them
            if disaster_type == 'tsunami':
                use_dedicated_index = True
                index_name = 'DisasterTypeIndex'
                key_condition = Key('disaster_type').eq(disaster_type)
        if use_dedicated_index:
            logger.info(f"Using dedicated index {index_name} for type: {disaster_type}")
            params = {
                'IndexName': index_name,
                'KeyConditionExpression': key_condition,
                'Limit': limit,
                'ScanIndexForward': False
            }

            if next_token:
                try:
                    # Decode the complex key for GSI correctly
                    token_data = json.loads(next_token)
                    # GSI Key includes primary key of main table as well
                    params['ExclusiveStartKey'] = {
                        'disaster_type': token_data['disaster_type'],  # GSI Hash Key
                        'indexed_at': token_data['indexed_at'],  # GSI Sort Key
                        'post_id': token_data['post_id']  # Main Table Hash Key
                    }
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Invalid next_token format for GSI: {next_token} - Error: {e}")
                    return jsonify({"error": "Invalid pagination token"}), 400


            response = posts_table.query(**params)
            posts = process_items(response.get('Items', []), already_applied_disaster_filter=True)

            if 'LastEvaluatedKey' in response:
                last_evaluated_key = response['LastEvaluatedKey']
        else:
            logger.info(f"Using IsDisasterIndex and filtering for type: {disaster_type}")
            params = {
                'IndexName': 'IsDisasterIndex',
                'KeyConditionExpression': Key('is_disaster_str').eq('true'),
                'Limit': limit * 2,  # Get more to account for filtering
                'ScanIndexForward': False
            }

            # Add pagination token if provided
            if next_token:
                try:
                    # Decode the complex key for IsDisasterIndex
                    token_data = json.loads(next_token)
                    params['ExclusiveStartKey'] = {
                        'is_disaster_str': token_data['is_disaster_str'],  # Index Hash Key
                        'indexed_at': token_data['indexed_at'],  # Index Sort Key
                        'post_id': token_data['post_id']  # Main Table Hash Key
                    }
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Invalid next_token format for IsDisasterIndex: {next_token} - Error: {e}")
                    return jsonify({"error": "Invalid pagination token"}), 400

            # Execute the query - this will get ALL disaster posts
            response = posts_table.query(**params)

            # Process items with filtering based on disaster_type
            # For 'all', this will just apply basic checks
            # For specific types, this will apply our flexible matching logic
            posts = process_items(response.get('Items', []), already_applied_disaster_filter=False)

            # Save the last evaluated key for pagination
            if 'LastEvaluatedKey' in response:
                last_evaluated_key = response['LastEvaluatedKey']

            # If we need more items, continue fetching with pagination
            while len(posts) < limit and 'LastEvaluatedKey' in response:
                params['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = posts_table.query(**params)

                new_posts = process_items(response.get('Items', []), already_applied_disaster_filter=False)
                posts.extend(new_posts)

                if 'LastEvaluatedKey' in response:
                    last_evaluated_key = response['LastEvaluatedKey']
                else:
                    last_evaluated_key = None  # Explicitly clear if no more keys
                    break  # Exit loop if no more keys

        # Ensure we're only returning up to the requested limit
        posts = posts[:limit]

        # Build the response with pagination support
        result = {'posts': posts}

        # Add pagination token if we have more results
        if last_evaluated_key:
            result['next_token'] = json.dumps(last_evaluated_key)

        # Create the API response
        api_response = app.response_class(
            response=json.dumps(result, cls=DecimalEncoder),
            status=200,
            mimetype='application/json'
        )

        # Cache the response
        set_cached_response(cache_key, api_response)

        return api_response

    except Exception as e:
        logger.error(f"Error in get_posts: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/disaster-summary', methods=['GET'])
def get_disaster_summary():
    try:
        # Check cache first
        cache_key = "disaster_summary"
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return cached_response

        logger.info("Generating disaster summary")

        dynamodb = get_dynamodb()
        posts_table = dynamodb.Table(POSTS_TABLE)

        # We'll use the IsDisasterIndex to get disaster posts efficiently
        response = posts_table.query(
            IndexName='IsDisasterIndex',
            KeyConditionExpression=Key('is_disaster_str').eq('true')
        )

        all_disaster_posts = response['Items']

        # Continue scanning if we have more items (pagination)
        while 'LastEvaluatedKey' in response:
            response = posts_table.query(
                IndexName='IsDisasterIndex',
                KeyConditionExpression=Key('is_disaster_str').eq('true'),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            all_disaster_posts.extend(response['Items'])

        # Group posts by disaster_type
        disaster_summary = {}

        for post in all_disaster_posts:
            disaster_type = post.get('disaster_type', 'unknown')
            created_at = post.get('created_at', '')
            confidence = Decimal(post.get('confidence_score', 0))

            if disaster_type not in disaster_summary:
                disaster_summary[disaster_type] = {
                    'disaster_type': disaster_type,
                    'count': 0,
                    'first_occurrence': created_at,
                    'latest_occurrence': created_at,
                    'confidence_sum': Decimal('0'),
                    'avg_confidence': Decimal('0')
                }

            summary = disaster_summary[disaster_type]
            summary['count'] += 1
            summary['confidence_sum'] += confidence

            # Update first_occurrence if this post is older
            if created_at < summary['first_occurrence']:
                summary['first_occurrence'] = created_at

            # Update latest_occurrence if this post is newer
            if created_at > summary['latest_occurrence']:
                summary['latest_occurrence'] = created_at

        # Calculate average confidence for each disaster type
        for disaster_type, summary in disaster_summary.items():
            if summary['count'] > 0:
                summary['avg_confidence'] = summary['confidence_sum'] / summary['count']
            del summary['confidence_sum']  # Remove the sum as it's not needed in the result

        # Convert the dictionary to a list of summaries, sorted by count
        result = list(disaster_summary.values())
        result.sort(key=lambda x: x['count'], reverse=True)

        logger.info(f"Generated summary with {len(result)} disaster types")

        # Create the API response
        api_response = app.response_class(
            response=json.dumps(result, cls=DecimalEncoder),
            status=200,
            mimetype='application/json'
        )

        # Cache the response
        set_cached_response(cache_key, api_response)

        return api_response

    except Exception as e:
        logger.error(f"Error in get_disaster_summary: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/disaster-types', methods=['GET'])
def get_disaster_types():
    try:
        # Check cache first
        cache_key = "disaster_types"
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return cached_response

        logger.info("Fetching unique disaster types")

        dynamodb = get_dynamodb()
        posts_table = dynamodb.Table(POSTS_TABLE)

        # Use the IsDisasterIndex to get disaster posts efficiently
        response = posts_table.query(
            IndexName='IsDisasterIndex',
            KeyConditionExpression=Key('is_disaster_str').eq('true'),
            ProjectionExpression='disaster_type'
        )

        disaster_types = set()
        for item in response['Items']:
            if 'disaster_type' in item:
                disaster_types.add(item['disaster_type'])

        # Continue querying if we have more items (pagination)
        while 'LastEvaluatedKey' in response:
            response = posts_table.query(
                IndexName='IsDisasterIndex',
                KeyConditionExpression=Key('is_disaster_str').eq('true'),
                ProjectionExpression='disaster_type',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            for item in response['Items']:
                if 'disaster_type' in item:
                    disaster_types.add(item['disaster_type'])

        # Convert set to sorted list
        result = sorted(list(disaster_types))

        logger.info(f"Found {len(result)} unique disaster types")

        api_response = jsonify(result)

        # Cache the response
        set_cached_response(cache_key, api_response)

        return api_response

    except Exception as e:
        logger.error(f"Error in get_disaster_types: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/chart/disaster-distribution', methods=['GET'])
def get_disaster_distribution():
    """Get count and percentage of posts by disaster type"""
    try:
        # Check cache first
        cache_key = "disaster_distribution"
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return cached_response

        dynamodb = get_dynamodb()
        posts_table = dynamodb.Table(POSTS_TABLE)

        # Get all disaster posts using IsDisasterIndex
        response = posts_table.query(
            IndexName='IsDisasterIndex',
            KeyConditionExpression=Key('is_disaster_str').eq('true')
        )

        all_items = response['Items']
        while 'LastEvaluatedKey' in response:
            response = posts_table.query(
                IndexName='IsDisasterIndex',
                KeyConditionExpression=Key('is_disaster_str').eq('true'),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            all_items.extend(response['Items'])

        # Count by disaster type
        type_counts = {}
        total_count = 0

        for item in all_items:
            disaster_type = item.get('disaster_type', 'unknown')
            if disaster_type not in type_counts:
                type_counts[disaster_type] = 0
            type_counts[disaster_type] += 1
            total_count += 1

        # Calculate percentages
        result = {
            "data": [],
            "total_count": total_count
        }

        for disaster_type, count in type_counts.items():
            percentage = (count / total_count * 100) if total_count > 0 else 0
            result["data"].append({
                "type": disaster_type,
                "count": count,
                "percentage": round(float(percentage), 1)
            })

        # Sort by count descending
        result["data"].sort(key=lambda x: x["count"], reverse=True)

        api_response = app.response_class(
            response=json.dumps(result, cls=DecimalEncoder),
            status=200,
            mimetype='application/json'
        )

        # Cache the response
        set_cached_response(cache_key, api_response)

        return api_response

    except Exception as e:
        logger.error(f"Error in get_disaster_distribution: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/chart/disaster-timeline', methods=['GET'])
def get_disaster_timeline():
    """Get time-series data for disaster posts"""
    try:
        # Get query parameters
        interval = request.args.get('interval', 'daily')  # daily, weekly, monthly
        days = int(request.args.get('days', '30'))  # last 30 days by default
        disaster_type = request.args.get('type', None)  # optional filter

        # Generate cache key
        cache_key = f"disaster_timeline_{interval}_{days}_{disaster_type}"
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return cached_response

        dynamodb = get_dynamodb()
        posts_table = dynamodb.Table(POSTS_TABLE)

        # Calculate start date - FIXED datetime usage
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_date_str = start_date.isoformat()

        # Decide which index and query to use
        if disaster_type and disaster_type != 'all':
            # Use DisasterTypeIndex
            response = posts_table.query(
                IndexName='DisasterTypeIndex',
                KeyConditionExpression=Key('disaster_type').eq(disaster_type) &
                                       Key('indexed_at').gte(start_date_str)
            )
        else:
            # Use IsDisasterIndex
            response = posts_table.query(
                IndexName='IsDisasterIndex',
                KeyConditionExpression=Key('is_disaster_str').eq('true') &
                                       Key('indexed_at').gte(start_date_str)
            )

        all_items = response['Items']
        while 'LastEvaluatedKey' in response:
            if disaster_type and disaster_type != 'all':
                response = posts_table.query(
                    IndexName='DisasterTypeIndex',
                    KeyConditionExpression=Key('disaster_type').eq(disaster_type) &
                                           Key('indexed_at').gte(start_date_str),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
            else:
                response = posts_table.query(
                    IndexName='IsDisasterIndex',
                    KeyConditionExpression=Key('is_disaster_str').eq('true') &
                                           Key('indexed_at').gte(start_date_str),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
            all_items.extend(response['Items'])

        # Process data by interval and disaster type
        timeline_data = {}
        date_labels = []

        # Group data by date and disaster type
        for item in all_items:
            date_str = item.get('created_at', '')
            if not date_str:
                continue

            try:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

                # Format date based on interval
                if interval == 'daily':
                    interval_key = date.strftime('%Y-%m-%d')
                elif interval == 'weekly':
                    # Get start of week (Monday)
                    start_of_week = date - timedelta(days=date.weekday())
                    interval_key = start_of_week.strftime('%Y-%m-%d')
                elif interval == 'monthly':
                    interval_key = date.strftime('%Y-%m')

                # Add to date labels if new
                if interval_key not in date_labels:
                    date_labels.append(interval_key)

                # Count by disaster type
                disaster_type = item.get('disaster_type', 'unknown')

                if disaster_type not in timeline_data:
                    timeline_data[disaster_type] = {}

                if interval_key not in timeline_data[disaster_type]:
                    timeline_data[disaster_type][interval_key] = 0

                timeline_data[disaster_type][interval_key] += 1

            except (ValueError, TypeError):
                continue

        # Sort date labels
        date_labels.sort()

        # Format result
        datasets = []
        for disaster_type, dates in timeline_data.items():
            data_points = []
            for label in date_labels:
                data_points.append(dates.get(label, 0))

            datasets.append({
                "label": disaster_type,
                "data": data_points
            })

        result = {
            "interval": interval,
            "labels": date_labels,
            "datasets": datasets
        }

        api_response = jsonify(result)

        # Cache the response
        set_cached_response(cache_key, api_response)

        return api_response

    except Exception as e:
        logger.error(f"Error in get_disaster_timeline: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/chart/post-volume-metrics', methods=['GET'])
def get_post_volume_metrics():
    """Get overall post volume metrics"""
    try:
        # Check cache first
        cache_key = "post_volume_metrics"
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return cached_response

        dynamodb = get_dynamodb()
        posts_table = dynamodb.Table(POSTS_TABLE)

        # Get all posts
        # Note: This could be inefficient for large tables
        # Consider implementing a counter table for production
        scan_response = posts_table.scan(
            Select='COUNT'
        )
        total_processed = scan_response.get('Count', 0)

        # Get disaster posts count
        disaster_response = posts_table.query(
            IndexName='IsDisasterIndex',
            KeyConditionExpression=Key('is_disaster_str').eq('true'),
            Select='COUNT'
        )
        disaster_posts = disaster_response.get('Count', 0)

        # Calculate percentage
        disaster_percentage = (disaster_posts / total_processed * 100) if total_processed > 0 else 0

        # Get last 24 hours metrics - FIXED datetime usage
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()

        # This is simplified - for a complete implementation, you'd need to handle pagination
        recent_response = posts_table.scan(
            FilterExpression=Attr('indexed_at').gte(yesterday),
            Select='COUNT'
        )
        last_24h_total = recent_response.get('Count', 0)

        # Recent disaster posts
        recent_disaster_response = posts_table.query(
            IndexName='IsDisasterIndex',
            KeyConditionExpression=Key('is_disaster_str').eq('true') & Key('indexed_at').gte(yesterday),
            Select='COUNT'
        )
        last_24h_disaster = recent_disaster_response.get('Count', 0)

        # Calculate recent percentage
        last_24h_percentage = (last_24h_disaster / last_24h_total * 100) if last_24h_total > 0 else 0

        result = {
            "total_processed": total_processed,
            "disaster_posts": disaster_posts,
            "disaster_percentage": round(float(disaster_percentage), 1),
            "last_24h": {
                "total_processed": last_24h_total,
                "disaster_posts": last_24h_disaster,
                "disaster_percentage": round(float(last_24h_percentage), 1)
            }
        }

        api_response = app.response_class(
            response=json.dumps(result, cls=DecimalEncoder),
            status=200,
            mimetype='application/json'
        )

        # Cache the response
        set_cached_response(cache_key, api_response)

        return api_response

    except Exception as e:
        logger.error(f"Error in get_post_volume_metrics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/chart/disaster-distribution-months', methods=['GET'])
def get_disaster_distribution_months():
    """Get count and percentage of posts by disaster type for a specific month range"""
    try:
        # Get the months parameter (defaults to 6 months)
        months_back = request.args.get('months', '6')
        try:
            months_back = int(months_back)
        except ValueError:
            months_back = 6

        # Generate cache key including the months parameter
        cache_key = f"disaster_distribution_months_{months_back}"
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return cached_response

        dynamodb = get_dynamodb()
        posts_table = dynamodb.Table(POSTS_TABLE)

        # Calculate start date for filtering
        now = datetime.now()
        start_month = now.month - months_back
        start_year = now.year
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        start_date = datetime(start_year, start_month, 1)
        start_date_str = start_date.isoformat()
        logger.info(f"Filtering disasters for the last {months_back} months (from {start_date_str})")
        filter_expression = Attr('created_at').gte(start_date_str)
        logger.info(f"Filtering disasters using indexed_at >= {start_date_str}")

        # Query parameters
        query_params = {
            'IndexName': 'IsDisasterIndex',
            'KeyConditionExpression': Key('is_disaster_str').eq('true') & Key('indexed_at').gte(start_date_str)
        }

        # Get all disaster posts using IsDisasterIndex with time filter
        response = posts_table.query(**query_params)

        all_items = response['Items']
        while 'LastEvaluatedKey' in response:
            query_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = posts_table.query(**query_params)
            all_items.extend(response['Items'])

        logger.info(f"Found {len(all_items)} disaster posts in the last {months_back} months")

        # Count by disaster type
        type_counts = {}
        total_count = 0

        for item in all_items:
            disaster_type = item.get('disaster_type', 'unknown')
            if disaster_type not in type_counts:
                type_counts[disaster_type] = 0
            type_counts[disaster_type] += 1
            total_count += 1

        # Calculate percentages
        result = {
            "data": [],
            "total_count": total_count,
            "time_period": f"{months_back} months"
        }

        for disaster_type, count in type_counts.items():
            percentage = (count / total_count * 100) if total_count > 0 else 0
            result["data"].append({
                "type": disaster_type,
                "count": count,
                "percentage": round(float(percentage), 1)
            })

        # Sort by count descending
        result["data"].sort(key=lambda x: x["count"], reverse=True)

        api_response = app.response_class(
            response=json.dumps(result, cls=DecimalEncoder),
            status=200,
            mimetype='application/json'
        )

        # Cache the response
        set_cached_response(cache_key, api_response)

        return api_response

    except Exception as e:
        logger.error(f"Error in get_disaster_distribution_months: {e}")
        return jsonify({"error": str(e)}), 500


# Endpoint to clear cache (for debugging/testing)
@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
    try:
        global response_cache
        response_cache = {}
        return jsonify({"status": "success", "message": "Cache cleared"}), 200
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    socketio.run(app, debug=True, port=8000)