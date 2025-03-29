import React, { useState, useEffect } from "react";
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

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

// Disaster category mapping
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

const Timechart = ({ disasterData, selectedDisaster, apiData }) => {
    const [view, setView] = useState("weeks"); // State to toggle between "weeks" and "months"
    const [chartData, setChartData] = useState(null);

    // Process data based on source (API data or fallback to processed disasterData)
    useEffect(() => {
        if (apiData) {
            // If we have API data, use it
            console.log("Using API data for timeline:", apiData);

            // Map API colors to match our UI theme
            const colors = ["#36A2EB", "#FF6384", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40", "#8E44AD", "#1ABC9C"];

            const datasets = apiData.datasets.map((dataset, index) => {
                return {
                    label: dataset.label,
                    data: dataset.data,
                    borderColor: colors[index % colors.length],
                    backgroundColor: colors[index % colors.length] + "80",
                    fill: true,
                };
            });

            setChartData({
                labels: apiData.labels,
                datasets,
            });
        } else if (disasterData) {
            // Otherwise fall back to our local processing
            processLocalData();
        }
    }, [apiData, disasterData, selectedDisaster, view]);

    // Helper function to get the last 12 weeks
    const getLast12Weeks = () => {
        const weeks = [];
        const now = new Date();
        for (let i = 0; i < 12; i++) {
            const startOfWeek = new Date(now);
            startOfWeek.setDate(now.getDate() - now.getDay() - i * 7); // Get the start of each week
            const endOfWeek = new Date(startOfWeek);
            endOfWeek.setDate(startOfWeek.getDate() + 6); // End of the week
            weeks.push(
                `${startOfWeek.toLocaleDateString("en-US", { month: "short", day: "numeric" })} - ${endOfWeek.toLocaleDateString(
                    "en-US",
                    { month: "short", day: "numeric" }
                )}`
            );
        }
        return weeks.reverse();
    };

    // Helper function to get the last 12 months
    const getLast12Months = () => {
        const months = [];
        const now = new Date();
        for (let i = 0; i < 12; i++) {
            const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
            months.push(date.toLocaleDateString("en-US", { year: "numeric", month: "short" }));
        }
        return months.reverse();
    };

    // Process local data (fallback when API data isn't available)
    const processLocalData = () => {
        // Determine labels based on the current view
        const labels = view === "weeks" ? getLast12Weeks() : getLast12Months();

        // Initialize disaster categories with subcategories
        const disasterCategories = {};
        Object.keys(disasterCategoriesMapping).forEach((category) => {
            disasterCategoriesMapping[category].forEach((subCategory) => {
                disasterCategories[subCategory] = [];
            });
        });

        // Process disaster data and group by subcategories
        if (disasterData && disasterData.length > 0) {
            disasterData.forEach((post) => {
                if (post.is_disaster && post.predicted_disaster_type) {
                    const disasterType = post.predicted_disaster_type.toLowerCase();
                    const date = new Date(post.timestamp);

                    // Format the timestamp based on the current view
                    let timestamp;
                    if (view === "weeks") {
                        const startOfWeek = new Date(date);
                        startOfWeek.setDate(date.getDate() - date.getDay()); // Start of the week
                        const endOfWeek = new Date(startOfWeek);
                        endOfWeek.setDate(startOfWeek.getDate() + 6); // End of the week
                        timestamp = `${startOfWeek.toLocaleDateString("en-US", { month: "short", day: "numeric" })} - ${endOfWeek.toLocaleDateString(
                            "en-US",
                            { month: "short", day: "numeric" }
                        )}`;
                    } else {
                        timestamp = date.toLocaleDateString("en-US", { year: "numeric", month: "short" });
                    }

                    // Find the matching subcategory
                    Object.keys(disasterCategoriesMapping).forEach((category) => {
                        if (disasterCategoriesMapping[category].includes(disasterType)) {
                            if (!disasterCategories[disasterType]) {
                                disasterCategories[disasterType] = [];
                            }
                            disasterCategories[disasterType].push(timestamp);
                        }
                    });
                }
            });
        }

        // Filter datasets based on the selected disaster category
        const filteredCategories =
            selectedDisaster === "all"
                ? Object.keys(disasterCategories)
                : disasterCategoriesMapping[selectedDisaster] || [];

        const datasets = filteredCategories.map((subCategory, index) => {
            // Count occurrences per label for each subcategory
            const data = labels.map((label) =>
                disasterCategories[subCategory]?.filter((date) => date === label).length || 0
            );

            const colors = ["#36A2EB", "#FF6384", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40", "#8E44AD", "#1ABC9C"];
            return {
                label: subCategory, // Display subcategory name in the legend
                data,
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + "80",
                fill: true,
            };
        });

        setChartData({
            labels,
            datasets,
        });
    };

    const options = {
        responsive: true,
        plugins: {
            legend: {
                position: "top",
                labels: {
                    color: "#e0e0e0" // Light text for dark background
                }
            },
            title: {
                display: true,
                text: apiData ?
                    `Disaster Events (${apiData.interval})` :
                    `${view === "weeks" ? "Last 12 Weeks" : "Last 12 Months"}`,
                color: "#e0e0e0" // Light text for dark background
            },
        },
        scales: {
            y: {
                beginAtZero: true, // Ensure the Y-axis starts at 0
                grid: {
                    color: "rgba(255, 255, 255, 0.1)" // Lighter grid lines
                },
                ticks: {
                    color: "#aaaaaa" // Light text for tick labels
                }
            },
            x: {
                grid: {
                    color: "rgba(255, 255, 255, 0.1)" // Lighter grid lines
                },
                ticks: {
                    color: "#aaaaaa" // Light text for tick labels
                }
            }
        },
    };

    // If we don't have data yet, show a loading indicator
    if (!chartData) {
        return <div className="chart-loading">Loading chart data...</div>;
    }

    return (
        <div className="chart-section">
            {/* Line Chart */}
            <Line data={chartData} options={options} />

            {/* Only show toggle buttons if using local data (not API data) */}
            {!apiData && (
                <div className="view-toggle-buttons">
                    <button
                        className={`toggle-button ${view === "weeks" ? "active" : ""}`}
                        onClick={() => setView("weeks")}
                    >
                        Weeks
                    </button>
                    <button
                        className={`toggle-button ${view === "months" ? "active" : ""}`}
                        onClick={() => setView("months")}
                    >
                        Months
                    </button>
                </div>
            )}
        </div>
    );
};

export default Timechart;