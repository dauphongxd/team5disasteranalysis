import React, { useState } from "react";
import { Marker, InfoWindow } from "@react-google-maps/api";

// Weather emoji mapping
const weatherEmojis = {
  "Clear": "☀️",
  "Clouds": "☁️",
  "Rain": "🌧️",
  "Drizzle": "🌦️",
  "Thunderstorm": "⛈️",
  "Snow": "❄️",
  "Mist": "🌫️",
  "Fog": "🌫️",
  "Haze": "🌫️",
  "Dust": "🌫️",
  "Smoke": "🌫️",
  "Tornado": "🌪️",
  "Hurricane": "🌀",
  "Severe Storm": "⚡",
  "Unknown": "❓"
};

function WeatherMarker({ position, weatherData }) {
  const [isOpen, setIsOpen] = useState(false);
  
  // Get the appropriate emoji
  const getEmoji = () => {
    if (!weatherData.weather) return weatherEmojis["Unknown"];
    return weatherEmojis[weatherData.weather] || weatherEmojis["Unknown"];
  };
  
  // Toggle info window
  const toggleOpen = () => {
    setIsOpen(!isOpen);
  };
  
  return (
    <Marker
      position={position}
      onClick={toggleOpen}
      icon={{
        path: "M 0,0 C -2,-20 -10,-22 -10,-30 A 10,10 0 1,1 10,-30 C 10,-22 2,-20 0,0 z",
        fillColor: "#FF0000",
        fillOpacity: 0,
        strokeWeight: 0,
        scale: 1,
        labelOrigin: { x: 0, y: -30 }
      }}
      label={{
        text: getEmoji(),
        fontSize: "24px",
        className: "weather-marker"
      }}
    >
      {isOpen && (
        <InfoWindow onCloseClick={toggleOpen}>
          <div className="info-window">
            <h3>{weatherData.city || "Weather Location"}</h3>
            <p><strong>Weather:</strong> {weatherData.weather || "Unknown"}</p>
            {weatherData.temperature && (
              <p><strong>Temperature:</strong> {weatherData.temperature}°C</p>
            )}
            {weatherData.humidity && (
              <p><strong>Humidity:</strong> {weatherData.humidity}%</p>
            )}
            {weatherData.wind_speed && (
              <p><strong>Wind Speed:</strong> {weatherData.wind_speed} m/s</p>
            )}
            <p><strong>Severity:</strong> {(weatherData.severity * 100).toFixed(0)}%</p>
          </div>
        </InfoWindow>
      )}
    </Marker>
  );
}

export default WeatherMarker;