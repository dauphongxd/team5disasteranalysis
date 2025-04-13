import React, { useEffect, useState, useRef } from "react";

function MapSection({ performanceMode, showDataViewer, toggleDataViewer, NWSDataViewerComponent }) {
  const [alerts, setAlerts] = useState([]);
  const [wildfires, setWildfires] = useState([]);
  const [hurricanes, setHurricanes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [activeDataLayers, setActiveDataLayers] = useState({
    nwsAlerts: true,
    wildfires: true,
    hurricanes: true,
    flaggedAlerts: true
  });
  const [alertStats, setAlertStats] = useState({
    byType: {},
    bySeverity: {},
    mappedCount: 0,
    flaggedCount: 0
  });
  const [isLegendExpanded, setIsLegendExpanded] = useState(false);
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layerGroupsRef = useRef({});
  const refreshTimerRef = useRef(null);

  // Function to fetch data and update the state
  const fetchData = async () => {
    if (performanceMode) {
      setLoading(false);
      return;
    }

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
    // Skip heavy processing in performance mode
    if (performanceMode) {
      setLoading(false);
      return;
    }

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
  }, [performanceMode]);

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
        
        // Load Leaflet MarkerCluster plugin after Leaflet loads
        await new Promise((resolve, reject) => {
          // MarkerCluster CSS
          const clusterCssLink = document.createElement('link');
          clusterCssLink.rel = 'stylesheet';
          clusterCssLink.href = 'https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css';
          document.head.appendChild(clusterCssLink);
          
          // MarkerCluster Default CSS
          const clusterDefaultCssLink = document.createElement('link');
          clusterDefaultCssLink.rel = 'stylesheet';
          clusterDefaultCssLink.href = 'https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css';
          document.head.appendChild(clusterDefaultCssLink);
          
          // MarkerCluster JS
          const clusterScript = document.createElement('script');
          clusterScript.src = 'https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js';
          clusterScript.onload = resolve;
          clusterScript.onerror = reject;
          document.head.appendChild(clusterScript);
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
    // Initialize map after data is loaded and not in performance mode
    if (!loading && !error && !performanceMode && window.L && mapRef.current) {
      // If map already exists, clean it up first
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
      }

      // Initialize map centered on US
      const map = window.L.map(mapRef.current, {
        center: [39.8, -98.5],
        zoom: 4,
        zoomControl: false, // We'll add a custom position for zoom control
        minZoom: 3, // Limit zoom out to avoid distortion
        maxBoundsViscosity: 1.0 // Keep map within bounds
      });
      mapInstanceRef.current = map;

      // Set map bounds to focus on the US with some extra space
      const southWest = window.L.latLng(18, -140);
      const northEast = window.L.latLng(62, -50);
      const bounds = window.L.latLngBounds(southWest, northEast);
      map.setMaxBounds(bounds);

      // Add zoom control to top-right
      window.L.control.zoom({
        position: 'topright'
      }).addTo(map);

      // Add scale control to bottom-left
      window.L.control.scale({
        imperial: true,
        metric: true,
        position: 'bottomleft'
      }).addTo(map);

      // Add OpenStreetMap tile layer
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | <a href="https://www.weather.gov" target="_blank">NWS Data</a>',
        maxZoom: 19
      }).addTo(map);

      // Create layer groups
      const nwsAlertsLayer = window.L.layerGroup();
      const wildfiresLayer = window.L.layerGroup();
      const hurricanesLayer = window.L.layerGroup();
      
      // Use marker clustering for flag markers to better organize them
      const flaggedAlertsLayer = window.L.markerClusterGroup({
        maxClusterRadius: 30,
        iconCreateFunction: function(cluster) {
          const count = cluster.getChildCount();
          let size = 'small';
          if (count > 50) {
            size = 'large';
          } else if (count > 20) {
            size = 'medium';
          }
          
          return window.L.divIcon({
            html: `<div class="cluster-icon cluster-${size}">${count}</div>`,
            className: 'alert-cluster-icon',
            iconSize: window.L.point(40, 40)
          });
        },
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: true,
        zoomToBoundsOnClick: true,
        animate: true
      });
      
      // Separate cluster group for regular alerts
      const regularAlertsCluster = window.L.markerClusterGroup({
        maxClusterRadius: 60,
        disableClusteringAtZoom: 7,
        spiderfyOnMaxZoom: true
      });
      
      // Only add active layers to the map
      if (activeDataLayers.nwsAlerts) nwsAlertsLayer.addTo(mapInstanceRef.current);
      if (activeDataLayers.wildfires) wildfiresLayer.addTo(mapInstanceRef.current);
      if (activeDataLayers.hurricanes) hurricanesLayer.addTo(mapInstanceRef.current);
      
      layerGroupsRef.current = {
        nwsAlerts: nwsAlertsLayer,
        wildfires: wildfiresLayer,
        hurricanes: hurricanesLayer,
        flaggedAlerts: flaggedAlertsLayer,
        regularAlertsCluster: regularAlertsCluster
      };

      // Helper function to check if alert is urgent (expiring soon)
      const isUrgent = (alert) => {
        const now = new Date();
        const expiryDate = new Date(alert.properties.expires);
        const hoursRemaining = (expiryDate - now) / (1000 * 60 * 60);
        return hoursRemaining < 3; // Less than 3 hours until expiry
      };
      
      // Helper function to create a flag icon for an alert
      const simpleFlagIcon = (alert) => {
        const event = alert.properties.event.toLowerCase();
        const severity = alert.properties.severity;
        
        // Determine color based on severity
        let color = '#1e90ff'; // Default blue
        if (severity === 'Extreme') {
          color = '#ff0000'; // Red for extreme
        } else if (severity === 'Severe') {
          color = '#ff7700'; // Orange for severe
        } else if (severity === 'Moderate') {
          color = '#ffc107'; // Yellow for moderate
        }
        
        // Determine icon based on event type
        let icon = '⚠️'; // Default warning icon
        if (event.includes('tornado')) {
          icon = '🌪️';
          color = '#800080'; // Purple for tornado
        } else if (event.includes('hurricane') || event.includes('tropical')) {
          icon = '🌀';
          color = '#ff69b4'; // Pink for hurricane
        } else if (event.includes('flood')) {
          icon = '🌊';
          color = '#1e90ff'; // Blue for flood
        } else if (event.includes('fire') || event.includes('smoke')) {
          icon = '🔥';
          color = '#ff4500'; // Red-orange for fire
        } else if (event.includes('winter') || event.includes('snow') || event.includes('ice')) {
          icon = '❄️';
          color = '#87ceeb'; // Light blue for winter
        } else if (event.includes('thunder') || event.includes('lightning')) {
          icon = '⚡';
          color = '#ffa500'; // Orange for thunder
        }
        
        // Create the flag HTML
        const flagHtml = `
          <div class="flag-marker">
            <div class="flag-pole"></div>
            <div class="flag-banner" style="background-color: ${color}">${icon}</div>
            ${isUrgent(alert) ? '<div class="urgent-indicator"></div>' : ''}
          </div>
        `;
        
        return window.L.divIcon({
          html: flagHtml,
          className: 'alert-flag-icon',
          iconSize: [30, 40],
          iconAnchor: [5, 40]
        });
      };

      // Helper function to format time remaining
      const formatTimeRemaining = (expiryTime) => {
        const now = new Date();
        const expiryDate = new Date(expiryTime);
        const timeDiff = expiryDate - now;
        const hoursRemaining = Math.round((timeDiff / (1000 * 60 * 60)) * 10) / 10;
        
        if (hoursRemaining <= 0) {
          return '<span style="color: #ff0000; font-weight: bold;">EXPIRED</span>';
        } else if (hoursRemaining < 1) {
          const minutesRemaining = Math.round(hoursRemaining * 60);
          return `<span style="color: #ff0000; font-weight: bold;">EXPIRES SOON: ${minutesRemaining} minutes remaining</span>`;
        } else if (hoursRemaining < 3) {
          return `<span style="color: #ff7700; font-weight: bold;">EXPIRES SOON: ${hoursRemaining} hours remaining</span>`;
        } else {
          return `Expires in: ${Math.floor(hoursRemaining)} hours`;
        }
      };
      
      // Create a marker for alert polygons
      const addAlertMarker = (lat, lon, alert, isImportant) => {
        const marker = window.L.marker([lat, lon], { icon: simpleFlagIcon(alert) })
          .bindPopup(`
            <div class="alert-popup-content">
              ${isImportant ? '<div class="alert-popup-header">⚠️ IMPORTANT ALERT ⚠️</div>' : ''}
              <div class="alert-popup-title">${alert.properties.headline || alert.properties.event}</div>
              <div class="alert-popup-meta">
                <span class="alert-severity">${alert.properties.severity}</span>
                <span class="alert-location">${alert.properties.areaDesc || 'Unknown Area'}</span>
              </div>
              <div class="alert-popup-time">
                <div>Issued: ${new Date(alert.properties.effective).toLocaleString()}</div>
                <div>${formatTimeRemaining(alert.properties.expires)}</div>
              </div>
              ${alert.properties.instruction ? `
                <div class="alert-popup-instructions">
                  <strong>Instructions:</strong> ${alert.properties.instruction.substring(0, 150)}${alert.properties.instruction.length > 150 ? '...' : ''}
                </div>
              ` : ''}
              <a href="${alert.properties.url}" target="_blank" class="alert-popup-link">View Full Details</a>
            </div>
          `);
          
        // Add marker to appropriate cluster group
        if (isImportant) {
          flaggedAlertsLayer.addLayer(marker);
        } else {
          regularAlertsCluster.addLayer(marker);
        }
      };

      // Process and display NWS alerts
      const alertsByType = {};
      const alertsBySeverity = {};
      let mappedAlertsCount = 0;
      let flaggedAlertsCount = 0;
      
      // Function to determine if an alert should be flagged as critical
      const shouldFlagAlert = (alert) => {
        const properties = alert.properties;
        const eventLower = properties.event.toLowerCase();
        const severity = properties.severity;
        
        // Enhanced flag criteria - flag more alert types
        return (
          // Flag all extreme and severe alerts
          (severity === 'Extreme' || severity === 'Severe') || 
          // Flag specific hazardous events regardless of severity
          eventLower.includes('tornado') || 
          eventLower.includes('hurricane') || 
          eventLower.includes('flash flood') || 
          eventLower.includes('wildfire') ||
          eventLower.includes('tsunami') ||
          eventLower.includes('earthquake')
        );
      };

      // Function to determine flag color based on alert type and severity
      const getFlagColor = (alert) => {
        const properties = alert.properties;
        const eventLower = properties.event.toLowerCase();
        const severity = properties.severity;
        
        // First prioritize by event type
        if (eventLower.includes('tornado')) {
          return '#800080'; // Purple for tornadoes
        } else if (eventLower.includes('hurricane') || eventLower.includes('tropical storm')) {
          return '#ff69b4'; // Hot pink for hurricanes
        } else if (eventLower.includes('flood')) {
          return '#1e90ff'; // Dodger blue for floods
        } else if (eventLower.includes('fire') || eventLower.includes('wildfire')) {
          return '#ff4500'; // Orange red for fires
        } else if (eventLower.includes('tsunami')) {
          return '#00ffff'; // Cyan for tsunamis
        } else if (eventLower.includes('earthquake')) {
          return '#8b4513'; // Saddle brown for earthquakes
        }
        
        // Then by severity if event type doesn't match
        switch (severity) {
          case 'Extreme':
            return '#ff0000'; // Red
          case 'Severe':
            return '#ff7700'; // Orange
          case 'Moderate':
            return '#ffcc00'; // Yellow
          default:
            return '#ff0000'; // Default red
        }
      };

      // Create a function to generate flag HTML based on alert properties
      const createFlagIconHtml = (alert) => {
        const properties = alert.properties;
        const eventLower = properties.event.toLowerCase();
        const severity = properties.severity;
        const flagColor = getFlagColor(alert);
        
        // Check if this is a time-sensitive alert (expiring soon)
        const now = new Date();
        const expiryDate = new Date(properties.expires);
        const timeDiff = expiryDate - now;
        const hoursRemaining = timeDiff / (1000 * 60 * 60);
        
        // Check if this is a critical alert
        const isCritical = shouldFlagAlert(alert);
        
        // Add urgent class if less than 2 hours remaining or it's a critical alert
        const isUrgent = (hoursRemaining < 2 && hoursRemaining > 0) || (isCritical && hoursRemaining < 6);
        
        // Add animation and styling based on alert type
        const pulseClass = isUrgent ? 'pulse-urgent' : 'pulse-normal';
        
        // Create event-specific icon badges
        let eventBadge = '';
        if (eventLower.includes('tornado')) {
          eventBadge = '🌪️';
        } else if (eventLower.includes('hurricane') || eventLower.includes('tropical')) {
          eventBadge = '🌀';
        } else if (eventLower.includes('flood')) {
          eventBadge = '🌊';
        } else if (eventLower.includes('fire')) {
          eventBadge = '🔥';
        } else if (eventLower.includes('thunder') || eventLower.includes('lightning')) {
          eventBadge = '⚡';
        } else if (eventLower.includes('snow') || eventLower.includes('winter')) {
          eventBadge = '❄️';
        } else if (eventLower.includes('earthquake')) {
          eventBadge = '⚠️';
        } else {
          eventBadge = '⚠️';
        }
        
        // Make flags for critical alerts slightly larger
        const scaleStyle = isCritical ? 'transform: scale(1.15);' : '';
        
        return `
          <div class="flag-marker ${pulseClass}" style="${scaleStyle}">
            <div class="flag-pole" style="${isCritical ? 'width: 4px; background-color: #000;' : ''}"></div>
            <div class="flag-banner" style="background-color: ${flagColor};">${eventBadge}</div>
            ${isUrgent ? '<div class="urgent-indicator"></div>' : ''}
          </div>
        `;
      };
      
      // Remove this duplicate createFlagIcon function
      const createFlagIcon = (alert) => {
        return window.L.divIcon({
          html: createFlagIconHtml(alert),
          className: 'alert-flag-icon',
          iconSize: [30, 40],
          iconAnchor: [5, 40]
        });
      };

      // Update the layer toggle function reference to handle clusters
      const originalToggleLayer = toggleLayer;
      
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
            
            // Calculate centroid of polygon for flag placement
            let centroidLat = 0;
            let centroidLon = 0;
            coordinates.forEach(coord => {
              centroidLat += coord[0];
              centroidLon += coord[1];
            });
            centroidLat /= coordinates.length;
            centroidLon /= coordinates.length;
            
            // Check if this is an important alert that should be highlighted
            const isImportantAlert = shouldFlagAlert(alert);
            
            // Add a flag marker for this alert using our cluster-enabled function
            addAlertMarker(centroidLat, centroidLon, alert, isImportantAlert);
            
            // Increment flagged count only for important alerts
            if (isImportantAlert) {
              flaggedAlertsCount++;
            }
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
            
            // Check if this is an important alert that should be highlighted
            const isImportantAlert = shouldFlagAlert(alert);
            
            // Add a flag marker for this alert using our cluster-enabled function
            addAlertMarker(lat, lon, alert, isImportantAlert);
            
            // Increment flagged count only for important alerts
            if (isImportantAlert) {
              flaggedAlertsCount++;
            }
        }
      });

      // Save alert statistics for the legend
      setAlertStats({
        byType: alertsByType,
        bySeverity: alertsBySeverity,
        mappedCount: mappedAlertsCount,
        flaggedCount: flaggedAlertsCount
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

      // After processing all alerts, add the cluster groups to the map if active
      if (activeDataLayers.nwsAlerts) regularAlertsCluster.addTo(mapInstanceRef.current);
      if (activeDataLayers.flaggedAlerts) flaggedAlertsLayer.addTo(mapInstanceRef.current);

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
  }, [alerts, wildfires, hurricanes, loading, error, performanceMode, activeDataLayers, lastUpdated]);

  // Handler for layer toggle checkboxes in the legend
  const handleLayerToggle = (layerName) => {
    toggleLayer(layerName);
  };

  // Toggle legend expanded/collapsed state
  const toggleLegendExpanded = () => {
    // If collapsing the legend and data viewer is visible, also hide the data viewer
    if (isLegendExpanded && showDataViewer) {
      toggleDataViewer();
    }
    setIsLegendExpanded(!isLegendExpanded);
  };

  // Render the legend outside of the map
  const renderLegend = () => {
    if (loading || error || performanceMode) return null;

    return (
      <div className={`disaster-map-legend ${isLegendExpanded ? 'expanded' : 'collapsed'}`}>
        <div className="legend-header">
          <h4>Disaster Map Legend</h4>
          <button 
            className="legend-toggle-button"
            onClick={toggleLegendExpanded}
            aria-label={isLegendExpanded ? "Collapse legend" : "Expand legend"}
          >
            {isLegendExpanded ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M7 14l5-5 5 5z"/>
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M7 10l5 5 5-5z"/>
              </svg>
            )}
          </button>
        </div>
        
        {isLegendExpanded && (
          <>
            {lastUpdated && (
              <div className="timestamp">Last updated: {lastUpdated.toLocaleString()}</div>
            )}
            <div className="auto-update-note">Data automatically refreshes every 5 minutes</div>
            
            <div className="legend-section">
              <h5>Map Layers</h5>
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
                  <em>All alerts are displayed as flag markers on the map</em>
                </div>
              </div>
              <div className="layer-toggle">
                <label>
                  <input
                    type="checkbox"
                    checked={activeDataLayers.flaggedAlerts}
                    onChange={() => handleLayerToggle('flaggedAlerts')}
                  />
                  <span>Critical Alerts ({alertStats.flaggedCount || 0})</span>
                </label>
                {alertStats.flaggedCount > 0 && (
                  <div className="mapping-stats">
                    <em>
                      Severe and high-priority alerts requiring immediate attention
                    </em>
                  </div>
                )}
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

              {/* NWS Data Viewer Toggle Button */}
              <div className="layer-toggle nws-viewer-toggle">
                <button
                  className={`nws-legend-button ${showDataViewer ? 'active' : ''}`}
                  onClick={toggleDataViewer}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                    <path d="M19 9h-14l7 7 7-7z"></path>
                  </svg>
                  {showDataViewer ? 'Hide NWS Data Viewer' : 'Show NWS Data Viewer'}
                </button>
              </div>
            </div>
            
            {/* Render NWSDataViewer component inside the legend if showDataViewer is true */}
            {showDataViewer && NWSDataViewerComponent && (
              <div className="legend-section nws-viewer-container">
                <NWSDataViewerComponent />
              </div>
            )}
            
            <div className="legend-section">
              <h5>Alert Flag Guide</h5>
              <div className="flag-guide">
                <div className="flag-example-row">
                  <div className="flag-example">
                    <div className="mini-flag" style={{backgroundColor: '#ff0000'}}>⚠️</div>
                    <span>Extreme</span>
                  </div>
                  <div className="flag-example">
                    <div className="mini-flag" style={{backgroundColor: '#ff7700'}}>⚠️</div>
                    <span>Severe</span>
                  </div>
                </div>
                <div className="flag-example-row">
                  <div className="flag-example">
                    <div className="mini-flag" style={{backgroundColor: '#800080'}}>🌪️</div>
                    <span>Tornado</span>
                  </div>
                  <div className="flag-example">
                    <div className="mini-flag" style={{backgroundColor: '#ff69b4'}}>🌀</div>
                    <span>Hurricane</span>
                  </div>
                </div>
                <div className="flag-example-row">
                  <div className="flag-example">
                    <div className="mini-flag" style={{backgroundColor: '#1e90ff'}}>🌊</div>
                    <span>Flood</span>
                  </div>
                  <div className="flag-example">
                    <div className="mini-flag" style={{backgroundColor: '#ff4500'}}>🔥</div>
                    <span>Fire</span>
                  </div>
                </div>
                <div className="flag-example-row">
                  <div className="flag-example">
                    <div className="mini-flag" style={{backgroundColor: '#87ceeb'}}>❄️</div>
                    <span>Winter</span>
                  </div>
                  <div className="flag-example">
                    <div className="mini-flag" style={{backgroundColor: '#ffa500'}}>⚡</div>
                    <span>Thunder</span>
                  </div>
                </div>
              </div>
            </div>
            
            {alertStats.bySeverity && Object.keys(alertStats.bySeverity).length > 0 && (
              <div className="legend-section">
                <h5>Alerts by Severity</h5>
                <div className="severity-stats">
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
                      
                      const count = alertStats.bySeverity[severity].length;
                      const percentage = alerts.length > 0 
                        ? Math.round((count / alerts.length) * 100)
                        : 0;
                      
                      return (
                        <div key={severity} className="severity-item">
                          <div className="severity-label">
                            <span className="color-dot" style={{ backgroundColor: color }}></span>
                            <span className="legend-label">{severity}</span>
                          </div>
                          <div className="severity-bar-container">
                            <div 
                              className="severity-bar" 
                              style={{ 
                                width: `${percentage}%`,
                                backgroundColor: color,
                                minWidth: count > 0 ? '10px' : '0'
                              }}
                            ></div>
                            <span className="severity-count">{count} ({percentage}%)</span>
                          </div>
                        </div>
                      );
                    });
                  })()}
                </div>
              </div>
            )}
            
            {alertStats.byType && Object.keys(alertStats.byType).length > 0 && (
              <div className="legend-section">
                <h5>Top Alert Categories</h5>
                <div className="type-stats">
                  {(() => {
                    // Create a sortable array of event types with their counts
                    const eventTypeEntries = Object.entries(alertStats.byType)
                      .map(([type, alerts]) => ({ type, count: alerts.length }))
                      .sort((a, b) => b.count - a.count); // Sort by count, descending
                    
                    // Only show top 6 categories
                    const topEventTypes = eventTypeEntries.slice(0, 6);
                    
                    return topEventTypes.map(({ type, count }) => {
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
                      
                      const percentage = alerts.length > 0 
                        ? Math.round((count / alerts.length) * 100)
                        : 0;
                      
                      return (
                        <div key={type} className="type-item">
                          <div className="type-label">
                            <span className="color-dot" style={{ backgroundColor: color }}></span>
                            <span className="legend-label" title={type}>
                              {type.length > 20 ? type.substring(0, 18) + '...' : type}
                            </span>
                          </div>
                          <div className="type-bar-container">
                            <div 
                              className="type-bar" 
                              style={{ 
                                width: `${percentage}%`,
                                backgroundColor: color,
                                minWidth: count > 0 ? '10px' : '0'
                              }}
                            ></div>
                            <span className="type-count">{count} ({percentage}%)</span>
                          </div>
                        </div>
                      );
                    });
                  })()}
                  {Object.keys(alertStats.byType).length > 6 && (
                    <div className="more-types-note">
                      <em>+ {Object.keys(alertStats.byType).length - 6} more categories</em>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            <div className="legend-section legend-footer">
              <button 
                className="legend-refresh-button" 
                onClick={handleRefreshData}
              >
                Refresh Data
              </button>
            </div>
          </>
        )}
        {!isLegendExpanded && (
          <div className="collapsed-legend-summary">
            <div className="collapsed-stats">
              <span>Alerts: {alerts.length}</span>
              <span>Critical: {alertStats.flaggedCount}</span>
              <span>Wildfires: {wildfires.length}</span>
              <span>Hurricanes: {hurricanes.length}</span>
            </div>
            <div className="collapsed-controls">
              <button 
                className="legend-refresh-button collapsed-refresh" 
                onClick={handleRefreshData}
              >
                Refresh
              </button>
            </div>
            
            {/* Show NWSDataViewer even in collapsed mode */}
            {showDataViewer && NWSDataViewerComponent && (
              <div className="collapsed-nws-viewer">
                <NWSDataViewerComponent />
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  if (performanceMode) {
    return (
      <div className="map-section performance-mode">
        <div id="map" className="performance-map">
          <p>Map disabled in performance mode</p>
        </div>
      </div>
    );
  }

  return (
    <div className="map-section">
      <div className="map-header">
        <h3> </h3>
        {lastUpdated && (
          <div className="mobile-timestamp">
            Last updated: {lastUpdated.toLocaleString()}
          </div>
        )}
      </div>
      
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
      
      {/* Render the legend below the map */}
      {renderLegend()}
    </div>
  );
}

export default MapSection;
