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

// Super category mapping
const disasterCategoriesMapping = {
  fire: ["wild fire", "bush fire", "forest fire", "wildfire", "bushfire", "forestfire"],
  storm: ["storm", "blizzard", "cyclone", "dust storm", "hurricane", "tornado", "typhoon"],
  earthquake: ["earthquake"],
  tsunami: ["tsunami"],
  volcano: ["volcano"],
  flood: ["flood"],
  landslide: ["landslide", "avalanche"],
  other: ["haze", "meteor", "unknown"]
};

const Timechart = ({ selectedDisaster }) => {
  const [view, setView] = useState("weekly"); // Default to weekly, removing daily
  const [timeframeInDays, setTimeframeInDays] = useState(84); // 12 weeks by default
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Function to generate monthly labels from current month back 11 months
  const generateMonthlyLabels = () => {
    const labels = [];
    const currentDate = new Date();

    // Go back 11 months from current month
    for (let i = 11; i >= 0; i--) {
      const d = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
      labels.push(d.toISOString().substring(0, 7)); // Format as YYYY-MM for consistency
    }

    return labels;
  };

  // Utility function to normalize a month string to YYYY-MM format
  const normalizeMonthString = (monthStr) => {
    // Handle different possible formats
    if (monthStr.match(/^\d{4}-\d{2}$/)) {
      return monthStr; // Already in YYYY-MM format
    }

    try {
      const date = new Date(monthStr);
      return date.toISOString().substring(0, 7);
    } catch (e) {
      console.error("Failed to normalize month string:", monthStr);
      return monthStr;
    }
  };

  // Format month label for display
  const formatMonthLabel = (monthStr) => {
    try {
      // If it's in YYYY-MM format
      if (monthStr.match(/^\d{4}-\d{2}$/)) {
        const [year, month] = monthStr.split("-");
        const date = new Date(parseInt(year), parseInt(month) - 1);
        return date.toLocaleDateString("en-US", { year: "numeric", month: "short" });
      } else {
        // Try to parse it as a date string
        const date = new Date(monthStr);
        return date.toLocaleDateString("en-US", { year: "numeric", month: "short" });
      }
    } catch (e) {
      return monthStr; // Return as is if parsing fails
    }
  };

  // Get subcategories for selected super category
  const getSubcategoriesForSelectedDisaster = () => {
    if (selectedDisaster === 'all') {
      // For 'all', return all subcategories from all super categories
      return Object.values(disasterCategoriesMapping).flat();
    }

    // Return the subcategories for the selected super category
    return disasterCategoriesMapping[selectedDisaster] || [];
  };

  // Use useCallback to memoize the fetchTimelineData function
  const fetchTimelineData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      console.log("Fetching timeline data for disaster type:", selectedDisaster);

      // Get subcategories for the selected super category
      const subcategories = getSubcategoriesForSelectedDisaster();
      console.log("Subcategories to fetch:", subcategories);

      let combinedChartData = {
        labels: [],
        datasets: []
      };

      // If we're in monthly view, pre-generate the labels
      const monthlyLabels = view === "monthly" ? generateMonthlyLabels() : [];

      // For "all" category or a super category, we need to fetch data for each subcategory
      // We'll fetch them in parallel
      const fetchPromises = [];

      if (selectedDisaster === 'all') {
        // For "all", just make a single API call with "all"
        fetchPromises.push(api.getDisasterTimeline(view, timeframeInDays, 'all'));
      } else {
        // For a specific super category, fetch data for each subcategory
        subcategories.forEach(subcategory => {
          fetchPromises.push(api.getDisasterTimeline(view, timeframeInDays, subcategory));
        });
      }

      const results = await Promise.all(fetchPromises);

      // Process results
      let allLabels = new Set();
      const datasetsByCategory = {};

      results.forEach((data, index) => {
        if (!data || !data.labels || !data.datasets) {
          console.warn("Invalid data format received from API for subcategory:", index);
          return;
        }

        // Add labels to our set of all labels (for weekly view)
        if (view === "weekly") {
          data.labels.forEach(label => allLabels.add(label));
        }

        // Process each dataset in this result
        data.datasets.forEach(dataset => {
          // Store the dataset with its label as the key
          datasetsByCategory[dataset.label] = dataset.data.map((value, i) => ({
            label: data.labels[i],
            value
          }));
        });
      });

      // Prepare final datasets
      const finalDatasets = [];
      const colors = ["#36A2EB", "#FF6384", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40", "#8E44AD", "#1ABC9C"];
      let colorIndex = 0;

      // For weekly view, we need to sort the labels chronologically
      let finalLabels = [];
      if (view === "weekly") {
        finalLabels = Array.from(allLabels).sort();
      } else if (view === "monthly") {
        finalLabels = monthlyLabels;
      }

      // Create a dataset for each disaster category
      Object.entries(datasetsByCategory).forEach(([categoryName, dataPoints]) => {
        const color = colors[colorIndex % colors.length];
        colorIndex++;

        // Initialize an array of zeros for all labels
        const values = Array(finalLabels.length).fill(0);

        // Fill in the actual values where we have data
        dataPoints.forEach(point => {
          let labelIndex;

          if (view === "weekly") {
            labelIndex = finalLabels.indexOf(point.label);
          } else if (view === "monthly") {
            // For monthly, we need to normalize the date format first
            const normalizedPointLabel = normalizeMonthString(point.label);
            labelIndex = finalLabels.indexOf(normalizedPointLabel);
          }

          if (labelIndex !== -1) {
            values[labelIndex] = point.value;
          }
        });

        finalDatasets.push({
          label: capitalizeFirstLetter(categoryName),
          data: values,
          borderColor: color,
          backgroundColor: color + "80",
          fill: true
        });
      });

      // Format labels for display
      let displayLabels;
      if (view === "weekly") {
        displayLabels = finalLabels.map(label => formatDateLabel(label, "weekly"));
      } else if (view === "monthly") {
        displayLabels = finalLabels.map(label => formatMonthLabel(label));
      }

      setChartData({
        labels: displayLabels,
        datasets: finalDatasets
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
      if (viewType === "weekly") {
        // For weekly view, we use the date as the start of week
        const date = new Date(label);
        const endOfWeek = new Date(date);
        endOfWeek.setDate(date.getDate() + 6);

        return `${date.toLocaleDateString("en-US", { month: "short", day: "numeric" })} - ${endOfWeek.toLocaleDateString(
            "en-US",
            { month: "short", day: "numeric" }
        )}`;
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
    maintainAspectRatio: true,
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
          text: view === "weekly" ? "Week" : "Month",
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

          {/* Buttons to toggle between time views - removed daily */}
          <div className="view-toggle-buttons">
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