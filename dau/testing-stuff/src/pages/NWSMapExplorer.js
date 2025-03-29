// pages/NWSMapExplorer.js
import React, { useState, useEffect } from "react";
import MapSection from "../components/MapSection";
import NWSDataViewer from "../components/NWSDataViewer";
import { api } from "../services/api";

function NWSMapExplorer({ performanceMode }) {
    const [selectedView, setSelectedView] = useState('map'); // 'map', 'split', 'data'
    const [alertFilter, setAlertFilter] = useState('all');
    const [selectedAlert, setSelectedAlert] = useState(null);

    // State for the map features
    const [heatmapEnabled, setHeatmapEnabled] = useState(false);
    const [clusteringEnabled, setClusteringEnabled] = useState(false);
    const [alertsData, setAlertsData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchAlertData = async () => {
            try {
                setLoading(true);
                // In a real implementation, you would fetch from your API
                // For now we'll rely on the NWSDataViewer component's internal fetching
                setLoading(false);
            } catch (err) {
                console.error("Error fetching NWS data:", err);
                setError("Failed to load NWS data. Please try again.");
                setLoading(false);
            }
        };

        fetchAlertData();
    }, []);

    // Handle alert selection from the data viewer
    const handleAlertSelect = (alert) => {
        setSelectedAlert(alert);
        // If in data view, switch to split view to show the alert on map
        if (selectedView === 'data') {
            setSelectedView('split');
        }
    };

    // Handle filter change from the data viewer
    const handleFilterChange = (filterType) => {
        setAlertFilter(filterType);
        // This would then be passed to the map to filter displayed alerts
    };

    return (
        <div className="nws-map-explorer-page">
            <div className="view-controls">
                <button
                    className={`view-btn ${selectedView === 'map' ? 'active' : ''}`}
                    onClick={() => setSelectedView('map')}
                >
                    Map View
                </button>
                <button
                    className={`view-btn ${selectedView === 'split' ? 'active' : ''}`}
                    onClick={() => setSelectedView('split')}
                >
                    Split View
                </button>
                <button
                    className={`view-btn ${selectedView === 'data' ? 'active' : ''}`}
                    onClick={() => setSelectedView('data')}
                >
                    Data View
                </button>
            </div>

            <div className={`nws-map-content ${selectedView}`}>
                {/* Map Section - Always visible in 'map' and 'split' views */}
                {(selectedView === 'map' || selectedView === 'split') && (
                    <div className={`map-container ${selectedView === 'split' ? 'split' : 'full'}`}>
                        <MapSection
                            performanceMode={performanceMode}
                            heatmapEnabled={heatmapEnabled}
                            clusteringEnabled={clusteringEnabled}
                            alertFilter={alertFilter}
                            selectedAlert={selectedAlert}
                            fullScreen={selectedView === 'map'}
                        />

                        {selectedView === 'map' && (
                            <div className="map-controls">
                                <div className="map-control-panel">
                                    <h3>Map Settings</h3>
                                    <div className="map-options">
                                        <label>
                                            <input
                                                type="checkbox"
                                                checked={heatmapEnabled}
                                                onChange={(e) => setHeatmapEnabled(e.target.checked)}
                                            />
                                            Enable Heatmap
                                        </label>
                                        <label>
                                            <input
                                                type="checkbox"
                                                checked={clusteringEnabled}
                                                onChange={(e) => setClusteringEnabled(e.target.checked)}
                                            />
                                            Enable Clustering
                                        </label>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* NWS Data Viewer - Always visible in 'data' and 'split' views */}
                {(selectedView === 'data' || selectedView === 'split') && (
                    <div className={`data-container ${selectedView === 'split' ? 'split' : 'full'}`}>
                        <NWSDataViewer
                            onAlertSelect={handleAlertSelect}
                            onFilterChange={handleFilterChange}
                            selectedAlert={selectedAlert}
                        />
                    </div>
                )}
            </div>

            {/* Information panel at the bottom - always visible */}
            <div className="nws-info-panel">
                <h3>About NWS Data</h3>
                <p>
                    This page displays real-time National Weather Service (NWS) alerts and warnings.
                    The map visualization shows the geographical coverage of alerts, while the data view
                    provides detailed information about each alert.
                </p>
                <p>
                    <strong>Tips:</strong> Click on an alert in the data view to highlight it on the map.
                    Use the filter options to focus on specific types of weather events.
                </p>
            </div>
        </div>
    );
}

export default NWSMapExplorer;