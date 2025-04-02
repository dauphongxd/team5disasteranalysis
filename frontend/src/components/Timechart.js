import React, { useState, useEffect, useCallback } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import api from "../services/api";

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

const Timechart = ({ selectedDisaster }) => {
  const [view, setView] = useState("weekly"); // Use API's interval property: "daily", "weekly", "monthly"
  const [timeframeInDays, setTimeframeInDays] = useState(84); // 12 weeks by default
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Use useCallback to memoize the fetchTimelineData function
  const fetchTimelineData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Use the api module to fetch timeline data
      const data = await api.getDisasterTimeline(view, timeframeInDays, selectedDisaster);

      if (!data || !data.labels || !data.datasets) {
        throw new Error('Invalid data format received from API');
      }

      // Format dates based on the view
      const formattedLabels = data.labels.map(label => formatDateLabel(label, view));

      // Apply consistent colors for different disaster types
      const formattedDatasets = data.datasets.map((dataset, index) => {
        const colors = ["#36A2EB", "#FF6384", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40", "#8E44AD", "#1ABC9C"];
        return {
          label: capitalizeFirstLetter(dataset.label), // Format the label
          data: dataset.data,
          borderColor: colors[index % colors.length],
          backgroundColor: colors[index % colors.length] + "80", // Add transparency
          fill: true,
        };
      });

      setChartData({
        labels: formattedLabels,
        datasets: formattedDatasets,
      });

      setLoading(false);
    } catch (err) {
      console.error("Error fetching timeline data:", err);
      setError(err.message);
      setLoading(false);
    }
  }, [selectedDisaster, view, timeframeInDays]);

  // Fetch data when component mounts or when dependencies change
  useEffect(() => {
    fetchTimelineData();
  }, [fetchTimelineData]);

  // Helper function to format date labels based on current view
  const formatDateLabel = (label, viewType) => {
    try {
      if (viewType === "daily") {
        // For daily view, format as "MMM DD"
        const date = new Date(label);
        return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      } else if (viewType === "weekly") {
        // For weekly view, we use the date as the start of week
        const date = new Date(label);
        const endOfWeek = new Date(date);
        endOfWeek.setDate(date.getDate() + 6);

        return `${date.toLocaleDateString("en-US", { month: "short", day: "numeric" })} - ${endOfWeek.toLocaleDateString(
            "en-US",
            { month: "short", day: "numeric" }
        )}`;
      } else if (viewType === "monthly") {
        // For monthly view, format as "MMM YYYY"
        if (label.includes('-')) {
          // If in YYYY-MM format
          const [year, month] = label.split("-");
          const date = new Date(parseInt(year), parseInt(month) - 1);
          return date.toLocaleDateString("en-US", { year: "numeric", month: "short" });
        } else {
          // Just use as is
          return label;
        }
      }
      return label; // Return original label if parsing fails
    } catch (e) {
      console.error("Error formatting date label:", e);
      return label;
    }
  };

  const capitalizeFirstLetter = (string) => {
    if (!string) return "";
    return string.charAt(0).toUpperCase() + string.slice(1);
  };

  // Chart options configuration
  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "top",
      },
      title: {
        display: true,
        text: `${capitalizeFirstLetter(view)} Disaster Trends`,
        color: "#ffffff", // Match your theme
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        titleColor: '#ffffff',
        bodyColor: '#ffffff',
        borderColor: 'rgba(255, 255, 255, 0.3)',
        borderWidth: 1,
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Number of Events',
          color: "#ffffff", // Match your theme
        },
        ticks: {
          color: "#ffffff", // Match your theme
        },
        grid: {
          color: "rgba(255, 255, 255, 0.1)", // Subtle grid lines
        }
      },
      x: {
        title: {
          display: true,
          text: view === "daily" ? "Date" : view === "weekly" ? "Week" : "Month",
          color: "#ffffff", // Match your theme
        },
        ticks: {
          color: "#ffffff", // Match your theme
        },
        grid: {
          color: "rgba(255, 255, 255, 0.1)", // Subtle grid lines
        }
      }
    },
  };

  // Toggle between different time views
  const handleViewToggle = (newView) => {
    // Update timeframe appropriately with the new view
    switch (newView) {
      case "daily":
        setTimeframeInDays(30); // Last 30 days
        break;
      case "weekly":
        setTimeframeInDays(84); // Last 12 weeks
        break;
      case "monthly":
        setTimeframeInDays(365); // Last 12 months
        break;
      default:
        setTimeframeInDays(84);
    }
    setView(newView);
  };

  if (loading && !chartData) {
    return (
        <div className="help-section">
          <h2>Disaster Timeline</h2>
          <div className="chart-section">
            <div className="loading-indicator">Loading timeline data...</div>
          </div>
        </div>
    );
  }

  if (error && !chartData) {
    return (
        <div className="help-section">
          <h2>Disaster Timeline</h2>
          <div className="chart-section">
            <div className="error-message">Error: {error}</div>
            <button onClick={fetchTimelineData} className="retry-button">Retry</button>
          </div>
        </div>
    );
  }

  return (
      <div className="help-section">
        <h2>Disaster Timeline</h2>
        <div className="chart-section">
          {/* Line Chart */}
          {chartData && <Line data={chartData} options={options} />}

          {/* Buttons to toggle between time views */}
          <div className="view-toggle-buttons">
            <button
                className={`toggle-button ${view === "daily" ? "active" : ""}`}
                onClick={() => handleViewToggle("daily")}
            >
              Daily
            </button>
            <button
                className={`toggle-button ${view === "weekly" ? "active" : ""}`}
                onClick={() => handleViewToggle("weekly")}
            >
              Weekly
            </button>
            <button
                className={`toggle-button ${view === "monthly" ? "active" : ""}`}
                onClick={() => handleViewToggle("monthly")}
            >
              Monthly
            </button>
          </div>
        </div>
      </div>
  );
};

export default Timechart;