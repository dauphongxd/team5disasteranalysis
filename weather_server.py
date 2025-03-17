from flask import Flask, jsonify
from flask_cors import CORS
import random
import logging
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Configure CORS more explicitly
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": "*"}})

# Load environment variables
load_dotenv()

# Use the API key from environment variables
API_KEY = os.getenv("OPENWEATHER_API_KEY")

CITIES = [
    {"name": "New York", "latitude": 40.7128, "longitude": -74.0060},
    {"name": "Los Angeles", "latitude": 34.0522, "longitude": -118.2437},
    {"name": "Chicago", "latitude": 41.8781, "longitude": -87.6298},
    {"name": "Miami", "latitude": 25.7617, "longitude": -80.1918},
    {"name": "San Francisco", "latitude": 37.7749, "longitude": -122.4194},
    {"name": "Seattle", "latitude": 47.6062, "longitude": -122.3321},
    {"name": "Denver", "latitude": 39.7392, "longitude": -104.9903},
    {"name": "Houston", "latitude": 29.7604, "longitude": -95.3698},
    {"name": "Boston", "latitude": 42.3601, "longitude": -71.0589},
    {"name": "Atlanta", "latitude": 33.7490, "longitude": -84.3880},
]

# Add an extreme weather point
EXTREME_WEATHER = {
    "name": "Severe Storm",
    "latitude": 40.7128,  # New York area
    "longitude": -74.0060,
    "severity": 1.0  # Very high severity - this will make it red
}

def calculate_severity(weather_data):
    """Calculate severity (0.0 to 1.0) based on actual weather parameters"""
    severity = 0.0
    
    # Get weather parameters
    temp = weather_data["main"]["temp"]  # Temperature in Celsius
    humidity = weather_data["main"]["humidity"]  # Humidity percentage
    weather_condition = weather_data["weather"][0]["main"]
    
    # Add severity for extreme temperatures
    if temp > 35: severity += 0.3  # Very hot
    elif temp > 30: severity += 0.2  # Hot
    elif temp < -10: severity += 0.3  # Very cold
    elif temp < 0: severity += 0.2  # Cold
    
    # Add severity for weather conditions
    condition_severity = {
        "Thunderstorm": 0.4,
        "Tornado": 0.5,
        "Hurricane": 0.5,
        "Snow": 0.3,
        "Rain": 0.2,
        "Drizzle": 0.1,
        "Fog": 0.2,
        "Clear": 0.0,
        "Clouds": 0.1
    }
    severity += condition_severity.get(weather_condition, 0.1)
    
    # Add severity for high humidity
    if humidity > 90: severity += 0.2
    elif humidity > 80: severity += 0.1
    
    # If we have wind data
    if "wind" in weather_data:
        wind_speed = weather_data["wind"]["speed"]  # Wind speed in m/s
        if wind_speed > 20: severity += 0.3  # Very windy
        elif wind_speed > 10: severity += 0.2  # Windy
    
    # Ensure severity stays between 0 and 1
    return min(1.0, severity)

@app.route("/get_weather_data", methods=["GET"])
def get_weather_data():
    logger.info("Received request for weather data")
    
    # Fetch real weather data
    weather_data = []
    
    for city in CITIES:
        try:
            response = requests.get(
                "http://api.openweathermap.org/data/2.5/weather",
                params={"lat": city["latitude"], "lon": city["longitude"], "appid": API_KEY, "units": "metric"}
            )
            
            if response.status_code == 200:
                data = response.json()
                severity = calculate_severity(data)
                
                weather_data.append({
                    "latitude": city["latitude"],
                    "longitude": city["longitude"],
                    "severity": severity,
                    "city": city["name"],
                    "weather": data["weather"][0]["main"],
                    "weather_description": data["weather"][0]["description"],
                    "weather_icon": data["weather"][0]["icon"],
                    "weather_id": data["weather"][0]["id"],
                    "temperature": data["main"]["temp"],
                    "humidity": data["main"]["humidity"],
                    "wind_speed": data["wind"].get("speed", 0)
                })
                logger.info(f"Added data for {city['name']} with severity {severity} and weather {data['weather'][0]['main']}")
            else:
                logger.warning(f"Failed to get weather data for {city['name']}: {response.status_code}")
                # Fallback to random severity if API call fails
                weather_data.append({
                    "latitude": city["latitude"],
                    "longitude": city["longitude"],
                    "severity": round(random.uniform(0.2, 0.9), 2),
                    "city": city["name"],
                    "weather": "Unknown",
                    "weather_description": "Data unavailable",
                    "weather_icon": "50d",  # Default mist icon
                    "weather_id": 741  # Mist ID
                })
        except Exception as e:
            logger.error(f"Error fetching weather data for {city['name']}: {e}")
            # Fallback to random severity if API call fails
            weather_data.append({
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "severity": round(random.uniform(0.2, 0.9), 2),
                "city": city["name"],
                "weather": "Unknown",
                "weather_description": "Error fetching data",
                "weather_icon": "50d",  # Default mist icon
                "weather_id": 741  # Mist ID
            })
    
    # Add the extreme weather point
    weather_data.append({
        "latitude": EXTREME_WEATHER["latitude"],
        "longitude": EXTREME_WEATHER["longitude"],
        "severity": EXTREME_WEATHER["severity"],
        "city": EXTREME_WEATHER["name"],
        "weather": "Severe Storm",
        "weather_description": "Extreme weather event",
        "weather_icon": "11d",  # Thunderstorm icon
        "weather_id": 781  # Tornado ID
    })
    
    logger.info(f"Returning {len(weather_data)} weather data points")
    return jsonify(weather_data)

@app.route("/", methods=["GET"])
def home():
    return "Weather API is running. Use /get_weather_data to get weather data."

if __name__ == "__main__":
    # Use a fixed port instead of trying multiple ports
    fixed_port = 5002
    print(f"Starting Flask server on port {fixed_port}...")
    app.run(debug=True, port=fixed_port, host="127.0.0.1")