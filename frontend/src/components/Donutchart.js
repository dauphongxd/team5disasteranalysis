import React, { useState, useEffect, useRef, useCallback } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import api from "../services/api";

// Register Chart.js components
ChartJS.register(ArcElement, Tooltip, Legend);

// Disaster categories mapping for aggregating data - using underscores for consistency
// Removed tsunami from mappings
const disasterCategoriesMapping = {
  fire: ["wild_fire", "bush_fire", "forest_fire"],
  storm: ["storm", "blizzard", "cyclone", "dust_storm", "hurricane", "tornado", "typhoon"],
  earthquake: ["earthquake"],
  volcano: ["volcano"],
  flood: ["flood"],
  landslide: ["landslide", "avalanche"],
  other: ["haze", "meteor", "unknown"]
};

// Super category display names (for better formatting)
// Removed tsunami from super category names
const superCategoryNames = {
  fire: "Fire",
  storm: "Storm",
  earthquake: "Earthquake",
  volcano: "Volcano",
  flood: "Flood",
  landslide: "Landslide",
  other: "Other"
};

// Consistent color mapping for each category
// Removed tsunami from color mapping
const categoryColors = {
  fire: "#FF6384",     // Red
  storm: "#36A2EB",    // Blue
  earthquake: "#FFCE56", // Yellow
  volcano: "#9966FF",  // Purple
  flood: "#4BC0C0",    // Teal
  landslide: "#FF9F40", // Orange
  other: "#C9CBCF"     // Gray
};

// Define the order we want to display categories in
// Removed tsunami from category order
const categoryOrder = [
  "fire",
  "storm",
  "earthquake",
  "volcano",
  "flood",
  "landslide",
  "other"
];

// Helper function to normalize disaster types
const normalizeDisasterType = (type) => {
  if (!type) return '';
  return String(type).toLowerCase().replace(/ /g, '_');
};

const DonutChart = () => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const chartRef = useRef(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [lastClickTime, setLastClickTime] = useState(0);
  const MONTHS_PERIOD = 6;

  // Store the category map so we can look it up correctly in the click handler
  const categoryMapRef = useRef(null);

  // Store the raw API data for subcategory drill-down
  const apiDataRef = useRef(null);

  // Keep track of subcategory data
  const [subcategoryData, setSubcategoryData] = useState(null);

  // Use useCallback to memoize the fetchDisasterDistribution function
  const fetchDisasterDistribution = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Use the dedicated 6-month endpoint
      const apiData = await api.getDisasterDistributionMonths(MONTHS_PERIOD);

      if (!apiData || !apiData.data || !Array.isArray(apiData.data)) {
        throw new Error('Invalid data format received from API');
      }

      // Store the raw API data for later use in subcategory drilldown
      apiDataRef.current = apiData.data;

      // Initialize all super categories with 0 counts
      const superCategoryCounts = {};
      Object.keys(disasterCategoriesMapping).forEach(category => {
        superCategoryCounts[category] = 0;
      });

      let totalCount = 0;

      // Process each data item
      apiData.data.forEach(item => {
        // Normalize the type for consistent comparison
        const normalizedType = normalizeDisasterType(item.type);
        const count = item.count || 0;

        // Skip tsunami data
        if (normalizedType === 'tsunami' || normalizedType === 'tsunami_') {
          return;
        }

        totalCount += count;

        // Find which super category this item belongs to
        let foundSuperCategory = false;
        for (const [superCategory, subcategories] of Object.entries(disasterCategoriesMapping)) {
          // Check if this is a direct match with a super category
          if (superCategory === normalizedType) {
            superCategoryCounts[superCategory] += count;
            foundSuperCategory = true;
            break;
          }

          // Check if it matches any subcategory (with normalization)
          const matchingSubcategory = subcategories.some(subType => {
            const normalizedSubType = normalizeDisasterType(subType);
            return normalizedType === normalizedSubType ||
                normalizedType === normalizedSubType.replace(/_/g, ' ') ||
                normalizedType.replace(/_/g, ' ') === normalizedSubType;
          });

          if (matchingSubcategory) {
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

      // Create array of ALL super categories including those with 0 counts
      // Order by our predefined ordering, not by count
      const superCategoryData = categoryOrder.map(category => ({
        category,
        displayName: superCategoryNames[category] || capitalizeFirstLetter(category),
        count: superCategoryCounts[category] || 0
      }));

      // Sort superCategoryData by count in descending order
      superCategoryData.sort((a, b) => b.count - a.count);

      // Save the ordered categories to the ref so we can use it in click handler
      categoryMapRef.current = superCategoryData;

      // Extract the label and data arrays in the same order
      const labels = superCategoryData.map(item => item.displayName);
      const dataValues = superCategoryData.map(item => item.count);
      const backgroundColors = superCategoryData.map(item => categoryColors[item.category]);

      // Format for Chart.js
      const formattedData = {
        labels: labels,
        datasets: [
          {
            label: "Disaster Occurrences",
            data: dataValues,
            backgroundColor: backgroundColors,
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

  // Function to prepare subcategory data for the selected category
  const prepareSubcategoryData = useCallback((selectedSuperCategory) => {
    if (!apiDataRef.current || !selectedSuperCategory) return null;

    // Get the subcategories for this super category
    const subcategoryTypes = disasterCategoriesMapping[selectedSuperCategory] || [];

    // Find all matching subcategories in the API data
    const subcategoryData = [];
    const subcategoryCounts = {};

    // Initialize counts for all expected subcategories
    subcategoryTypes.forEach(subType => {
      subcategoryCounts[subType] = 0;
    });

    // Sum the counts from the API data
    apiDataRef.current.forEach(item => {
      const normalizedType = normalizeDisasterType(item.type);
      const count = item.count || 0;

      // Skip tsunami data
      if (normalizedType === 'tsunami' || normalizedType === 'tsunami_') {
        return;
      }

      // Check if this item matches any subcategory
      for (const subType of subcategoryTypes) {
        const normalizedSubType = normalizeDisasterType(subType);

        if (normalizedType === normalizedSubType ||
            normalizedType === normalizedSubType.replace(/_/g, ' ') ||
            normalizedType.replace(/_/g, ' ') === normalizedSubType) {
          subcategoryCounts[subType] += count;
          break;
        }
      }
    });

    // Create an array of subcategory data
    Object.entries(subcategoryCounts).forEach(([subType, count]) => {
      if (count > 0) {
        subcategoryData.push({
          category: subType,
          displayName: capitalizeFirstLetter(subType.replace(/_/g, ' ')),
          count: count
        });
      }
    });

    // Sort by count in descending order
    subcategoryData.sort((a, b) => b.count - a.count);

    // If no subcategories have data, show a placeholder
    if (subcategoryData.length === 0) {
      subcategoryData.push({
        category: "no_data",
        displayName: "No Data Available",
        count: 0
      });
    }

    return subcategoryData;
  }, []);

  // When the selected category changes, update subcategory data
  useEffect(() => {
    if (selectedCategory) {
      const subcats = prepareSubcategoryData(selectedCategory);
      setSubcategoryData(subcats);
    } else {
      setSubcategoryData(null);
    }
  }, [selectedCategory, prepareSubcategoryData]);

  // Fetch data when component mounts
  useEffect(() => {
    fetchDisasterDistribution();
  }, [fetchDisasterDistribution]);

  const capitalizeFirstLetter = (string) => {
    if (!string) return "";
    return string.charAt(0).toUpperCase() + string.slice(1);
  };

  // Handle chart click events
  const handleChartClick = (event, chartElements) => {
    if (chartElements.length === 0) return;

    const clickedIndex = chartElements[0].index;
    console.log("Clicked index:", clickedIndex);

    // Get the ordered categories from our ref
    if (!categoryMapRef.current || clickedIndex >= categoryMapRef.current.length) {
      console.error("Invalid chart click index or categories not loaded");
      return;
    }

    // Get the category data from our ordered mapping
    const clickedCategoryData = categoryMapRef.current[clickedIndex];
    console.log("Clicked category data:", clickedCategoryData);

    // Get the category ID
    const clickedCategory = clickedCategoryData.category;
    console.log("Setting selected category to:", clickedCategory);

    // Calculate time since last click for double-click detection (300ms threshold)
    const currentTime = new Date().getTime();
    const isDoubleClick = (currentTime - lastClickTime < 300);
    setLastClickTime(currentTime);

    if (isDoubleClick || clickedCategory === selectedCategory) {
      // Reset selection on double-click or if clicking the same category again
      setSelectedCategory(null);
    } else {
      // Set new selection
      setSelectedCategory(clickedCategory);
    }
  };

  // Chart options
  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        position: "bottom",
        labels: {
          color: "#ffffff",
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
        callbacks: {
          // Add percentage to tooltip
          label: function(context) {
            const label = context.label || '';
            const value = context.raw || 0;
            const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
            const percentage = ((value / total) * 100).toFixed(2);

            return `${label}: ${value} (${percentage}%)`;
          }
        }
      }
    },
    // Add onClick handler to detect clicks on chart segments
    onClick: handleChartClick
  };

  if (loading && !chartData) {
    return (
        <div className="help-section">
          <h2 className="heading">Natural Disasters Overview</h2>
          {/*<div className="Donutchart-section">*/}
          {/*  <div className="loading-indicator">Loading disaster data (last {MONTHS_PERIOD} months)...</div>*/}
          {/*</div>*/}
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

  // Determine which data to display in the table
  const displayData = selectedCategory && subcategoryData
      ? subcategoryData   // Show subcategories when selected
      : chartData.superCategoryData;  // Otherwise show main categories

  return (
      <div className="help-section">
        <h2 className="heading">Natural Disasters Overview</h2>
        <div className="Donutchart-section" ref={chartRef}>
          {/* Donut Chart - Always show the super categories */}
          <div className="donutchart-container">
            <Doughnut data={chartData.chartJsData} options={options} />
          </div>

          {/* Overview Section - Shows subcategories when a category is selected */}
          <div className="overview-section">
            <h3>
              {selectedCategory
                  ? `${superCategoryNames[selectedCategory]}`
                  : `Disaster Categories Overview (${MONTHS_PERIOD} months)`}
            </h3>
            <ul>
              {displayData.map(item => (
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