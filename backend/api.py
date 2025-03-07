# api.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import os
from dotenv import load_dotenv
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

# Load environment variables
load_dotenv('disasterweb.env')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'my_database'),
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        # Get query parameters for filtering
        disaster_type = request.args.get('type', 'all')
        limit = int(request.args.get('limit', 50))
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Base query using the disaster_posts view
        query = """
        SELECT post_id, original_text, created_at, disaster_type, 
               confidence_score, username, user_id, longitude, latitude 
        FROM disaster_posts
        """
        
        # Add filter if specified
        if disaster_type != 'all':
            query += f" WHERE disaster_type = '{disaster_type}'"
            
        query += " ORDER BY created_at DESC LIMIT %s"
        
        cursor.execute(query, (limit,))
        posts = cursor.fetchall()
        
        # Get media for posts
        for post in posts:
            # Convert datetime objects to ISO format strings for JSON serialization
            if isinstance(post['created_at'], datetime):
                post['created_at'] = post['created_at'].isoformat()
                
            media_query = """
            SELECT media_url, media_type FROM media 
            WHERE post_id = %s
            """
            cursor.execute(media_query, (post['post_id'],))
            media = cursor.fetchall()
            post['media'] = media
        
        cursor.close()
        connection.close()
        
        return jsonify(posts)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/disaster-summary', methods=['GET'])
def get_disaster_summary():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT disaster_type, count, first_occurrence, latest_occurrence, avg_confidence
        FROM disaster_summary
        ORDER BY count DESC
        """
        
        cursor.execute(query)
        summary = cursor.fetchall()
        
        # Convert datetime objects to ISO format strings
        for item in summary:
            if isinstance(item['first_occurrence'], datetime):
                item['first_occurrence'] = item['first_occurrence'].isoformat()
            if isinstance(item['latest_occurrence'], datetime):
                item['latest_occurrence'] = item['latest_occurrence'].isoformat()
        
        cursor.close()
        connection.close()
        
        return jsonify(summary)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/disaster-types', methods=['GET'])
def get_disaster_types():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT DISTINCT disaster_type 
        FROM posts 
        WHERE is_disaster = true 
        ORDER BY disaster_type
        """
        
        cursor.execute(query)
        types = [row['disaster_type'] for row in cursor.fetchall()]
        
        cursor.close()
        connection.close()
        
        return jsonify(types)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)