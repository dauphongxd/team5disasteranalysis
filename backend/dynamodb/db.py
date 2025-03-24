import os
import datetime
import logging
import uuid
from decimal import Decimal
from typing import List, Dict, Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Initialize environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DisasterDatabase:
    """Class for handling DynamoDB operations for Disaster Feed application"""
    
    def __init__(self, aws_config):
        self._tables = {
            'users': os.getenv('USERS_TABLE', 'DisasterFeed_Users'),
            'posts': os.getenv('POSTS_TABLE', 'DisasterFeed_Posts'),
            'weather': os.getenv('WEATHER_TABLE', 'DisasterFeed_WeatherData')
        }
        
        self.dynamodb = self._init_dynamodb(aws_config)
        
    def _init_dynamodb(self, aws_config):
        """Initialize DynamoDB resource with environment variables"""
        try:
            region = aws_config['region'] 
            aws_access_key_id = aws_config['key_id'] 
            aws_secret_access_key = aws_config['access_key'] 

            if not all([aws_access_key_id, aws_secret_access_key]):
                raise ValueError("AWS credentials missing from environment variables")

            logger.info(f"Initializing DynamoDB in region {region}")
            return boto3.resource(
                'dynamodb',
                region_name=region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB: {e}")
            raise

    def _get_table(self, table_name: str):
        """Get table reference with error handling"""
        try:
            return self.dynamodb.Table(table_name)
        except ClientError as e:
            logger.error(f"Error accessing table {table_name}: {e}")
            raise

    def list_tables(self) -> List[str]:
        """List all DynamoDB tables in the account"""
        try:
            response = self.dynamodb.meta.client.list_tables()
            return response.get('TableNames', [])
        except ClientError as e:
            logger.error(f"Error listing tables: {e}")
            return []

    def put_user(self, user_data: Dict) -> Optional[str]:
        """Store user information in DynamoDB"""
        try:
            table = self._get_table(self._tables['users'])
            response = table.get_item(Key={'user_id': user_data['user_id']})

            if 'Item' not in response or user_data.get('update_existing', False):
                item = {
                    'user_id': user_data['user_id'],
                    'handle': user_data['handle'],
                    'display_name': user_data.get('display_name', ''),
                    'avatar_url': user_data.get('avatar_url', ''),
                    'created_at': datetime.datetime.now().isoformat()
                }
                table.put_item(Item=item)
                logger.info(f"User stored: {user_data['handle']}")
                
            return user_data['user_id']
        except Exception as e:
            logger.error(f"Error storing user: {e}")
            return None

    def put_post(self, post_data: Dict) -> Optional[str]:
        """Store disaster-related post in DynamoDB"""
        try:
            table = self._get_table(self._tables['posts'])
            
            # Convert types for DynamoDB compatibility
            confidence_score = Decimal(str(post_data.get('confidence_score', 0.0)))
            is_disaster_str = 'true' if post_data.get('is_disaster', False) else 'false'
            
            item = {
                'post_id': post_data['post_id'],
                'indexed_at': self._format_datetime(post_data['indexed_at']),
                'user_id': post_data['user_id'],
                'handle': post_data['handle'],
                'original_text': post_data['original_text'],
                'clean_text': post_data['clean_text'],
                'created_at': self._format_datetime(post_data['created_at']),
                'disaster_type': post_data.get('disaster_type', 'unknown'),
                'confidence_score': confidence_score,
                'is_disaster': post_data.get('is_disaster', False),
                'is_disaster_str': is_disaster_str,
                'has_media': bool(post_data.get('media_urls')),
                **self._optional_fields(post_data, ['display_name', 'avatar_url', 'location_name', 'media_urls'])
            }

            table.put_item(Item=item)
            logger.info(f"Post stored: {post_data['post_id']}")
            return post_data['post_id']
        except Exception as e:
            logger.error(f"Error storing post: {e}")
            return None
    
    def scan_table(self, table_name: str, limit: int = 100) -> List[Dict]:
        """Scan entire table (use cautiously for debugging)"""
        try:
            table = self._get_table(self._tables[table_name])
            response = table.scan(Limit=limit)
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error scanning table {table_name}: {e}")
            return []

    def put_weather_data(self, weather_data: Dict) -> Optional[str]:
        """Store weather data associated with a post"""
        try:
            table = self._get_table(self._tables['weather'])
            weather_id = str(uuid.uuid4())

            # Convert numeric fields to Decimal
            for field in ['temperature', 'humidity', 'wind_speed', 'latitude', 'longitude']:
                if field in weather_data and weather_data[field] is not None:
                    weather_data[field] = Decimal(str(weather_data[field]))

            item = {
                'weather_id': weather_id,
                'post_id': weather_data['post_id'],
                'collected_at': self._format_datetime(weather_data.get('collected_at')),
                **self._optional_fields(weather_data, [
                    'location_name', 'latitude', 'longitude',
                    'weather_condition', 'temperature',
                    'humidity', 'wind_speed'
                ])
            }

            table.put_item(Item=item)
            logger.info(f"Weather data stored for post: {weather_data['post_id']}")
            return weather_id
        except Exception as e:
            logger.error(f"Error storing weather data: {e}")
            return None

    def _format_datetime(self, dt) -> str:
        """Convert datetime objects to ISO format strings"""
        if isinstance(dt, datetime.datetime):
            return dt.isoformat()
        if isinstance(dt, str):
            return dt
        raise ValueError("Invalid datetime format")

    def _optional_fields(self, data: Dict, fields: List[str]) -> Dict:
        """Extract optional fields from data dictionary"""
        return {k: data[k] for k in fields if k in data}


if __name__ == "__main__":
    # Example usage
    db = DisasterDatabase()
    # List tables
    
    