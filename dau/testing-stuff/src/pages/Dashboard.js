// pages/Dashboard.js
import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import MapSection from "../components/MapSection";
import TweetFeed from "../components/TweetFeed";
import Timechart from "../components/Timechart";
import { api } from "../services/api";

function Dashboard({ disasterData, selectedDisaster, setSelectedDisaster }) {
    const [timelineData, setTimelineData] = useState(null);
    const [timelineLoading, setTimelineLoading] = useState(true);
    const [timelineError, setTimelineError] = useState(null);

    // Fetch timeline data from API
    useEffect(() => {
        const fetchTimelineData = async () => {
            try {
                setTimelineLoading(true);
                const data = await api.getDisasterTimeline('daily', 30, selectedDisaster === 'all' ? null : selectedDisaster);
                console.log("Timeline data loaded:", data);
                setTimelineData(data);
                setTimelineLoading(false);
            } catch (err) {
                console.error("Error fetching timeline data:", err);
                setTimelineError("Failed to load timeline data");
                setTimelineLoading(false);
            }
        };

        fetchTimelineData();
    }, [selectedDisaster]);

    return (
        <div className="dashboard-page">
            {/* Main content with map and tweets */}
            <div className="main-content">
                <div className="dashboard-map-container" style={{ flex: '0 0 70%' }}>
                    <div className="map-header">
                        <h3>Real-time Disaster Map</h3>
                    </div>
                    <MapSection showLegend={false} />
                    <Link to="/map" className="view-more-link">
                        View full map explorer →
                    </Link>
                </div>

                <div className="dashboard-tweets-container" style={{ flex: '0 0 30%' }}>
                    <div className="map-header">
                        <h3>Disaster Tweets</h3>
                    </div>
                    <TweetFeed limitTweets={20} />
                    <Link to="/tweets" className="view-more-link">
                        View all disaster tweets →
                    </Link>
                </div>
            </div>

            {/* Summary chart */}
            <div className="dashboard-chart">
                {timelineLoading ? (
                    <div className="loading-chart">Loading timeline data...</div>
                ) : timelineError ? (
                    <div className="error-chart">{timelineError}</div>
                ) : (
                    <Timechart
                        disasterData={disasterData}
                        selectedDisaster={selectedDisaster}
                        apiData={timelineData}
                    />
                )}
                <Link to="/analytics" className="view-more-link">
                    View detailed analytics →
                </Link>
            </div>
        </div>
    );
}

export default Dashboard;