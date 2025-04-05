import React, { useState, useEffect, useCallback, useRef } from "react";
import api from "../services/api";
import websocketService from "../services/websocket";

// Hardcoded WebSocket URL for development
const WEBSOCKET_URL = process.env.REACT_APP_WEBSOCKET_URL || 'http://localhost:5000';

function TweetFeed({ selectedDisaster }) {
  const [tweets, setTweets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nextToken, setNextToken] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [connected, setConnected] = useState(false);
  const loaderRef = useRef(null);
  const POSTS_PER_PAGE = 20;
  const initialLoadComplete = useRef(false);
  const preventAutoFetch = useRef(false);  // New ref to prevent auto-fetch
  const selectedDisasterRef = useRef(selectedDisaster); // Reference to track changes

  // Debug logging for props
  useEffect(() => {
    console.log("TweetFeed component received selectedDisaster:", selectedDisaster);
  }, [selectedDisaster]);

  // Connect to WebSocket when component mounts - ONLY ONCE
  useEffect(() => {
    // Skip if already connected
    if (connected) return;

    if (!WEBSOCKET_URL) {
      console.error("WebSocket URL is not defined");
      return;
    }

    const connectWebSocket = async () => {
      try {
        console.log("Attempting to connect to WebSocket:", WEBSOCKET_URL);
        await websocketService.connect(WEBSOCKET_URL);
        setConnected(true);

        // Subscribe to the selected disaster type
        websocketService.subscribeToDisasterType(selectedDisaster);
        console.log("WebSocket connected and subscribed to:", selectedDisaster);
      } catch (error) {
        console.error("WebSocket connection failed:", error);
        setConnected(false);
        // Don't let WebSocket failure prevent initial data load
      }
    };

    connectWebSocket();

    // Cleanup: disconnect when component unmounts
    return () => {
      if (websocketService && typeof websocketService.disconnect === 'function') {
        websocketService.disconnect();
      }
    };
  }, []); // IMPORTANT: Empty dependency array - connect ONLY ONCE

  // Subscribe to different disaster type when selection changes
  useEffect(() => {
    // Update the ref whenever selectedDisaster changes
    selectedDisasterRef.current = selectedDisaster;

    if (connected && websocketService && typeof websocketService.subscribeToDisasterType === 'function') {
      websocketService.subscribeToDisasterType(selectedDisaster);
      console.log("Subscribed to disaster type:", selectedDisaster);
    }
  }, [selectedDisaster, connected]);

  // Listen for new posts from WebSocket
  useEffect(() => {
    // Skip if not connected
    if (!connected || !websocketService || typeof websocketService.addEventListener !== 'function') {
      return () => {};
    }

    // Handler for new posts
    const handleNewPost = (post) => {
      console.log("Received new post via WebSocket:", post);

      // Filter by selected disaster if needed
      if (selectedDisasterRef.current !== 'all' && post.disaster_type !== selectedDisasterRef.current) {
        console.log("Filtering out post of type:", post.disaster_type);
        return;
      }

      // Format the post for display
      const formattedPost = {
        uri: post.post_id,
        handle: post.handle || post.username || '',
        display_name: post.display_name || 'Unknown User',
        text: post.text || post.original_text || '',
        timestamp: post.timestamp || post.created_at || new Date().toISOString(),
        avatar: post.avatar || post.avatar_url || '/default-avatar.jpg',
        disaster_type: post.disaster_type || 'unknown',
        confidence_score: post.confidence_score || 0,
        is_disaster: true
      };

      // Add the new post to the beginning of the list
      setTweets(prevTweets => {
        // Check if this post already exists in our list
        const exists = prevTweets.some(tweet => tweet.uri === formattedPost.uri);
        if (exists) {
          console.log("Post already exists, not adding:", formattedPost.uri);
          return prevTweets; // No change needed
        }

        console.log("Adding new post to tweets list:", formattedPost.uri);
        // Add to the beginning of the array (newest first)
        return [formattedPost, ...prevTweets];
      });
    };

    // Register event handler for new posts
    console.log("Setting up WebSocket event listener for new posts");
    const unsubscribe = websocketService.addEventListener('new_post', handleNewPost);

    // Clean up event handler when component unmounts
    return unsubscribe;
  }, [connected]);

  // Fetch initial tweets
  const fetchTweets = useCallback(async (isInitialLoad = false, loadMore = false) => {
    try {
      if (isInitialLoad) {
        setLoading(true);
        // Only reset state when we're explicitly loading the first page
        setTweets([]);
        setNextToken(null);
        setHasMore(true);
        preventAutoFetch.current = false; // Enable fetching for the initial load
      }

      setError(null);

      // Use the api module to fetch posts with selected disaster type
      const token = isInitialLoad ? null : nextToken;
      console.log(`Fetching tweets: isInitialLoad=${isInitialLoad}, token=${token}, type=${selectedDisasterRef.current}`);
      const data = await api.getPosts(selectedDisasterRef.current, POSTS_PER_PAGE, token);

      console.log("API response:", data);

      // Check if we have valid data
      if (!data || !data.posts || !Array.isArray(data.posts)) {
        console.error("Invalid data format returned from API:", data);
        throw new Error("Invalid data format returned from API");
      }

      if (data.posts.length === 0) {
        console.log("No posts returned from API");
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
      if (token && !isInitialLoad) {
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
      initialLoadComplete.current = true;

    } catch (error) {
      console.error("Error fetching tweets:", error);
      setError(error.message || "Failed to load tweets. Please try again.");
      setLoading(false);
      setHasMore(false);

      // If the initial load fails, we should still mark it as complete
      // but allow future attempts to load data
      initialLoadComplete.current = true;
    }
  }, [nextToken, selectedDisaster]); // Add selectedDisaster to dependencies

  // Dedicated effect for initial data loading when component mounts
  useEffect(() => {
    console.log("Component mounted - triggering initial data load");
    fetchTweets(true);
    // We don't need any dependencies here - this should run exactly once when mounted
  }, []); // Empty dependency array means this runs once on mount

  // Effect for handling disaster type changes
  useEffect(() => {
    // Skip first render (this is handled by the mount effect above)
    if (!initialLoadComplete.current) return;

    console.log("Disaster type changed:", selectedDisaster);

    // Skip if we're in the middle of loading
    if (loading) {
      console.log("Already loading, skipping fetch for type change");
      return;
    }

    // Refresh the data when disaster type changes
    if (selectedDisasterRef.current !== selectedDisaster) {
      console.log(`Disaster type changed from ${selectedDisasterRef.current} to ${selectedDisaster}`);
      fetchTweets(true); // Reset and load first page only
    }
  }, [selectedDisaster, loading, fetchTweets]);

  // Explicit "load more" handler for infinite scrolling - manually triggered only
  const handleLoadMore = useCallback(() => {
    if (!loading && hasMore) {
      console.log("Manually loading more tweets");
      fetchTweets(false, true);
    }
  }, [fetchTweets, loading, hasMore]);

  // Set up intersection observer for infinite scrolling
  useEffect(() => {
    // If we're already loading or there are no more tweets, don't do anything
    if (loading || !hasMore || !loaderRef.current || !initialLoadComplete.current) return;

    // Keep a reference to the current loader element
    const currentLoaderRef = loaderRef.current;

    const observer = new IntersectionObserver(
        entries => {
          // If the loader element is visible and we're not already loading
          if (entries[0].isIntersecting && hasMore && !loading) {
            handleLoadMore(); // Use the explicit load more handler
          }
        },
        { threshold: 0.5 } // Fire when 50% of the element is visible
    );

    // Start observing the loader element
    observer.observe(currentLoaderRef);

    // Clean up the observer when component unmounts or dependencies change
    return () => {
      observer.unobserve(currentLoaderRef);
    };
  }, [loading, hasMore, handleLoadMore]);

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