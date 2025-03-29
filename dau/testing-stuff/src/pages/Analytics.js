// pages/Analytics.js
import React, { useState, useEffect } from "react";
import Timechart from "../components/Timechart";
import { api } from "../services/api";

// Import your components
import DisasterCategoriesWithChart from "../components/Donutchart";
import StatCards from "../components/StatCards";

function Analytics({ disasterData, selectedDisaster, setSelectedDisaster }) {
    const [timelineData, setTimelineData] = useState(null);
    const [distributionData, setDistributionData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [timeInterval, setTimeInterval] = useState('daily');
    const [timeRange, setTimeRange] = useState(30); // days

    useEffect(() => {
        const fetchAnalyticsData = async () => {
            try {
                setLoading(true);

                // Fetch analytics data (timeline and distribution)
                const [timeline, distribution] = await Promise.all([
                    api.getDisasterTimeline(timeInterval, timeRange, selectedDisaster === 'all' ? null : selectedDisaster)
                        .catch(err => {
                            console.error("Timeline fetch error:", err);
                            return null;
                        }),
                    api.getDisasterDistribution()
                        .catch(err => {
                            console.error("Distribution fetch error:", err);
                            return null;
                        })
                ]);

                setTimelineData(timeline);
                setDistributionData(distribution);
                setLoading(false);
            } catch (err) {
                console.error("Error fetching analytics data:", err);
                setError("Failed to load analytics data. Please try again.");
                setLoading(false);
            }
        };

        fetchAnalyticsData();
    }, [selectedDisaster, timeInterval, timeRange]);

    return (
        <div className="analytics-page">
            <h2>Disaster Analytics Dashboard</h2>

            {/* Time interval controls - no disaster type filters */}
            <div className="filters-container">
                <div className="timeline-controls">
                    <div className="control-group">
                        <label>Time Interval:</label>
                        <select
                            value={timeInterval}
                            onChange={(e) => setTimeInterval(e.target.value)}
                        >
                            <option value="daily">Daily</option>
                            <option value="weekly">Weekly</option>
                            <option value="monthly">Monthly</option>
                        </select>
                    </div>
                    <div className="control-group">
                        <label>Time Range:</label>
                        <select
                            value={timeRange}
                            onChange={(e) => setTimeRange(parseInt(e.target.value))}
                        >
                            <option value="7">Last 7 days</option>
                            <option value="30">Last 30 days</option>
                            <option value="90">Last 90 days</option>
                            <option value="180">Last 6 months</option>
                            <option value="365">Last year</option>
                        </select>
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="loading-container">
                    <p>Loading analytics data...</p>
                </div>
            ) : error ? (
                <div className="error-container">
                    <p>{error}</p>
                    <button onClick={() => window.location.reload()}>Retry</button>
                </div>
            ) : (
                <div className="analytics-content">
                    {/* Post Volume Metrics - Stat Cards */}
                    <section className="analytics-section">
                        <h3>Post Volume Metrics</h3>
                        <StatCards />
                    </section>

                    {/* Main charts */}
                    <div className="charts-grid">
                        <div className="chart-container large">
                            <h3>Disaster Timeline</h3>
                            {/* Use the API-loaded timeline data if available */}
                            {timelineData ? (
                                <div className="api-timeline-chart">
                                    <Timechart
                                        apiData={timelineData}
                                        selectedDisaster={selectedDisaster}
                                    />
                                </div>
                            ) : (
                                // Fall back to the existing component using the props data
                                <Timechart
                                    disasterData={disasterData}
                                    selectedDisaster={selectedDisaster}
                                />
                            )}
                        </div>

                        <div className="chart-container medium">
                            <h3>Disaster Type Distribution</h3>
                            {distributionData ? (
                                <div className="api-distribution-chart">
                                    <DisasterCategoriesWithChart
                                        distributionData={distributionData}
                                    />
                                </div>
                            ) : (
                                <DisasterCategoriesWithChart />
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Analytics;