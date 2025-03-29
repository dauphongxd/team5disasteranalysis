import React, { useState, useEffect } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

// Register Chart.js components
ChartJS.register(ArcElement, Tooltip, Legend);

// Disaster categories mapping for fallback
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

const DisasterCategoriesWithChart = ({ distributionData }) => {
    const [selectedCategory, setSelectedCategory] = useState(null);
    const [chartData, setChartData] = useState(null);

    useEffect(() => {
        if (distributionData) {
            // Use the API data
            console.log("Using API distribution data:", distributionData);

            const labels = distributionData.data.map(item => item.type);
            const dataValues = distributionData.data.map(item => item.count);

            prepareChartData(labels, dataValues);
        } else {
            // Fallback to static data
            const labels = Object.keys(disasterCategoriesMapping);
            const dataValues = labels.map(category => disasterCategoriesMapping[category].length);

            prepareChartData(labels, dataValues);
        }
    }, [distributionData]);

    const prepareChartData = (labels, dataValues) => {
        // Colors for the chart
        const backgroundColors = [
            "#FF6384", // Red
            "#36A2EB", // Blue
            "#FFCE56", // Yellow
            "#4BC0C0", // Teal
            "#9966FF", // Purple
            "#FF9F40", // Orange
            "#C9CBCF", // Grey
            "#FF5733", // Coral
        ];

        // Capitalize labels
        const capitalizedLabels = labels.map(label =>
            label.charAt(0).toUpperCase() + label.slice(1)
        );

        setChartData({
            labels: capitalizedLabels,
            datasets: [
                {
                    label: "Number of Incidents",
                    data: dataValues,
                    backgroundColor: backgroundColors.slice(0, labels.length),
                    hoverBackgroundColor: backgroundColors.slice(0, labels.length).map(color =>
                        color.replace(")", ", 0.8)")
                    ),
                    borderWidth: 1,
                    borderColor: "rgba(255, 255, 255, 0.2)",
                },
            ],
        });
    };

    const options = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                position: "bottom",
                labels: {
                    boxWidth: 15,
                    padding: 15,
                    color: "#e0e0e0"
                },
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const label = context.label || '';
                        const value = context.raw || 0;
                        const dataset = context.dataset;
                        const total = dataset.data.reduce((acc, data) => acc + data, 0);
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${label}: ${value} (${percentage}%)`;
                    }
                }
            }
        },
        // Add a cutout to create the donut effect
        cutout: '60%',
        // Animation
        animation: {
            animateRotate: true,
            animateScale: true
        }
    };

    // Handle click to toggle the selected category
    const handleCategoryClick = (category) => {
        setSelectedCategory(selectedCategory === category ? null : category);
    };

    if (!chartData) {
        return <div className="chart-loading">Loading chart data...</div>;
    }

    return (
        <div className="donut-chart-container">
            <div className="chart-wrapper">
                <Doughnut data={chartData} options={options} />
            </div>

            {distributionData && distributionData.total_count && (
                <div className="chart-totals">
                    <p>Total incidents: <strong>{distributionData.total_count.toLocaleString()}</strong></p>
                </div>
            )}
        </div>
    );
};

export default DisasterCategoriesWithChart;