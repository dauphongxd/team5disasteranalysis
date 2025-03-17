import React, { useState, useEffect } from "react";
import { GoogleMap, LoadScript, HeatmapLayer } from "@react-google-maps/api";
import WeatherMarker from "./WeatherMarker";

const containerStyle = {
  width: '100%',
  height: '600px'
};

const center = {
  lat: 39.8283,
  lng: -98.5795 // Center of US
};

// Update this to match your Flask server's port
const API_URL = "http://localhost:5002/get_weather_data";

const GOOGLE_MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;

function MapSection() {
  const [weatherData, setWeatherData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showEmojis, setShowEmojis] = useState(true);
  const [heatmapData, setHeatmapData] = useState([]);

  // Fetch weather data
  useEffect(() => {
    // For testing, let's create some sample data
    const sampleData = [
      { latitude: 40.7128, longitude: -74.0060, severity: 0.8, city: "New York", weather: "Clouds", temperature: 22, humidity: 65, wind_speed: 5 },
      { latitude: 34.0522, longitude: -118.2437, severity: 0.6, city: "Los Angeles", weather: "Clear", temperature: 28, humidity: 50, wind_speed: 3 },
      { latitude: 41.8781, longitude: -87.6298, severity: 0.7, city: "Chicago", weather: "Rain", temperature: 18, humidity: 75, wind_speed: 7 },
      { latitude: 29.7604, longitude: -95.3698, severity: 0.9, city: "Houston", weather: "Thunderstorm", temperature: 30, humidity: 80, wind_speed: 10 },
      { latitude: 39.9526, longitude: -75.1652, severity: 0.5, city: "Philadelphia", weather: "Drizzle", temperature: 20, humidity: 70, wind_speed: 4 },
      { latitude: 33.4484, longitude: -112.0740, severity: 0.8, city: "Phoenix", weather: "Clear", temperature: 35, humidity: 30, wind_speed: 6 },
      { latitude: 29.4241, longitude: -98.4936, severity: 0.6, city: "San Antonio", weather: "Clouds", temperature: 32, humidity: 55, wind_speed: 5 },
      { latitude: 32.7157, longitude: -117.1611, severity: 0.4, city: "San Diego", weather: "Clear", temperature: 26, humidity: 60, wind_speed: 4 },
      { latitude: 32.7767, longitude: -96.7970, severity: 0.7, city: "Dallas", weather: "Clouds", temperature: 31, humidity: 65, wind_speed: 6 },
      { latitude: 37.7749, longitude: -122.4194, severity: 0.5, city: "San Francisco", weather: "Fog", temperature: 19, humidity: 75, wind_speed: 8 },
    ];

    // Try to fetch real data, but use sample data if that fails
    const fetchWeatherData = async () => {
      try {
        console.log(`Fetching weather data from: ${API_URL}`);
        
        const response = await fetch(API_URL);
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("Weather data received:", data);
        setWeatherData(data);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching weather data:', error);
        console.log('Using sample data instead');
        setWeatherData(sampleData);
        setLoading(false);
      }
    };

    fetchWeatherData();
  }, []);

  // Handle map load event
  const handleMapLoad = (map) => {
    console.log("Map loaded, creating heatmap data");
    if (weatherData.length > 0 && window.google && window.google.maps) {
      try {
        const data = weatherData
          .filter(point => 
            typeof point.latitude === 'number' && 
            typeof point.longitude === 'number' &&
            typeof point.severity === 'number'
          )
          .map(point => ({
            location: new window.google.maps.LatLng(point.latitude, point.longitude),
            weight: point.severity * 10
          }));
        setHeatmapData(data);
      } catch (error) {
        console.error("Error creating heatmap data:", error);
      }
    }
  };

  // Toggle emoji display
  const toggleEmojis = () => {
    setShowEmojis(!showEmojis);
  };

  return (
    <div className="map-section">
      {/* Controls - only emoji toggle button */}
      <div className="map-controls">
        <button 
          className="toggle-button" 
          onClick={toggleEmojis}
        >
          {showEmojis ? "Hide Weather Icons" : "Show Weather Icons"}
        </button>
      </div>

      {/* Debug info */}
      <div className="debug-info">
        {!loading && (
          <div>Data points: {weatherData.length}</div>
        )}
      </div>

      <LoadScript
        googleMapsApiKey={GOOGLE_MAPS_API_KEY}
        libraries={["visualization"]}
      >
        <GoogleMap
          mapContainerStyle={containerStyle}
          center={center}
          zoom={4}
          options={{ mapTypeId: "satellite" }} // Use satellite view for better contrast
          onLoad={handleMapLoad}
        >
          {/* Heatmap Layer */}
          {!loading && heatmapData.length > 0 && (
            <HeatmapLayer
              data={heatmapData}
              options={{
                radius: 40,
                opacity: 0.8,
                dissipating: true,
                maxIntensity: 10,
                gradient: [
                  'rgba(0, 255, 255, 0)',
                  'rgba(0, 255, 255, 1)',
                  'rgba(0, 191, 255, 1)',
                  'rgba(0, 127, 255, 1)',
                  'rgba(0, 63, 255, 1)',
                  'rgba(0, 0, 255, 1)',
                  'rgba(0, 0, 223, 1)',
                  'rgba(0, 0, 191, 1)',
                  'rgba(0, 0, 159, 1)',
                  'rgba(0, 0, 127, 1)',
                  'rgba(63, 0, 91, 1)',
                  'rgba(127, 0, 63, 1)',
                  'rgba(191, 0, 31, 1)',
                  'rgba(255, 0, 0, 1)'
                ]
              }}
            />
          )}

          {/* Weather Markers with Emojis */}
          {!loading && showEmojis && weatherData.map((point, index) => (
            <WeatherMarker
              key={`marker-${index}`}
              position={{ lat: point.latitude, lng: point.longitude }}
              weatherData={point}
            />
          ))}
        </GoogleMap>
      </LoadScript>
      
      {/* Loading and error states */}
      {loading && <div className="loading-overlay">Loading weather data...</div>}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

export default MapSection;