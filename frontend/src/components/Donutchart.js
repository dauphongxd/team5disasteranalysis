import React, { useState, useEffect, useRef, useCallback } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import api from "../services/api";

// Register Chart.js components
ChartJS.register(ArcElement, Tooltip, Legend);

// Disaster categories mapping for filtering
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

const DonutChart = ({ selectedDisaster }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const chartRef = useRef(null); // Reference for the chart container

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

      // Filter data based on selected disaster if needed
      let filteredData = apiData.data;

      if (selectedDisaster && selectedDisaster !== 'all') {
        // If category selection is active, filter to just relevant subcategories
        filteredData = apiData.data.filter(item => {
          const type = item.type.toLowerCase();
          return isMatchingCategory(type, selectedDisaster);
        });
      }

      // Sort by count for consistent ordering
      filteredData.sort((a, b) => b.count - a.count);

      // Prepare chart data format
      const labels = filteredData.map(item => capitalizeFirstLetter(item.type));
      const dataValues = filteredData.map(item => item.count);

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
        originalData: filteredData,
        totalCount: apiData.total_count || filteredData.reduce((sum, item) => sum + item.count, 0)
      });

      setLoading(false);
    } catch (err) {
      console.error("Error fetching disaster distribution:", err);
      setError(err.message);
      setLoading(false);
    }
  }, [selectedDisaster]);

  // Fetch data when component mounts or when dependencies change
  useEffect(() => {
    fetchDisasterDistribution();
  }, [fetchDisasterDistribution]);

  // Helper function to check if a disaster type matches a category
  const isMatchingCategory = (type, category) => {
    // If the type matches the category directly
    if (type === category) return true;

    // If the type is one of the subcategories of the category
    return disasterCategoriesMapping[category] && disasterCategoriesMapping[category].includes(type);
  };

  const capitalizeFirstLetter = (string) => {
    if (!string) return "";
    return string.charAt(0).toUpperCase() + string.slice(1);
  };

  const handleChartClick = (event, elements) => {
    if (elements && elements.length > 0) {
      const clickedCategory = chartData.chartJsData.labels[elements[0].index].toLowerCase();
      setSelectedCategory(clickedCategory);
    } else {
      setSelectedCategory(null);
    }
  };

  // Handle clicks outside the chart to reset selection
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (chartRef.current && !chartRef.current.contains(event.target)) {
        setSelectedCategory(null); // Reset to default overview
      }
    };

    document.addEventListener("click", handleClickOutside);
    return () => {
      document.removeEventListener("click", handleClickOutside);
    };
  }, []);

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
    },
    onClick: handleChartClick,
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

          {/* Overview Section */}
          <div className="overview-section">
            <h3>Disaster Categories Overview</h3>
            {selectedCategory ? (
                <ul className="subcategories">
                  <h4>{capitalizeFirstLetter(selectedCategory)}</h4>
                  {chartData.originalData
                      .filter(item => item.type.toLowerCase() === selectedCategory.toLowerCase())
                      .map(item => (
                          <li key={item.type}>
                    <span className="subcategory">
                      {capitalizeFirstLetter(item.type)}
                    </span>
                            <span className="occurrence">{item.count}</span>
                          </li>
                      ))}
                </ul>
            ) : (
                <ul>
                  {chartData.originalData.map(item => (
                      <li key={item.type}>
                  <span className="category">
                    {capitalizeFirstLetter(item.type)}
                  </span>
                        <span className="occurrence">{item.count}</span>
                      </li>
                  ))}
                </ul>
            )}
          </div>
        </div>
      </div>
  );
};

export default DonutChart;