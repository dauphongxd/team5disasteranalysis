import React, { useState } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

// Register Chart.js components
ChartJS.register(ArcElement, Tooltip, Legend);

// Disaster categories mapping
const disasterCategoriesMapping = {
  fire: ["wild fire", "bush fire", "forest fire"],
  storm: ["storm", "blizzard", "cyclone", "dust storm", "hurricane", "tornado", "typhoon"],
  earthquake: ["earthquake"],
  tsunami: ["tsunami"],
  volcano: ["volcano"],
  flood: ["flood"],
  landslide: ["landslide", "avalanche"],
  other: ["haze", "meteor", "unknown"],
};

const DisasterCategoriesWithChart = () => {
  const [selectedCategory, setSelectedCategory] = useState(null);

  // Prepare data for the donut chart
  const labels = Object.keys(disasterCategoriesMapping); // E.g., ['fire', 'storm', 'earthquake', ...]
  const dataValues = labels.map((category) => disasterCategoriesMapping[category].length); // Count subcategories

  const data = {
    labels: labels.map((label) => label.charAt(0).toUpperCase() + label.slice(1)), // Capitalize labels
    datasets: [
      {
        label: "Number of Subcategories",
        data: dataValues,
        backgroundColor: [
          "#FF6384", // Color for each section
          "#36A2EB",
          "#FFCE56",
          "#4BC0C0",
          "#9966FF",
          "#FF9F40",
          "#C9CBCF",
          "#FF5733",
        ],
        hoverBackgroundColor: [
          "#FF6384",
          "#36A2EB",
          "#FFCE56",
          "#4BC0C0",
          "#9966FF",
          "#FF9F40",
          "#C9CBCF",
          "#FF5733",
        ],
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "bottom",
      },
    },
  };

  // Handle click to toggle the selected category
  const handleCategoryClick = (category) => {
    setSelectedCategory(selectedCategory === category ? null : category);
  };

  return (
    <div className="help-section">
        <h2 className="heading">Natural Disasters Overview</h2>
        <div className="chart-section">
            {/* Donut Chart */}
            <div className="donutchart-container">
                <Doughnut data={data} options={options} />
            </div>
        </div>
    </div>
  );
};

export default DisasterCategoriesWithChart;
