import React, { useState } from "react";

function Filters({ setSelectedDisaster }) {
    const [activeFilter, setActiveFilter] = useState("all");

    const filterTweets = (disasterType) => {
        const tweetFeed = document.getElementById("tweet-feed");
        const tweets = tweetFeed.querySelectorAll(".tweet-container");

        tweets.forEach((tweet) => {
            const tag = tweet.querySelector(".disaster-tag").textContent.toLowerCase();

            // Logic for grouping subcategories
            const categoryGroups = {
                fire: ["wild fire", "bush fire", "forest fire"],
                storm: ["storm", "blizzard", "cyclone", "dust storm", "hurricane", "tornado", "typhoon"],
                earthquake: ["earthquake"],
                tsunami: ["tsunami"],
                volcano: ["volcano"],
                flood: ["flood"],
                landslide: ["landslide", "avalanche"],
                other: ["haze", "meteor", "unknown"],
            };

            if (
                disasterType === "all" || // Show all tweets
                tag === disasterType || // Match exact type
                (categoryGroups[disasterType] && categoryGroups[disasterType].includes(tag)) // Match subcategories
            ) {
                tweet.style.display = "block";
            } else {
                tweet.style.display = "none";
            }
        });

        setActiveFilter(disasterType);
        // Notify the parent component of the selected disaster type
        setSelectedDisaster(disasterType);
    };

    return (
        <div className="disaster-filters">
            <button
                className={`filter-button ${activeFilter === "all" ? "active" : ""}`}
                onClick={() => filterTweets("all")}
            >
                All
            </button>
            <button
                className={`filter-button ${activeFilter === "fire" ? "active" : ""}`}
                onClick={() => filterTweets("fire")}
            >
                WildFire
            </button>
            <button
                className={`filter-button ${activeFilter === "storm" ? "active" : ""}`}
                onClick={() => filterTweets("storm")}
            >
                Storm
            </button>
            <button
                className={`filter-button ${activeFilter === "earthquake" ? "active" : ""}`}
                onClick={() => filterTweets("earthquake")}
            >
                Earthquake
            </button>
            <button
                className={`filter-button ${activeFilter === "tsunami" ? "active" : ""}`}
                onClick={() => filterTweets("tsunami")}
            >
                Tsunami
            </button>
            <button
                className={`filter-button ${activeFilter === "volcano" ? "active" : ""}`}
                onClick={() => filterTweets("volcano")}
            >
                Volcano
            </button>
            <button
                className={`filter-button ${activeFilter === "flood" ? "active" : ""}`}
                onClick={() => filterTweets("flood")}
            >
                Flood
            </button>
            <button
                className={`filter-button ${activeFilter === "landslide" ? "active" : ""}`}
                onClick={() => filterTweets("landslide")}
            >
                Landslide
            </button>
            <button
                className={`filter-button ${activeFilter === "other" ? "active" : ""}`}
                onClick={() => filterTweets("other")}
            >
                Other
            </button>
        </div>
    );
}

export default Filters;
