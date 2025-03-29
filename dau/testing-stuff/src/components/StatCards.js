// components/StatCards.js
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

const StatCards = () => {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                setLoading(true);
                const data = await api.getPostVolumeMetrics();
                console.log("Metrics data:", data);
                setMetrics(data);
                setLoading(false);
            } catch (err) {
                console.error("Error fetching metrics:", err);
                setError("Failed to load metrics data");
                setLoading(false);
            }
        };

        fetchMetrics();
    }, []);

    if (loading) {
        return (
            <div className="metrics-loading">
                <p>Loading metrics data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="metrics-error">
                <p>{error}</p>
            </div>
        );
    }

    if (!metrics) {
        return (
            <div className="metrics-empty">
                <p>No metrics data available</p>
            </div>
        );
    }

    // Format numbers with commas
    const formatNumber = (num) => {
        return num.toLocaleString();
    };

    return (
        <div className="metrics-container">
            <div className="metrics-summary">
                <div className="metric-card">
                    <h3>Total Posts Processed</h3>
                    <div className="metric-value">{formatNumber(metrics.total_processed)}</div>
                </div>

                <div className="metric-card">
                    <h3>Disaster Posts</h3>
                    <div className="metric-value">{formatNumber(metrics.disaster_posts)}</div>
                    <div className="metric-percentage">{metrics.disaster_percentage}% of total</div>
                </div>

                <div className="metric-card highlight">
                    <h3>Last 24 Hours</h3>
                    <div className="metric-value">{formatNumber(metrics.last_24h.disaster_posts)}</div>
                    <div className="metric-percentage">{metrics.last_24h.disaster_percentage}% of recent</div>
                    <div className="metric-subtext">
                        out of {formatNumber(metrics.last_24h.total_processed)} total posts
                    </div>
                </div>

                <div className="metric-card">
                    <h3>Daily Disaster Ratio</h3>
                    <div className="metric-trend">
                        {metrics.last_24h.disaster_percentage > metrics.disaster_percentage ? (
                            <span className="trend-up">↑ {(metrics.last_24h.disaster_percentage - metrics.disaster_percentage).toFixed(1)}%</span>
                        ) : (
                            <span className="trend-down">↓ {(metrics.disaster_percentage - metrics.last_24h.disaster_percentage).toFixed(1)}%</span>
                        )}
                    </div>
                    <div className="metric-subtext">
                        compared to overall average
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StatCards;