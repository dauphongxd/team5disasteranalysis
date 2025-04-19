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

// Super category mapping with exact mapping as specified
// Removed tsunami from mapping
const disasterCategoriesMapping = {
  fire: ["wild_fire", "bush_fire", "forest_fire"],
  storm: ["storm", "blizzard", "cyclone", "dust_storm", "hurricane", "tornado", "typhoon"],
  earthquake: ["earthquake"],
  volcano: ["volcano"],
  flood: ["flood"],
  landslide: ["landslide", "avalanche"],
  other: ["haze", "meteor", "unknown"]
};

// Super category display names
// Removed tsunami
const superCategoryNames = {
  fire: "Fire",
  storm: "Storm",
  earthquake: "Earthquake",
  volcano: "Volcano",
  flood: "Flood",
  landslide: "Landslide",
  other: "Other"
};

// Define the fixed order of categories to ensure consistent display
// Removed tsunami
const categoryOrder = [
  "fire",
  "storm",
  "earthquake",
  "volcano",
  "flood",
  "landslide",
  "other"
];

// Consistent color mapping for each category
// Removed tsunami
const categoryColors = {
  fire: "#FF6384",     // Red
  storm: "#36A2EB",    // Blue
  earthquake: "#FFCE56", // Yellow
  volcano: "#9966FF",  // Purple
  flood: "#4BC0C0",    // Teal
  landslide: "#FF9F40", // Orange
  other: "#C9CBCF"     // Gray
};

// Helper function to normalize disaster types (handles both underscore and space formats)
const normalizeDisasterType = (type) => {
  if (!type) return '';
  return String(type).toLowerCase();
};

const Timechart = ({ selectedDisaster }) => {
  const [view, setView] = useState("weekly"); // Use API's interval property: "daily", "weekly", "monthly"
  const [timeframeInDays, setTimeframeInDays] = useState(35); // 5 weeks by default (changed from 84)
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Generate exactly 5 weeks of labels ending with the current week
  const generateExact5WeekLabels = () => {
    const labels = [];
    const today = new Date();

    // Find the start of the current week (Sunday)
    const currentWeekStart = new Date(today);
    const dayOfWeek = today.getDay(); // 0 is Sunday, 1 is Monday, etc.
    currentWeekStart.setDate(today.getDate() - dayOfWeek); // Go back to Sunday

    // Set time to 00:00:00 for consistent comparison
    currentWeekStart.setHours(0, 0, 0, 0);

    // Generate 5 weeks of labels, starting from 4 weeks ago
    for (let i = 4; i >= 0; i--) {
      const weekStart = new Date(currentWeekStart);
      weekStart.setDate(currentWeekStart.getDate() - (i * 7));

      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);

      // Format as ISO string for API compatibility
      labels.push(weekStart.toISOString().split('T')[0]);
    }

    return labels;
  };

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

  // Helper function to get super category for a disaster type
  const getSuperCategoryForType = (disasterType) => {
    if (!disasterType) return 'other';

    // Skip tsunami data
    if (disasterType.toLowerCase() === 'tsunami') {
      return null; // Return null to exclude from processing
    }

    // Normalize the disaster type
    const normalizedType = normalizeDisasterType(disasterType);

    // Check if the type is a super category itself
    if (Object.keys(disasterCategoriesMapping).includes(normalizedType)) {
      return normalizedType;
    }

    // Check each super category to see if it includes this type
    for (const [superCategory, subTypes] of Object.entries(disasterCategoriesMapping)) {
      for (const subType of subTypes) {
        const normalizedSubType = normalizeDisasterType(subType);

        // Check for exact match or match after replacing underscores with spaces
        if (normalizedType === normalizedSubType ||
            normalizedType === normalizedSubType.replace(/_/g, ' ') ||
            normalizedType.replace(/_/g, ' ') === normalizedSubType) {
          return superCategory;
        }
      }
    }

    return 'other'; // Default to other if no match
  };

  // Use useCallback to memoize the fetchTimelineData function
  const fetchTimelineData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      console.log("Fetching timeline data for disaster type:", selectedDisaster);

      // Generate the exact 5 week labels if we're in weekly view
      const weeklyLabels = view === "weekly" ? generateExact5WeekLabels() : [];

      // If we're in monthly view, pre-generate the labels
      const monthlyLabels = view === "monthly" ? generateMonthlyLabels() : [];

      // Use the api module to fetch all disaster data in one call
      const data = await api.getDisasterTimeline(view, timeframeInDays, 'all');

      if (!data || !data.labels || !data.datasets) {
        throw new Error('Invalid data format received from API');
      }

      // The final datasets we'll display
      let finalDatasets = [];

      // Process all labels
      let allLabels;

      // Choose the appropriate labels based on view
      if (view === "weekly") {
        allLabels = weeklyLabels;
      } else if (view === "monthly") {
        allLabels = monthlyLabels;
      } else {
        allLabels = data.labels;
      }

      if (selectedDisaster === 'all') {
        // When "all" is selected, we want to show super categories

        // First, aggregate data by super category
        const superCategoryData = {};

        // Initialize each super category with zeros
        categoryOrder.forEach(category => {
          superCategoryData[category] = Array(allLabels.length).fill(0);
        });

        // Go through each dataset and add its values to the appropriate super category
        data.datasets.forEach(dataset => {
          const disasterType = dataset.label.toLowerCase();

          // Skip tsunami data
          if (disasterType === 'tsunami') {
            return;
          }

          const superCategory = getSuperCategoryForType(disasterType);

          // Skip if superCategory is null (for tsunami)
          if (superCategory === null) {
            return;
          }

          // Map API data to our week labels
          dataset.data.forEach((value, i) => {
            if (i >= dataset.data.length) return;

            const apiLabel = data.labels[i];
            // Find the matching week in our generated labels
            let labelIndex = -1;

            if (view === "weekly") {
              // For weekly, find the closest match by parsing dates
              const apiDate = new Date(apiLabel);

              // Find the closest week
              for (let j = 0; j < allLabels.length; j++) {
                const weekStart = new Date(allLabels[j]);
                const weekEnd = new Date(weekStart);
                weekEnd.setDate(weekStart.getDate() + 6);

                if (apiDate >= weekStart && apiDate <= weekEnd) {
                  labelIndex = j;
                  break;
                }
              }
            } else if (view === "monthly") {
              const normalizedLabel = normalizeMonthString(apiLabel);
              labelIndex = allLabels.indexOf(normalizedLabel);
            } else {
              // For daily, use direct index if available
              labelIndex = allLabels.indexOf(apiLabel);
            }

            if (labelIndex !== -1) {
              superCategoryData[superCategory][labelIndex] += value;
            }
          });
        });

        // Create a dataset for each super category in the predefined order
        // Always include all categories, even if they have all zeros
        categoryOrder.forEach((category, index) => {
          const color = categoryColors[category] || Object.values(categoryColors)[index % Object.values(categoryColors).length];

          finalDatasets.push({
            label: superCategoryNames[category] || capitalizeFirstLetter(category),
            data: superCategoryData[category] || Array(allLabels.length).fill(0),
            borderColor: color,
            backgroundColor: color + "80", // Add transparency
            fill: true
          });
        });
      } else {
        // Special case: if tsunami is selected, skip rendering
        if (selectedDisaster === 'tsunami') {
          setChartData({
            labels: allLabels.map(label => formatDateLabel(label, view)),
            datasets: []
          });
          setLoading(false);
          return;
        }

        // When a specific super category is selected, show all its subcategories
        const subcategories = disasterCategoriesMapping[selectedDisaster] || [];
        const foundSubcategories = new Set();

        // First, add subcategories that exist in the data
        data.datasets.forEach((dataset, index) => {
          const disasterType = dataset.label.toLowerCase();

          // Skip tsunami data
          if (disasterType === 'tsunami') {
            return;
          }

          const superCategory = getSuperCategoryForType(disasterType);

          if (superCategory === selectedDisaster) {
            foundSubcategories.add(disasterType);

            // Map the data to our labels
            const mappedData = Array(allLabels.length).fill(0);

            dataset.data.forEach((value, i) => {
              if (i >= dataset.data.length) return;

              const apiLabel = data.labels[i];
              // Find the matching week in our generated labels
              let labelIndex = -1;

              if (view === "weekly") {
                // For weekly, find the closest match by parsing dates
                const apiDate = new Date(apiLabel);

                // Find the closest week
                for (let j = 0; j < allLabels.length; j++) {
                  const weekStart = new Date(allLabels[j]);
                  const weekEnd = new Date(weekStart);
                  weekEnd.setDate(weekStart.getDate() + 6);

                  if (apiDate >= weekStart && apiDate <= weekEnd) {
                    labelIndex = j;
                    break;
                  }
                }
              } else if (view === "monthly") {
                const normalizedLabel = normalizeMonthString(apiLabel);
                labelIndex = allLabels.indexOf(normalizedLabel);
              } else {
                // For daily, use direct index if available
                labelIndex = allLabels.indexOf(apiLabel);
              }

              if (labelIndex !== -1) {
                mappedData[labelIndex] = value;
              }
            });

            const colorIndex = index % Object.values(categoryColors).length;
            const color = Object.values(categoryColors)[colorIndex];

            finalDatasets.push({
              label: capitalizeFirstLetter(disasterType.replace('_', ' ')),
              data: mappedData,
              borderColor: color,
              backgroundColor: color + "80", // Add transparency
              fill: true
            });
          }
        });

        // Then add empty datasets for subcategories that don't exist in the data
        let extraColorIndex = finalDatasets.length;
        subcategories.forEach(subcategory => {
          if (!foundSubcategories.has(subcategory)) {
            const colorIndex = extraColorIndex % Object.values(categoryColors).length;
            const color = Object.values(categoryColors)[colorIndex];

            finalDatasets.push({
              label: capitalizeFirstLetter(subcategory.replace('_', ' ')),
              data: Array(allLabels.length).fill(0),
              borderColor: color,
              backgroundColor: color + "80", // Add transparency
              fill: true
            });
            extraColorIndex++;
          }
        });
      }

      // Format the labels for display
      const formattedLabels = allLabels.map(label => formatDateLabel(label, view));

      setChartData({
        labels: formattedLabels,
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
      if (viewType === "daily") {
        // For daily view, format as "MMM DD"
        const date = new Date(label);
        return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      } else if (viewType === "weekly") {
        // For weekly view, we use the date as the start of week and calculate end of week
        const date = new Date(label);
        const endOfWeek = new Date(date);
        endOfWeek.setDate(date.getDate() + 6);

        return `${date.toLocaleDateString("en-US", { month: "short", day: "numeric" })} - ${endOfWeek.toLocaleDateString(
            "en-US",
            { month: "short", day: "numeric" }
        )}`;
      } else if (viewType === "monthly") {
        // For monthly view, format as "MMM YYYY"
        if (label.match(/^\d{4}-\d{2}$/)) {
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

  // Chart options configuration - keep original design with your label
  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "top",
      },
      title: {
        display: true,
        text: selectedDisaster === 'all'
            ? `${capitalizeFirstLetter(view)} Disaster Trends by Category`
            : `${capitalizeFirstLetter(view)} ${superCategoryNames[selectedDisaster] || capitalizeFirstLetter(selectedDisaster)} Disaster Trends`,
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
          text: 'Occurrence', // Using your label
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
        setTimeframeInDays(35); // Last 5 weeks (changed from 84)
        break;
      case "monthly":
        setTimeframeInDays(365); // Last 12 months
        break;
      default:
        setTimeframeInDays(35); // Default to 5 weeks
    }
    setView(newView);
  };

  // If tsunami is selected, don't show the component
  if (selectedDisaster === 'tsunami') {
    return (
        <div className="help-section">
          <h2>Disaster Timeline</h2>
          <div className="chart-section">
            <div className="no-data-message">No timeline data available for this category.</div>
          </div>
        </div>
    );
  }

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
            {/*<button*/}
            {/*    className={`toggle-button ${view === "daily" ? "active" : ""}`}*/}
            {/*    onClick={() => handleViewToggle("daily")}*/}
            {/*>*/}
            {/*  Daily*/}
            {/*</button>*/}
            <button
                className={`sc-button ${view === "weekly" ? "active" : ""}`}
                onClick={() => handleViewToggle("weekly")}
            >
              Weekly
            </button>
            <button
                className={`sc-button ${view === "monthly" ? "active" : ""}`}
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