import React, { useState, useEffect } from "react";

function Filters({ setSelectedDisaster, selectedDisaster, availableTypes = [] }) {
    // Use the selectedDisaster from props for controlled component state
    const [activeFilter, setActiveFilter] = useState(selectedDisaster || "all");

    // Update active filter when selectedDisaster prop changes
    useEffect(() => {
        setActiveFilter(selectedDisaster);
    }, [selectedDisaster]);

    // Default disaster categories - will be used when API doesn't return specific types
    const defaultCategories = [
        { id: "all", label: "All" },
        { id: "fire", label: "Wildfire", includes: ["wild fire", "bush fire", "forest fire"] },
        { id: "storm", label: "Storm", includes: ["storm", "blizzard", "cyclone", "dust storm", "hurricane", "tornado", "typhoon"] },
        { id: "earthquake", label: "Earthquake", includes: ["earthquake"] },
        { id: "tsunami", label: "Tsunami", includes: ["tsunami"] },
        { id: "volcano", label: "Volcano", includes: ["volcano"] },
        { id: "flood", label: "Flood", includes: ["flood"] },
        { id: "landslide", label: "Landslide", includes: ["landslide", "avalanche"] },
        { id: "other", label: "Other", includes: ["haze", "meteor", "unknown"] }
    ];

    const filterTweets = (disasterType) => {
        // Update the active filter in this component
        setActiveFilter(disasterType);

        // Notify the parent component of the selection
        setSelectedDisaster(disasterType);
    };

    // Determine which categories to display based on available types
    const getCategoriesToDisplay = () => {
        // If no available types from API, use default categories
        if (!availableTypes || availableTypes.length === 0) {
            return defaultCategories;
        }

        // Otherwise, use the categories that have matching types in the API response
        return defaultCategories.filter(category => {
            // "All" category is always shown
            if (category.id === "all") return true;

            // For other categories, check if any of their included types are in availableTypes
            if (category.includes) {
                return category.includes.some(type => availableTypes.includes(type));
            }

            // If the category doesn't have includes, check if its ID matches any available types
            return availableTypes.includes(category.id);
        });
    };

    const categoriesToDisplay = getCategoriesToDisplay();

    return (
        <div className="disaster-filters">
            {categoriesToDisplay.map(category => (
                <button
                    key={category.id}
                    className={`filter-button ${activeFilter === category.id ? "active" : ""}`}
                    onClick={() => filterTweets(category.id)}
                >
                    {category.label}
                </button>
            ))}
        </div>
    );
}

export default Filters;