# api.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import boto3
import os
from dotenv import load_dotenv
import json
from datetime import datetime
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
load_dotenv('disasterweb.env')

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
                'user_id': item.get('user_id'),
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)