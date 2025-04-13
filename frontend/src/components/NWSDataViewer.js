import React, { useState, useEffect } from 'react';

function NWSDataViewer() {
  const [apiData, setApiData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filteredType, setFilteredType] = useState('all');
  const [eventTypes, setEventTypes] = useState([]);
  const [expandedItems, setExpandedItems] = useState([]);
  const [alertStats, setAlertStats] = useState({
    total: 0,
    hasGeometry: 0,
    noGeometry: 0,
    polygons: 0,
    points: 0,
    nullGeometry: 0,
    otherGeometry: 0
  });

  useEffect(() => {
    fetchNWSData();
  }, []);

  const fetchNWSData = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        "https://api.weather.gov/alerts/active?status=actual&message_type=alert"
      );
      
      if (!response.ok) {
        throw new Error(`NWS API returned ${response.status}`);
      }
      
      const data = await response.json();
      setApiData(data);
      
      // Extract unique event types
      const types = new Set();
      data.features.forEach(feature => {
        if (feature.properties && feature.properties.event) {
          types.add(feature.properties.event);
        }
      });
      setEventTypes(Array.from(types).sort());
      
      // Calculate alert statistics
      const stats = {
        total: data.features.length,
        hasGeometry: 0,
        noGeometry: 0,
        polygons: 0,
        points: 0,
        nullGeometry: 0,
        otherGeometry: 0
      };
      
      data.features.forEach(alert => {
        if (!alert.geometry) {
          stats.nullGeometry++;
          stats.noGeometry++;
        } else if (!alert.geometry.coordinates) {
          stats.noGeometry++;
        } else {
          stats.hasGeometry++;
          if (alert.geometry.type === 'Polygon') {
            stats.polygons++;
          } else if (alert.geometry.type === 'Point') {
            stats.points++;
          } else {
            stats.otherGeometry++;
          }
        }
      });
      
      setAlertStats(stats);
      setLoading(false);
    } catch (err) {
      console.error("Error fetching NWS data:", err);
      setError("Failed to load NWS API data. Please try again later.");
      setLoading(false);
    }
  };

  const toggleExpand = (id) => {
    setExpandedItems(prev => {
      if (prev.includes(id)) {
        return prev.filter(item => item !== id);
      } else {
        return [...prev, id];
      }
    });
  };

  if (loading) {
    return <div className="nws-data-viewer loading">Loading NWS API data...</div>;
  }

  if (error) {
    return (
      <div className="nws-data-viewer error">
        <p>{error}</p>
        <button onClick={fetchNWSData} className="retry-button">Retry</button>
      </div>
    );
  }

  if (!apiData || !apiData.features || apiData.features.length === 0) {
    return <div className="nws-data-viewer empty">No NWS alert data available</div>;
  }

  const filteredAlerts = filteredType === 'all' 
    ? apiData.features 
    : apiData.features.filter(feature => 
        feature.properties && feature.properties.event === filteredType
      );

  return (
    <div className="nws-data-viewer">
      <div className="nws-viewer-header">
        <h2>NWS API Data Explorer</h2>
        <div className="nws-viewer-controls">
          <button onClick={fetchNWSData} className="refresh-button">Refresh Data</button>
          <div className="filter-control">
            <label htmlFor="event-type-filter">Filter by Event Type: </label>
            <select 
              id="event-type-filter" 
              value={filteredType} 
              onChange={(e) => setFilteredType(e.target.value)}
            >
              <option value="all">All Events ({apiData.features.length})</option>
              {eventTypes.map(type => (
                <option key={type} value={type}>
                  {type} ({apiData.features.filter(f => f.properties.event === type).length})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="nws-data-summary">
        <p>
          <strong>Total Alerts:</strong> {apiData.features.length}<br />
          <strong>Event Types:</strong> {eventTypes.length}<br />
          <strong>Last Updated:</strong> {new Date(apiData.updated).toLocaleString()}
        </p>
      </div>
      
      <div className="nws-data-stats">
        <h3>Alert Geometry Statistics</h3>
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-label">Total Alerts:</span>
            <span className="stat-value">{alertStats.total}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Has Valid Geometry:</span>
            <span className="stat-value">{alertStats.hasGeometry}</span>
            <span className="stat-percent">({Math.round(alertStats.hasGeometry / alertStats.total * 100)}%)</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Missing Geometry:</span>
            <span className="stat-value">{alertStats.noGeometry}</span>
            <span className="stat-percent">({Math.round(alertStats.noGeometry / alertStats.total * 100)}%)</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Polygon Geometries:</span>
            <span className="stat-value">{alertStats.polygons}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Point Geometries:</span>
            <span className="stat-value">{alertStats.points}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Null Geometries:</span>
            <span className="stat-value">{alertStats.nullGeometry}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Other Geometry Types:</span>
            <span className="stat-value">{alertStats.otherGeometry}</span>
          </div>
        </div>
        <div className="stats-note">
          <p><strong>Note:</strong> Only alerts with valid geometry data (coordinates) can be displayed on the map. 
          This explains why you may see {alertStats.total} alerts in the count but only {alertStats.hasGeometry} visible on the map.</p>
        </div>
      </div>

      <div className="nws-alerts-list">
        {filteredAlerts.map((alert, index) => {
          const id = alert.id || `alert-${index}`;
          const properties = alert.properties || {};
          const isExpanded = expandedItems.includes(id);
          
          return (
            <div key={id} className="nws-alert-item">
              <div 
                className="nws-alert-header" 
                onClick={() => toggleExpand(id)}
              >
                <h3>{properties.event || 'Unknown Event'}</h3>
                <div className="alert-meta">
                  <span className="severity">{properties.severity || 'Unknown'}</span>
                  <span className="geometry-indicator" title="Whether this alert has map coordinates">
                    {alert.geometry && alert.geometry.coordinates ? '📍' : '❌'}
                  </span>
                  <span className="arrow">{isExpanded ? '▼' : '►'}</span>
                </div>
              </div>
              
              {isExpanded && (
                <div className="nws-alert-details">
                  <table>
                    <tbody>
                      <tr>
                        <th>Headline</th>
                        <td>{properties.headline || 'N/A'}</td>
                      </tr>
                      <tr>
                        <th>Area</th>
                        <td>{properties.areaDesc || 'N/A'}</td>
                      </tr>
                      <tr>
                        <th>Severity</th>
                        <td>{properties.severity || 'N/A'}</td>
                      </tr>
                      <tr>
                        <th>Certainty</th>
                        <td>{properties.certainty || 'N/A'}</td>
                      </tr>
                      <tr>
                        <th>Urgency</th>
                        <td>{properties.urgency || 'N/A'}</td>
                      </tr>
                      <tr>
                        <th>Effective</th>
                        <td>{properties.effective ? new Date(properties.effective).toLocaleString() : 'N/A'}</td>
                      </tr>
                      <tr>
                        <th>Expires</th>
                        <td>{properties.expires ? new Date(properties.expires).toLocaleString() : 'N/A'}</td>
                      </tr>
                      <tr>
                        <th>Description</th>
                        <td>
                          <div className="description-text">
                            {properties.description || 'N/A'}
                          </div>
                        </td>
                      </tr>
                      <tr>
                        <th>Categories</th>
                        <td>{properties.category || 'N/A'}</td>
                      </tr>
                      <tr>
                        <th>Has Geometry</th>
                        <td>{alert.geometry ? (alert.geometry.coordinates ? 'Yes (mappable)' : 'Yes (but no coordinates)') : 'No'}</td>
                      </tr>
                      {alert.geometry && (
                        <tr>
                          <th>Geometry Type</th>
                          <td>{alert.geometry.type || 'N/A'}</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default NWSDataViewer; 