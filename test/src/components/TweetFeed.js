import React, { useState, useEffect, useCallback, useRef } from "react";
import api from "../services/api";

function TweetFeed({ selectedDisaster }) {
  const [tweets, setTweets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nextToken, setNextToken] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const loaderRef = useRef(null); // Reference for the bottom loader element
  const POSTS_PER_PAGE = 20; // Load 20 posts at a time

  // Use useCallback to memoize the fetchTweets function
  const fetchTweets = useCallback(async (isInitialLoad = false) => {
    try {
      if (isInitialLoad) {
        setLoading(true);
      }

      setError(null);

      // Reset if it's the initial load due to filter change
      if (isInitialLoad && tweets.length > 0) {
        setTweets([]);
        setNextToken(null);
      }

      // Use the api module to fetch posts with selected disaster type
      const data = await api.getPosts(selectedDisaster, POSTS_PER_PAGE, nextToken);

      // Log the first post for debugging
      if (data.posts && data.posts.length > 0) {
        console.log("Sample tweet data:", data.posts[0]);
      }

      // Transform data into the expected format for display
      const formattedTweets = data.posts.map(post => {
        // Extract handle from username field or use handle directly
        let userHandle = '';
        if (post.handle) {
          userHandle = post.handle;
        } else if (post.username) {
          userHandle = post.username;
        } else if (post.user_id) {
          // Fallback to user_id if available
          userHandle = post.user_id.toString().substring(0, 10) + '...';
        }

        // Determine display name
        let userName = "Unknown User";
        if (post.display_name && post.display_name.trim()) {
          userName = post.display_name.trim();
        } else if (post.handle) {
          // If no display name, use handle as a fallback but don't repeat in both places
          userName = post.handle;
        }

        // Ensure avatar URL is usable
        let avatarUrl = "/default-avatar.jpg";
        if (post.avatar_url) {
          avatarUrl = post.avatar_url;
        }

        console.log("Tweet data:", {
          handle: userHandle,
          display_name: userName,
          avatar: avatarUrl
        });

        return {
          uri: post.post_id,
          handle: userHandle,
          display_name: userName,
          text: post.original_text || post.clean_text || "",
          timestamp: post.created_at,
          avatar: avatarUrl,
          disaster_type: post.disaster_type,
          confidence_score: post.confidence_score,
          is_disaster: true
        };
      });

      // If we're loading more (with nextToken), append to existing tweets
      // Otherwise, replace the tweets array
      if (nextToken && !isInitialLoad) {
        setTweets(prevTweets => [...prevTweets, ...formattedTweets]);
      } else {
        setTweets(formattedTweets);
      }

      // Save next token for pagination if available
      if (data.next_token) {
        setNextToken(data.next_token);
        setHasMore(true);
      } else {
        setNextToken(null); // No more pages
        setHasMore(false);
      }

      setLoading(false);
    } catch (error) {
      console.error("Error fetching tweets:", error);
      setError(error.message);
      setLoading(false);
      setHasMore(false);
    }
  }, [selectedDisaster, nextToken, tweets.length]);

  // Fetch tweets when component mounts or disaster type changes
  useEffect(() => {
    // Reset everything when selected disaster changes
    setTweets([]);
    setNextToken(null);
    setHasMore(true);
    fetchTweets(true);
  }, [selectedDisaster]); // Only include selectedDisaster to trigger refresh

  // Set up intersection observer for infinite scrolling
  useEffect(() => {
    // If we're already loading or there are no more tweets, don't do anything
    if (loading || !hasMore || !loaderRef.current) return;

    const observer = new IntersectionObserver(
        entries => {
          // If the loader element is visible and we're not already loading
          if (entries[0].isIntersecting && hasMore && !loading) {
            fetchTweets(false);
          }
        },
        { threshold: 0.5 } // Fire when 50% of the element is visible
    );

    // Start observing the loader element
    observer.observe(loaderRef.current);

    // Clean up the observer when component unmounts or dependencies change
    return () => {
      if (loaderRef.current) {
        observer.unobserve(loaderRef.current);
      }
    };
  }, [loading, hasMore, fetchTweets]);

  // If loading and no tweets yet, show a loading indicator
  if (loading && tweets.length === 0) {
    return (
        <div className="tweet-section">
          <div className="map-header">
            <h3>Disaster Tweets</h3>
          </div>
          <div className="tweet-feed">
            <div className="loading-indicator">Loading disaster tweets...</div>
          </div>
        </div>
    );
  }

  // If there's an error and no tweets, show error message
  if (error && tweets.length === 0) {
    return (
        <div className="tweet-section">
          <div className="map-header">
            <h3>Disaster Tweets</h3>
          </div>
          <div className="tweet-feed">
            <div className="error-message">Error: {error}</div>
            <button onClick={() => fetchTweets(true)} className="retry-button">Retry</button>
          </div>
        </div>
    );
  }

  return (
      <div className="tweet-section">
        <div className="map-header">
          <h3>Disaster Tweets</h3>
        </div>
        <div className="tweet-feed" id="tweet-feed">
          {tweets.length === 0 ? (
              <div className="no-tweets-message">
                No disaster tweets found for this category
              </div>
          ) : (
              <div className="tweet-content-wrapper">
                {tweets.map((tweet) => (
                    <div className="tweet-container" key={tweet.uri}>
                      <div className="tweet-header">
                        <img
                            src={tweet.avatar}
                            alt="Profile"
                            className="profile-pic"
                            onError={(e) => {
                              e.target.onerror = null;
                              e.target.src = "/default-avatar.jpg";
                            }}
                        />
                        <div>
                          <div>
                            <strong>{tweet.display_name}</strong>
                          </div>
                          <div>
                            <span>@{tweet.handle}</span>
                          </div>
                          <div>
                            <small>{new Date(tweet.timestamp).toLocaleString()}</small>
                          </div>
                        </div>
                      </div>
                      <div className="tweet-content">
                        <p>{tweet.text}</p>
                      </div>
                      <div className="disaster-tag">
                        {tweet.disaster_type}
                      </div>
                    </div>
                ))}

                {/* Loader reference element - appears at the bottom */}
                <div
                    ref={loaderRef}
                    className={`tweet-loader ${!hasMore ? 'hidden' : ''}`}
                >
                  {loading && <div className="loading-indicator">Loading more tweets...</div>}
                  {!loading && hasMore && <div className="scroll-indicator">Scroll for more tweets</div>}
                  {!hasMore && <div className="end-message">No more tweets to load</div>}
                </div>
              </div>
          )}
        </div>
      </div>
  );
}

export default TweetFeed;