import React, { useState, useEffect, useRef, useCallback } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import api from "../services/api";

// Register Chart.js components
ChartJS.register(ArcElement, Tooltip, Legend);

// Disaster categories mapping for aggregating data
const disasterCategoriesMapping = {
  fire: ["wild_fire", "bush_fire", "forest_fire"],
  storm: ["storm", "blizzard", "cyclone", "dust_storm", "hurricane", "tornado", "typhoon"],
  earthquake: ["earthquake"],
  tsunami: ["tsunami"],
  volcano: ["volcano"],
  flood: ["flood"],
  landslide: ["landslide", "avalanche"],
  other: ["haze", "meteor", "unknown"]
};

// Super category display names (for better formatting)
const superCategoryNames = {
  fire: "Fire",
  storm: "Storm",
  earthquake: "Earthquake",
  tsunami: "Tsunami",
  volcano: "Volcano",
  flood: "Flood",
  landslide: "Landslide",
  other: "Other"
};

const DonutChart = () => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const chartRef = useRef(null);

  // Use useCallback to memoize the fetchDisasterDistribution function
  const fetchDisasterDistribution = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Use the api module to fetch distribution data
      const apiData = await api.getDisasterDistribution();

      if (!apiData || !apiData.data || !Array.isArray(apiData.data)) {
        throw new Error('Invalid data format received from API');
      }

      // Aggregate data by super category
      const superCategoryCounts = {};
      let totalCount = 0;

      // Initialize all super categories with 0 counts
      Object.keys(disasterCategoriesMapping).forEach(category => {
        superCategoryCounts[category] = 0;
      });

      // Process each data item
      apiData.data.forEach(item => {
        const type = item.type.toLowerCase();
        const count = item.count || 0;
        totalCount += count;

        // Find which super category this item belongs to
        let foundSuperCategory = false;
        for (const [superCategory, subcategories] of Object.entries(disasterCategoriesMapping)) {
          if (superCategory === type || subcategories.includes(type)) {
            superCategoryCounts[superCategory] += count;
            foundSuperCategory = true;
            break;
          }
        }

        // If no match, add to "other" category
        if (!foundSuperCategory) {
          superCategoryCounts.other += count;
        }
      });

      // Create the array of super categories with counts > 0
      const superCategoryData = Object.entries(superCategoryCounts)
          .filter(([_, count]) => count > 0)
          .map(([category, count]) => ({
            category,
            displayName: superCategoryNames[category] || capitalizeFirstLetter(category),
            count
          }))
          .sort((a, b) => b.count - a.count); // Sort by count (highest first)

      // Prepare chart data format
      const labels = superCategoryData.map(item => item.displayName);
      const dataValues = superCategoryData.map(item => item.count);

      // Define chart colors - match your theme
      const backgroundColors = [
        "#FF6384", // Red
        "#36A2EB", // Blue
        "#FFCE56", // Yellow
        "#4BC0C0", // Teal
        "#9966FF", // Purple
        "#FF9F40", // Orange
        "#FF5733", // Bright Orange
        "#C9CBCF", // Gray
      ];

      // Format for Chart.js
      const formattedData = {
        labels: labels,
        datasets: [
          {
            label: "Disaster Occurrences",
            data: dataValues,
            backgroundColor: backgroundColors.slice(0, labels.length),
            borderWidth: 0,
            hoverOffset: 10,
          },
        ],
      };

      setChartData({
        chartJsData: formattedData,
        superCategoryData: superCategoryData,
        totalCount: totalCount
      });

      setLoading(false);
    } catch (err) {
      console.error("Error fetching disaster distribution:", err);
      setError(err.message);
      setLoading(false);
    }
  }, []);

  // Fetch data when component mounts
  useEffect(() => {
    fetchDisasterDistribution();
  }, [fetchDisasterDistribution]);

  const capitalizeFirstLetter = (string) => {
    if (!string) return "";
    return string.charAt(0).toUpperCase() + string.slice(1);
  };

  // Chart options
  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        position: "bottom",
        labels: {
          color: "#ffffff", // Match your theme
          font: {
            size: 12
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        titleColor: '#ffffff',
        bodyColor: '#ffffff',
        borderColor: 'rgba(255, 255, 255, 0.3)',
        borderWidth: 1,
      }
    }
    // Keep hover effects but no click handler
  };

  if (loading && !chartData) {
    return (
        <div className="help-section">
          <h2 className="heading">Natural Disasters Overview</h2>
          <div className="Donutchart-section">
            <div className="loading-indicator">Loading disaster data...</div>
          </div>
        </div>
    );
  }

  if (error && !chartData) {
    return (
        <div className="help-section">
          <h2 className="heading">Natural Disasters Overview</h2>
          <div className="Donutchart-section">
            <div className="error-message">Error: {error}</div>
            <button onClick={fetchDisasterDistribution} className="retry-button">Retry</button>
          </div>
        </div>
    );
  }

  if (!chartData) return null;

  return (
      <div className="help-section">
        <h2 className="heading">Natural Disasters Overview</h2>
        <div className="Donutchart-section" ref={chartRef}>
          {/* Donut Chart */}
          <div className="donutchart-container">
            <Doughnut data={chartData.chartJsData} options={options} />
          </div>

          {/* Overview Section - Always shows super categories */}
          <div className="overview-section">
            <h3>Disaster Categories Overview</h3>
            <ul>
              {chartData.superCategoryData.map(item => (
                  <li key={item.category}>
                <span className="category">
                  {item.displayName}
                </span>
                    <span className="occurrence">{item.count}</span>
                  </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
  );
};

export default DonutChart;