// src/pages/TweetFeedPage.js
import React, { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../services/api";
import Filters from "../components/Filters";

function TweetFeedPage({ selectedDisaster, setSelectedDisaster }) {
    const [tweets, setTweets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [nextToken, setNextToken] = useState(null);
    const [hasMore, setHasMore] = useState(true);
    const [initialLoad, setInitialLoad] = useState(true);
    const [currentDisasterType, setCurrentDisasterType] = useState(selectedDisaster || "all");

    // Observer for infinite scrolling
    const observer = useRef();
    const lastTweetElementRef = useCallback(node => {
        if (loading) return;
        if (observer.current) observer.current.disconnect();

        observer.current = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting && hasMore) {
                loadMoreTweets();
            }
        }, { threshold: 0.5 });

        if (node) observer.current.observe(node);
    }, [loading, hasMore]);

    // Function to fetch initial tweets
    const fetchTweets = async (disasterType = "all", reset = false) => {
        try {
            setLoading(true);
            setCurrentDisasterType(disasterType);

            // Clear tweets if changing disaster type
            if (reset) {
                setTweets([]);
                setNextToken(null);
            }

            const result = await api.getPosts(disasterType, 20, reset ? null : nextToken);

            if (result && result.posts) {
                setTweets(prev => reset ? result.posts : [...prev, ...result.posts]);
                setNextToken(result.next_token || null);
                setHasMore(!!result.next_token);
            } else {
                setHasMore(false);
            }

            setLoading(false);
            setInitialLoad(false);
        } catch (err) {
            console.error("Error fetching tweets:", err);
            setError("Failed to load tweets. Please try again.");
            setLoading(false);
            setInitialLoad(false);
        }
    };

    // Function to load more tweets (pagination)
    const loadMoreTweets = () => {
        if (!nextToken || loading) return;
        fetchTweets(currentDisasterType);
    };

    // Update when selected disaster changes
    useEffect(() => {
        if (selectedDisaster !== currentDisasterType) {
            fetchTweets(selectedDisaster, true);
        }
    }, [selectedDisaster]);

    // Initial load
    useEffect(() => {
        fetchTweets(currentDisasterType, true);
    }, []);

    // Handle disaster filter change
    const handleDisasterChange = (disasterType) => {
        if (setSelectedDisaster) {
            setSelectedDisaster(disasterType);
        }
        fetchTweets(disasterType, true);
    };

    // Format date in a friendly way
    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="tweet-feed-page">
            <h2>Disaster Tweets</h2>

            {/* Filters component */}
            <Filters
                selectedDisaster={currentDisasterType}
                setSelectedDisaster={handleDisasterChange}
            />

            {/* Stats and info */}
            <div className="tweets-info">
                <p>
                    {tweets.length > 0 ? (
                        `Showing ${tweets.length} tweets related to ${currentDisasterType === "all" ? "all disasters" : currentDisasterType}`
                    ) : !loading ? (
                        "No tweets found"
                    ) : (
                        "Loading tweets..."
                    )}
                </p>
            </div>

            {/* Tweets list */}
            {initialLoad ? (
                <div className="loading-container">
                    <div className="loader"></div>
                    <p>Loading tweets...</p>
                </div>
            ) : error ? (
                <div className="error-container">
                    <p>{error}</p>
                    <button onClick={() => fetchTweets(currentDisasterType, true)}>
                        Try Again
                    </button>
                </div>
            ) : tweets.length === 0 ? (
                <div className="no-tweets-container">
                    <p>No tweets found for this disaster type.</p>
                </div>
            ) : (
                <div className="tweets-container">
                    <div className="tweet-feed" id="tweet-feed">
                        {tweets.map((tweet, index) => {
                            // Check if this is the last element
                            const isLastElement = index === tweets.length - 1;

                            return (
                                <div
                                    className="tweet-container"
                                    key={tweet.post_id || index}
                                    ref={isLastElement ? lastTweetElementRef : null}
                                >
                                    <div className="tweet-header">
                                        <div className="profile-pic-placeholder"></div>
                                        <div className="tweet-user-info">
                                            <div>
                                                <strong>{tweet.username || "Unknown User"}</strong>
                                            </div>
                                            <div>
                                                <span>@{tweet.username || tweet.user_id || "user"}</span>
                                            </div>
                                            <div>
                                                <small>{formatDate(tweet.created_at)}</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="tweet-content">
                                        <p>{tweet.original_text}</p>

                                        {tweet.media && tweet.media.length > 0 && (
                                            <div className="tweet-media">
                                                {tweet.media.map((mediaUrl, idx) => (
                                                    <img
                                                        key={idx}
                                                        src={mediaUrl}
                                                        alt="Tweet media"
                                                        className="tweet-media-item"
                                                        onError={(e) => {
                                                            e.target.onerror = null;
                                                            e.target.src = "https://via.placeholder.com/300x200?text=Media+Unavailable";
                                                        }}
                                                    />
                                                ))}
                                            </div>
                                        )}

                                        {tweet.location_name && (
                                            <div className="tweet-location">
                                                📍 {tweet.location_name}
                                            </div>
                                        )}
                                    </div>
                                    <div className="tweet-footer">
                                        <div className="disaster-tag">
                                            {tweet.disaster_type}
                                        </div>
                                        <div className="confidence-score">
                                            Confidence: {typeof tweet.confidence_score === 'number' ?
                                            `${Math.round(tweet.confidence_score * 100)}%` :
                                            tweet.confidence_score}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Loading indicator for pagination */}
                    {loading && !initialLoad && (
                        <div className="loading-more">
                            <div className="loader-small"></div>
                            <p>Loading more tweets...</p>
                        </div>
                    )}

                    {/* End of tweets message */}
                    {!hasMore && tweets.length > 0 && (
                        <div className="end-message">
                            <p>You've reached the end of available tweets</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default TweetFeedPage;