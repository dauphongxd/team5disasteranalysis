import React, { useState, useEffect } from "react";

function Filters({ setSelectedDisaster, selectedDisaster, availableTypes = [] }) {
    // Use the selectedDisaster from props for controlled component state
    const [activeFilter, setActiveFilter] = useState(selectedDisaster || "all");

    // Update active filter when selectedDisaster prop changes
    useEffect(() => {
        setActiveFilter(selectedDisaster);
    }, [selectedDisaster]);

    // Default disaster categories - will be used when API doesn't return specific types
    // Updated to use underscores instead of spaces for consistency with backend
    // Removed tsunami from categories
    const defaultCategories = [
        { id: "all", label: "All" },
        { id: "fire", label: "Fire", includes: ["wild_fire", "bush_fire", "forest_fire"] },
        { id: "storm", label: "Storm", includes: ["storm", "blizzard", "cyclone", "dust_storm", "hurricane", "tornado", "typhoon"] },
        { id: "earthquake", label: "Earthquake", includes: ["earthquake"] },
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

    // Helper function to normalize disaster types (handles both underscore and space formats)
    const normalizeDisasterType = (type) => {
        if (!type) return '';
        return String(type).toLowerCase().replace(/ /g, '_');
    };

    // Modified to always show all categories
    const getCategoriesToDisplay = () => {
        // Always return all default categories
        return defaultCategories;
    };

    const categoriesToDisplay = getCategoriesToDisplay();

    return (
        <div className="disaster-filters">
            {categoriesToDisplay.map(category => (
                <button
                    key={category.id}
                    className={`sc-button ${activeFilter === category.id ? "active" : ""}`}
                    onClick={() => filterTweets(category.id)}
                >
                    {category.label}
                </button>
            ))}
        </div>
    );
}

export default Filters;