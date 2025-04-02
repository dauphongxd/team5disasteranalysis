# api.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import boto3
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta  # Added timedelta import
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

# Load environment variables
load_dotenv('.env')

# DynamoDB table names
POSTS_TABLE = 'DisasterFeed_Posts'
USERS_TABLE = 'DisasterFeed_Users'
WEATHER_TABLE = 'DisasterFeed_WeatherData'


# Initialize DynamoDB client
def get_dynamodb():
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


# Helper function to convert Decimal to float for JSON serialization
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        # Get query parameters for filtering
        disaster_type = request.args.get('type', 'all')
        limit = int(request.args.get('limit', 50))
        next_token = request.args.get('next_token')  # For pagination

        logger.info(f"Getting posts with type={disaster_type}, limit={limit}")

        dynamodb = get_dynamodb()
        posts_table = dynamodb.Table(POSTS_TABLE)

        # Set up query parameters
        if disaster_type != 'all':
            # Use the GlobalSecondaryIndex for disaster_type
            params = {
                'IndexName': 'DisasterTypeIndex',
                'KeyConditionExpression': Key('disaster_type').eq(disaster_type),
                'Limit': limit,
                'ScanIndexForward': False  # Sort in descending order (newest first)
            }
            operation = posts_table.query
        else:
            # For 'all', we'll use the IsDisasterIndex with 'true' key
            params = {
                'IndexName': 'IsDisasterIndex',
                'KeyConditionExpression': Key('is_disaster_str').eq('true'),
                'Limit': limit,
                'ScanIndexForward': False  # Sort in descending order (newest first)
            }
            operation = posts_table.query

        # Add pagination token if provided
        if next_token:
            try:
                params['ExclusiveStartKey'] = json.loads(next_token)
            except json.JSONDecodeError:
                logger.error(f"Invalid next_token format: {next_token}")
                return jsonify({"error": "Invalid pagination token"}), 400

        # Execute the query or scan
        response = operation(**params)

        # Process posts
        posts = []
        for item in response.get('Items', []):
            # Transform DynamoDB item to match expected format
            post = {
                'post_id': item.get('post_id'),
                'original_text': item.get('original_text'),
                'created_at': item.get('created_at'),
                'disaster_type': item.get('disaster_type'),
                'confidence_score': item.get('confidence_score'),
                'username': item.get('handle'),  # Using handle as username
                'handle': item.get('handle'),  # Also include handle explicitly
                'user_id': item.get('user_id'),
                'display_name': item.get('display_name'),  # Add display_name
                'avatar_url': item.get('avatar_url'),  # Add avatar_url
                'location_name': item.get('location_name', ''),
                'media': item.get('media_urls', [])
            }
            posts.append(post)

        # Build the response with pagination support
        result = {'posts': posts}

        if 'LastEvaluatedKey' in response:
            result['next_token'] = json.dumps(response['LastEvaluatedKey'])

        return app.response_class(
            response=json.dumps(result, cls=DecimalEncoder),
            status=200,
            mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"Error in get_posts: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/disaster-summary', methods=['GET'])
def get_disaster_summary():
    try:
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

        return app.response_class(
            response=json.dumps(result, cls=DecimalEncoder),
            status=200,
            mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"Error in get_disaster_summary: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/disaster-types', methods=['GET'])
def get_disaster_types():
    try:
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

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in get_disaster_types: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/chart/disaster-distribution', methods=['GET'])
def get_disaster_distribution():
    """Get count and percentage of posts by disaster type"""
    try:
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

        return app.response_class(
            response=json.dumps(result, cls=DecimalEncoder),
            status=200,
            mimetype='application/json'
        )

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

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in get_disaster_timeline: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/chart/post-volume-metrics', methods=['GET'])
def get_post_volume_metrics():
    """Get overall post volume metrics"""
    try:
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

        return app.response_class(
            response=json.dumps(result, cls=DecimalEncoder),
            status=200,
            mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"Error in get_post_volume_metrics: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)