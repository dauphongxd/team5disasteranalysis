import React, { useEffect, useState } from "react";
import { api } from "../services/api";

function TweetFeed({ limitTweets = 20 }) {
    const [tweets, setTweets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Fetch latest tweets from DynamoDB through API
        async function fetchLatestTweets() {
            try {
                setLoading(true);

                // Use the same API method as TweetFeedPage
                const result = await api.getPosts("all", limitTweets, null);

                if (result && result.posts) {
                    console.log(`Loaded ${result.posts.length} tweets from DynamoDB`);
                    setTweets(result.posts);
                } else {
                    console.log("No tweets returned from API");
                    setTweets([]);
                }

                setLoading(false);
            } catch (err) {
                console.error("Error fetching tweets from DynamoDB:", err);
                setError("Failed to load tweets. Please try again.");
                setLoading(false);

                // Fallback to local JSON if API fails
                try {
                    console.log("Attempting to fallback to local JSON file");
                    const response = await fetch("/posts.json");
                    const data = await response.json();
                    const disasterTweets = data.filter(tweet => tweet.is_disaster === true);
                    const limitedTweets = disasterTweets.slice(0, limitTweets);
                    setTweets(limitedTweets);
                    console.log(`Loaded ${limitedTweets.length} tweets from fallback JSON`);
                } catch (fallbackError) {
                    console.error("Fallback also failed:", fallbackError);
                }
            }
        }

        fetchLatestTweets();
    }, [limitTweets]);

    // Format date in a friendly way
    const formatDate = (dateString) => {
        if (!dateString) return "";

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
        <div className="tweet-section">
            {loading ? (
                <div className="loading-container">
                    <p>Loading tweets...</p>
                </div>
            ) : error ? (
                <div className="error-container">
                    <p>{error}</p>
                </div>
            ) : (
                <div className="tweet-feed" id="tweet-feed" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                    {tweets.length > 0 ? (
                        tweets.map((tweet, index) => (
                            <div className="tweet-container" key={tweet.post_id || tweet.id || index}>
                                <div className="tweet-header">
                                    <div className="profile-pic-placeholder"></div>
                                    <div className="tweet-user-info">
                                        <div>
                                            <strong>{tweet.username || tweet.display_name || "Unknown User"}</strong>
                                        </div>
                                        <div>
                                            <span>@{tweet.username || tweet.handle || tweet.user_id || "user"}</span>
                                        </div>
                                        <div>
                                            <small>{formatDate(tweet.created_at || tweet.timestamp)}</small>
                                        </div>
                                    </div>
                                </div>
                                <div className="tweet-content">
                                    <p>{tweet.original_text || tweet.text}</p>

                                    {/* Media attachments */}
                                    {(tweet.media || tweet.media_urls) && (
                                        <div className="tweet-media">
                                            {(tweet.media || tweet.media_urls || []).map((mediaUrl, idx) => (
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

                                    {/* Location information */}
                                    {tweet.location_name && (
                                        <div className="tweet-location">
                                            📍 {tweet.location_name}
                                        </div>
                                    )}
                                </div>
                                <div className="tweet-footer">
                                    <div className="disaster-tag">
                                        {tweet.disaster_type || tweet.predicted_disaster_type}
                                    </div>
                                    {tweet.confidence_score && (
                                        <div className="confidence-score">
                                            Confidence: {typeof tweet.confidence_score === 'number' ?
                                            `${Math.round(tweet.confidence_score * 100)}%` :
                                            tweet.confidence_score}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="no-tweets-container">
                            <p>No disaster tweets found</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default TweetFeed;