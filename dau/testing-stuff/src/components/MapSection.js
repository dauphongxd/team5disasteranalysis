import React, { useEffect, useState, useRef } from "react";

function MapSection({ showLegend = true }) {
    const [alerts, setAlerts] = useState([]);
    const [wildfires, setWildfires] = useState([]);
    const [hurricanes, setHurricanes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [activeDataLayers, setActiveDataLayers] = useState({
        nwsAlerts: true,
        wildfires: true,
        hurricanes: true
    });
    const [alertStats, setAlertStats] = useState({
        byType: {},
        bySeverity: {},
        mappedCount: 0
    });
    const mapRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const layerGroupsRef = useRef({});
    const refreshTimerRef = useRef(null);

    // Function to fetch data and update the state
    const fetchData = async () => {
        try {
            setLoading(true);

            // Fetch all data sources in parallel
            const [alertsData, wildfiresData, hurricanesData] = await Promise.all([
                fetchNWSAlerts(),
                fetchWildfires(),
                fetchHurricanes()
            ]);

            // Update last updated timestamp
            setLastUpdated(new Date());
            setLoading(false);
        } catch (err) {
            console.error("Error fetching data:", err);
            setError("Failed to load disaster data. Please try again.");
            setLoading(false);
        }
    };

    useEffect(() => {
        // Load Leaflet and initial data
        const initializeMap = async () => {
            await loadLeaflet();
            await fetchData();

            // Set up automatic refresh every 5 minutes
            refreshTimerRef.current = setInterval(() => {
                fetchData();
            }, 5 * 60 * 1000); // 5 minutes
        };

        initializeMap();

        return () => {
            // Clean up map when component unmounts
            if (mapInstanceRef.current) {
                mapInstanceRef.current.remove();
                mapInstanceRef.current = null;
            }

            // Clear refresh timer
            if (refreshTimerRef.current) {
                clearInterval(refreshTimerRef.current);
            }
        };
    }, []);

    const fetchNWSAlerts = async () => {
        try {
            // Fetch active alerts from NWS API
            const response = await fetch(
                "https://api.weather.gov/alerts/active?status=actual&message_type=alert"
            );

            if (!response.ok) {
                throw new Error(`NWS API returned ${response.status}`);
            }

            const data = await response.json();

            // Filter alerts to highlight specific disaster types
            const allAlerts = data.features || [];

            // Track how many alerts have valid geometry for mapping
            let mappableCount = 0;
            allAlerts.forEach(alert => {
                if (alert.geometry && alert.geometry.coordinates) {
                    mappableCount++;
                }
            });

            console.log(`Total NWS alerts: ${allAlerts.length}, Mappable: ${mappableCount}`);

            setAlerts(allAlerts);
            return allAlerts;
        } catch (err) {
            console.error("Error fetching NWS data:", err);
            setError("Failed to load weather alerts. Please try again later.");
            return [];
        }
    };

    const fetchWildfires = async () => {
        try {
            // USGS Wildfire data
            // Note: In a real app, you'd use a proper fire data API
            // This is simulated data for demonstration
            const simulatedWildfires = [
                {
                    id: 'wf1',
                    name: 'Caldor Fire',
                    location: [38.6268, -120.2432],
                    size: 221775, // acres
                    containment: 76,
                    started: '2023-08-14'
                },
                {
                    id: 'wf2',
                    name: 'Dixie Fire',
                    location: [40.0722, -121.2086],
                    size: 963309, // acres
                    containment: 94,
                    started: '2023-07-13'
                },
                {
                    id: 'wf3',
                    name: 'KNP Complex',
                    location: [36.5484, -118.7730],
                    size: 88064, // acres
                    containment: 60,
                    started: '2023-09-09'
                },
                {
                    id: 'wf4',
                    name: 'Windy Fire',
                    location: [36.0724, -118.5698],
                    size: 97528, // acres
                    containment: 80,
                    started: '2023-09-09'
                }
            ];

            setWildfires(simulatedWildfires);
            return simulatedWildfires;
        } catch (err) {
            console.error("Error fetching wildfire data:", err);
            return [];
        }
    };

    const fetchHurricanes = async () => {
        try {
            // Hurricane data simulation
            // In a real app, you would use NOAA's Hurricane API
            const simulatedHurricanes = [
                {
                    id: 'h1',
                    name: 'Hurricane Helene',
                    category: 4,
                    pressure: 948,
                    windSpeed: 130, // mph
                    location: [27.8, -82.5],
                    path: [
                        [25.1, -80.0],
                        [26.0, -80.8],
                        [26.8, -81.6],
                        [27.8, -82.5],
                        [28.5, -83.2]
                    ],
                    forecastPath: [
                        [28.5, -83.2],
                        [29.3, -84.0],
                        [30.1, -84.8],
                        [31.0, -85.6]
                    ]
                },
                {
                    id: 'h2',
                    name: 'Tropical Storm Milton',
                    category: 1,
                    pressure: 985,
                    windSpeed: 65, // mph
                    location: [23.2, -88.1],
                    path: [
                        [20.5, -86.2],
                        [21.2, -86.8],
                        [22.1, -87.5],
                        [23.2, -88.1]
                    ],
                    forecastPath: [
                        [23.2, -88.1],
                        [24.0, -88.8],
                        [25.1, -89.5],
                        [26.2, -90.2]
                    ]
                }
            ];

            setHurricanes(simulatedHurricanes);
            return simulatedHurricanes;
        } catch (err) {
            console.error("Error fetching hurricane data:", err);
            return [];
        }
    };

    // Dynamically load Leaflet.js
    const loadLeaflet = async () => {
        try {
            // Only load if window.L isn't already defined
            if (!window.L) {
                // Load Leaflet CSS
                const linkEl = document.createElement('link');
                linkEl.rel = 'stylesheet';
                linkEl.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
                linkEl.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
                linkEl.crossOrigin = '';
                document.head.appendChild(linkEl);

                // Load Leaflet JS
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
                    script.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
                    script.crossOrigin = '';
                    script.onload = resolve;
                    script.onerror = reject;
                    document.head.appendChild(script);
                });
            }
        } catch (err) {
            console.error("Error loading Leaflet:", err);
            setError("Failed to load map. Please try again later.");
            throw err;
        }
    };

    // Function to manually refresh data
    const handleRefreshData = () => {
        fetchData();
    };

    // Function to toggle data layers
    const toggleLayer = (layerName) => {
        setActiveDataLayers(prev => {
            const updatedLayers = { ...prev, [layerName]: !prev[layerName] };

            // Update layer visibility if map is already initialized
            if (mapInstanceRef.current && layerGroupsRef.current[layerName]) {
                if (updatedLayers[layerName]) {
                    layerGroupsRef.current[layerName].addTo(mapInstanceRef.current);
                } else {
                    mapInstanceRef.current.removeLayer(layerGroupsRef.current[layerName]);
                }
            }

            return updatedLayers;
        });
    };

    useEffect(() => {
        // Initialize map after data is loaded
        if (!loading && !error && window.L && mapRef.current) {
            // If map already exists, clean it up first
            if (mapInstanceRef.current) {
                mapInstanceRef.current.remove();
            }

            // Initialize map centered on US
            const map = window.L.map(mapRef.current).setView([39.8, -98.5], 4);
            mapInstanceRef.current = map;

            // Add OpenStreetMap tile layer
            window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);

            // Create layer groups for different data types
            const nwsAlertsLayer = window.L.layerGroup();
            const wildfiresLayer = window.L.layerGroup();
            const hurricanesLayer = window.L.layerGroup();

            layerGroupsRef.current = {
                nwsAlerts: nwsAlertsLayer,
                wildfires: wildfiresLayer,
                hurricanes: hurricanesLayer
            };

            // Process and display NWS alerts
            const alertsByType = {};
            const alertsBySeverity = {};
            let mappedAlertsCount = 0;

            alerts.forEach(alert => {
                const properties = alert.properties;
                const event = properties.event;
                const severity = properties.severity || 'Unknown';

                // Group alerts by event type
                if (!alertsByType[event]) {
                    alertsByType[event] = [];
                }

                // Group alerts by severity
                if (!alertsBySeverity[severity]) {
                    alertsBySeverity[severity] = [];
                }

                alertsByType[event].push(alert);
                alertsBySeverity[severity].push(alert);

                // Skip if no geometry or coordinates
                if (!alert.geometry || !alert.geometry.coordinates) return;

                mappedAlertsCount++;

                // Determine alert color based on event type and severity
                let color = 'blue';
                const eventLower = event.toLowerCase();

                if (eventLower.includes('flood')) {
                    color = '#1e90ff'; // DodgerBlue
                } else if (eventLower.includes('tornado')) {
                    color = '#800080'; // Purple
                } else if (eventLower.includes('thunderstorm') || eventLower.includes('lightning')) {
                    color = '#ffa500'; // Orange
                } else if (eventLower.includes('fire') || eventLower.includes('smoke')) {
                    color = '#ff4500'; // OrangeRed
                } else if (eventLower.includes('winter') || eventLower.includes('snow') || eventLower.includes('ice')) {
                    color = '#87ceeb'; // SkyBlue
                } else if (eventLower.includes('hurricane') || eventLower.includes('tropical')) {
                    color = '#ff69b4'; // HotPink
                } else if (eventLower.includes('heat')) {
                    color = '#dc143c'; // Crimson
                } else {
                    // Default color based on severity
                    switch (properties.severity) {
                        case 'Extreme':
                            color = 'darkred';
                            break;
                        case 'Severe':
                            color = 'red';
                            break;
                        case 'Moderate':
                            color = 'orange';
                            break;
                        case 'Minor':
                            color = 'yellow';
                            break;
                    }
                }

                // For polygon alerts
                if (alert.geometry.type === 'Polygon') {
                    const coordinates = alert.geometry.coordinates[0].map(coord => [coord[1], coord[0]]);
                    window.L.polygon(coordinates, { color, weight: 2, fillOpacity: 0.3 })
                        .bindPopup(`
              <strong>${properties.headline || event}</strong><br>
              <em>Severity: ${properties.severity}</em><br>
              <em>Issued: ${new Date(properties.effective).toLocaleString()}</em><br>
              <em>Expires: ${new Date(properties.expires).toLocaleString()}</em><br>
              ${properties.description ? properties.description.substring(0, 200) + '...' : ''}
              <a href="${properties.url}" target="_blank">More info</a>
            `)
                        .addTo(nwsAlertsLayer);
                }
                // For point alerts
                else if (alert.geometry.type === 'Point') {
                    const [lon, lat] = alert.geometry.coordinates;
                    window.L.circleMarker([lat, lon], {
                        radius: 8,
                        color,
                        fillColor: color,
                        fillOpacity: 0.5
                    })
                        .bindPopup(`
              <strong>${properties.headline || event}</strong><br>
              <em>Severity: ${properties.severity}</em><br>
              <em>Issued: ${new Date(properties.effective).toLocaleString()}</em><br>
              <em>Expires: ${new Date(properties.expires).toLocaleString()}</em><br>
              ${properties.description ? properties.description.substring(0, 200) + '...' : ''}
              <a href="${properties.url}" target="_blank">More info</a>
            `)
                        .addTo(nwsAlertsLayer);
                }
            });

            // Save alert statistics for the legend
            setAlertStats({
                byType: alertsByType,
                bySeverity: alertsBySeverity,
                mappedCount: mappedAlertsCount
            });

            // Create custom wildfire icons
            const fireIcon = window.L.divIcon({
                html: '<div class="fire-icon"></div>',
                className: 'fire-marker',
                iconSize: [30, 30]
            });

            // Add wildfires to the map
            wildfires.forEach(fire => {
                const popupContent = `
          <strong>${fire.name}</strong><br>
          <b>Size:</b> ${fire.size.toLocaleString()} acres<br>
          <b>Containment:</b> ${fire.containment}%<br>
          <b>Started:</b> ${new Date(fire.started).toLocaleDateString()}<br>
        `;

                window.L.marker(fire.location, { icon: fireIcon })
                    .bindPopup(popupContent)
                    .addTo(wildfiresLayer);

                // Add a circle to represent fire size
                const radiusInMeters = Math.sqrt(fire.size * 4047) / Math.PI;
                window.L.circle(fire.location, {
                    radius: radiusInMeters * 2, // Scale for visibility
                    color: '#FF5349',
                    fillColor: '#FF6B6B',
                    fillOpacity: 0.3,
                    weight: 1
                }).addTo(wildfiresLayer);
            });

            // Add hurricanes to the map
            hurricanes.forEach(hurricane => {
                // Current position marker
                const hurricaneIcon = window.L.divIcon({
                    html: `<div class="hurricane-icon cat${hurricane.category}"></div>`,
                    className: 'hurricane-marker',
                    iconSize: [40, 40]
                });

                const popupContent = `
          <strong>${hurricane.name}</strong><br>
          <b>Category:</b> ${hurricane.category}<br>
          <b>Wind Speed:</b> ${hurricane.windSpeed} mph<br>
          <b>Pressure:</b> ${hurricane.pressure} mb<br>
        `;

                window.L.marker(hurricane.location, { icon: hurricaneIcon })
                    .bindPopup(popupContent)
                    .addTo(hurricanesLayer);

                // Draw path
                if (hurricane.path && hurricane.path.length > 1) {
                    window.L.polyline(hurricane.path, {
                        color: '#FF00FF',
                        weight: 3,
                        opacity: 0.7
                    }).addTo(hurricanesLayer);
                }

                // Draw forecast path
                if (hurricane.forecastPath && hurricane.forecastPath.length > 1) {
                    window.L.polyline(hurricane.forecastPath, {
                        color: '#FF00FF',
                        weight: 3,
                        dashArray: '5, 10',
                        opacity: 0.5
                    }).addTo(hurricanesLayer);

                    // Add cone of uncertainty
                    const conePoints = [];
                    const lastHistoricalPoint = hurricane.path[hurricane.path.length - 1];
                    const forecastPoints = hurricane.forecastPath;

                    // Simplified cone - in a real app, use actual forecast uncertainty data
                    const startWidth = 50000; // meters
                    const endWidth = 250000; // meters

                    forecastPoints.forEach((point, i) => {
                        const progress = i / (forecastPoints.length - 1);
                        const width = startWidth + (endWidth - startWidth) * progress;

                        // Create perpendicular points for the cone
                        const prev = i === 0 ? lastHistoricalPoint : forecastPoints[i - 1];
                        const angle = Math.atan2(point[0] - prev[0], point[1] - prev[1]) - Math.PI/2;

                        const leftPoint = [
                            point[0] + Math.sin(angle) * width / 111000,
                            point[1] + Math.cos(angle) * width / 111000
                        ];

                        const rightPoint = [
                            point[0] - Math.sin(angle) * width / 111000,
                            point[1] - Math.cos(angle) * width / 111000
                        ];

                        conePoints.push(leftPoint);
                        // Save right points for the way back
                        if (i === forecastPoints.length - 1) {
                            conePoints.push(rightPoint);
                        }
                    });

                    // Add the right side points in reverse
                    for (let i = forecastPoints.length - 2; i >= 0; i--) {
                        const progress = i / (forecastPoints.length - 1);
                        const width = startWidth + (endWidth - startWidth) * progress;

                        const point = forecastPoints[i];
                        const prev = i === 0 ? lastHistoricalPoint : forecastPoints[i - 1];
                        const angle = Math.atan2(point[0] - prev[0], point[1] - prev[1]) - Math.PI/2;

                        const rightPoint = [
                            point[0] - Math.sin(angle) * width / 111000,
                            point[1] - Math.cos(angle) * width / 111000
                        ];

                        conePoints.push(rightPoint);
                    }

                    window.L.polygon(conePoints, {
                        color: '#FF00FF',
                        weight: 1,
                        fillColor: '#FF00FF',
                        fillOpacity: 0.1
                    }).addTo(hurricanesLayer);
                }
            });

            // Add layers to map based on active state
            if (activeDataLayers.nwsAlerts) nwsAlertsLayer.addTo(map);
            if (activeDataLayers.wildfires) wildfiresLayer.addTo(map);
            if (activeDataLayers.hurricanes) hurricanesLayer.addTo(map);

            // Add refresh control
            const refreshControl = window.L.control({ position: 'topleft' });
            refreshControl.onAdd = function() {
                const div = window.L.DomUtil.create('div', 'refresh-control');
                div.innerHTML = `<button class="refresh-button">Refresh Data</button>`;

                // Prevent map click events from propagating through the control
                window.L.DomEvent.disableClickPropagation(div);

                // Add event handler
                div.querySelector('.refresh-button').addEventListener('click', handleRefreshData);

                return div;
            };
            refreshControl.addTo(map);
        }
    }, [alerts, wildfires, hurricanes, loading, error, activeDataLayers, lastUpdated]);

    // Handler for layer toggle checkboxes in the legend
    const handleLayerToggle = (layerName) => {
        toggleLayer(layerName);
    };

    // Render the legend outside of the map
    const renderLegend = () => {
        if (loading || error || !showLegend) return null;

        return (
            <div className="disaster-map-legend">
                <h4>Disaster Map Legend</h4>
                {lastUpdated && (
                    <div className="timestamp">Last updated: {lastUpdated.toLocaleString()}</div>
                )}
                <div className="auto-update-note">Data automatically refreshes every 5 minutes</div>

                <div className="legend-section">
                    <h5>Data Layers</h5>
                    <div className="layer-toggle">
                        <label>
                            <input
                                type="checkbox"
                                checked={activeDataLayers.nwsAlerts}
                                onChange={() => handleLayerToggle('nwsAlerts')}
                            />
                            <span>NWS Alerts ({alerts.length})</span>
                        </label>
                        <div className="mapping-stats">
                            <em>
                                Mapped: {alertStats.mappedCount} of {alerts.length} alerts
                                ({alerts.length > 0 ? Math.round(alertStats.mappedCount/alerts.length*100) : 0}%)
                            </em>
                            <br/>
                            <em>Note: Only alerts with geometry data appear on map</em>
                        </div>
                    </div>
                    <div className="layer-toggle">
                        <label>
                            <input
                                type="checkbox"
                                checked={activeDataLayers.wildfires}
                                onChange={() => handleLayerToggle('wildfires')}
                            />
                            <span>Wildfires ({wildfires.length})</span>
                        </label>
                    </div>
                    <div className="layer-toggle">
                        <label>
                            <input
                                type="checkbox"
                                checked={activeDataLayers.hurricanes}
                                onChange={() => handleLayerToggle('hurricanes')}
                            />
                            <span>Hurricanes ({hurricanes.length})</span>
                        </label>
                    </div>
                </div>

                {alertStats.bySeverity && Object.keys(alertStats.bySeverity).length > 0 && (
                    <div className="legend-section">
                        <h5>Alert Severities</h5>
                        {(() => {
                            // Define the order we want to display severities
                            const severityOrder = ['Extreme', 'Severe', 'Moderate', 'Minor', 'Unknown'];

                            // Sort the severities according to our defined order
                            const sortedSeverities = Object.keys(alertStats.bySeverity).sort((a, b) => {
                                return severityOrder.indexOf(a) - severityOrder.indexOf(b);
                            });

                            return sortedSeverities.map(severity => {
                                let color;
                                switch (severity) {
                                    case 'Extreme':
                                        color = 'darkred';
                                        break;
                                    case 'Severe':
                                        color = 'red';
                                        break;
                                    case 'Moderate':
                                        color = 'orange';
                                        break;
                                    case 'Minor':
                                        color = 'yellow';
                                        break;
                                    default:
                                        color = 'blue';
                                }

                                return (
                                    <div key={severity} className="legend-item">
                                        <span className="color-dot" style={{ backgroundColor: color }}></span>
                                        <span className="legend-label">
                      {severity} ({alertStats.bySeverity[severity].length})
                    </span>
                                    </div>
                                );
                            });
                        })()}
                    </div>
                )}

                {alertStats.byType && Object.keys(alertStats.byType).length > 0 && (
                    <div className="legend-section">
                        <h5>All Alert Categories</h5>
                        {(() => {
                            // Create a sortable array of event types with their counts
                            const eventTypeEntries = Object.entries(alertStats.byType)
                                .map(([type, alerts]) => ({ type, count: alerts.length }))
                                .sort((a, b) => b.count - a.count); // Sort by count, descending

                            return eventTypeEntries.map(({ type, count }) => {
                                let color = 'blue';
                                const typeLower = type.toLowerCase();

                                if (typeLower.includes('flood')) {
                                    color = '#1e90ff';
                                } else if (typeLower.includes('tornado')) {
                                    color = '#800080';
                                } else if (typeLower.includes('thunderstorm') || typeLower.includes('lightning')) {
                                    color = '#ffa500';
                                } else if (typeLower.includes('fire') || typeLower.includes('smoke')) {
                                    color = '#ff4500';
                                } else if (typeLower.includes('winter') || typeLower.includes('snow') || typeLower.includes('ice')) {
                                    color = '#87ceeb';
                                } else if (typeLower.includes('hurricane') || typeLower.includes('tropical')) {
                                    color = '#ff69b4';
                                } else if (typeLower.includes('heat')) {
                                    color = '#dc143c';
                                }

                                return (
                                    <div key={type} className="legend-item">
                                        <span className="color-dot" style={{ backgroundColor: color }}></span>
                                        <span className="legend-label">
                      {type} ({count})
                    </span>
                                    </div>
                                );
                            });
                        })()}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="map-section">
            {!loading && lastUpdated && (
                <div className="mobile-timestamp">
                    Last updated: {lastUpdated.toLocaleString()}
                </div>
            )}

            {loading && (
                <div className="map-loading">
                    <p>Loading disaster data...</p>
                </div>
            )}

            {error && (
                <div className="map-error">
                    <p>{error}</p>
                    <button onClick={handleRefreshData} className="retry-button">Retry</button>
                </div>
            )}

            <div
                id="map"
                ref={mapRef}
                style={{
                    height: '600px',
                    width: '100%',
                    display: loading ? 'none' : 'block'
                }}
            >
                {!loading && alerts.length === 0 && wildfires.length === 0 && hurricanes.length === 0 && !error && (
                    <p>No active disaster data found</p>
                )}
            </div>

            {/* Render the legend below the map - conditionally based on showLegend prop */}
            {renderLegend()}
        </div>
    );
}

export default MapSection;