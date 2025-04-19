import React, { useState, useEffect, useCallback, useRef } from "react";
import api from "../services/api";
import websocketService from "../services/websocket";

// Disaster categories mapping for proper filtering
// Removed tsunami from mapping
const disasterCategoriesMapping = {
  fire: ["wild_fire", "bush_fire", "forest_fire"],
  storm: ["storm", "blizzard", "cyclone", "dust_storm", "hurricane", "tornado", "typhoon"],
  earthquake: ["earthquake"],
  volcano: ["volcano"],
  flood: ["flood"],
  landslide: ["landslide", "avalanche"],
  other: ["haze", "meteor", "unknown"]
};

// Helper function to normalize disaster types
const normalizeDisasterType = (type) => {
  if (!type) return '';
  return String(type).toLowerCase().replace(/[_-]/g, ' ').trim();
};

// Enhanced matching function
const checkDisasterTypeMatch = (postType, selectedType) => {
  // If post type is tsunami, never match
  if (postType && normalizeDisasterType(postType) === 'tsunami') {
    return false;
  }

  // If tsunami is selected, don't match any posts
  if (selectedType === 'tsunami') {
    return false;
  }

  // If no post type, match only with 'all' or 'other'
  if (!postType) {
    return selectedType === 'all' || selectedType === 'other';
  }

  // All category matches everything (except tsunami which is handled above)
  if (selectedType === 'all') {
    return true;
  }

  // Normalize both types for comparison
  const normalizedPostType = normalizeDisasterType(postType);
  const normalizedSelectedType = normalizeDisasterType(selectedType);

  // Check direct match
  if (normalizedSelectedType === normalizedPostType) {
    return true;
  }

  // Check for substring match
  if (normalizedPostType.includes(normalizedSelectedType) ||
      normalizedSelectedType.includes(normalizedPostType)) {
    return true;
  }

  // Check for match with super category
  if (disasterCategoriesMapping[selectedType]) {
    for (const subType of disasterCategoriesMapping[selectedType]) {
      const normalizedSubType = normalizeDisasterType(subType);

      // Check for substring match
      if (normalizedPostType.includes(normalizedSubType) ||
          normalizedSubType.includes(normalizedPostType)) {
        return true;
      }
    }
  }

  return false;
};

function TweetFeed({ selectedDisaster }) {
  // State variables
  const [tweets, setTweets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nextToken, setNextToken] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [connected, setConnected] = useState(false);

  // Refs for preventing unnecessary renders and API calls
  const loaderRef = useRef(null);
  const POSTS_PER_PAGE = 20;
  const initialLoadComplete = useRef(false);
  const selectedDisasterRef = useRef(selectedDisaster);
  const isInitialMount = useRef(true);
  const fetchingRef = useRef(false);
  const nextTokenRef = useRef(null);
  const currentOperationRef = useRef(null);
  const tweetsRef = useRef(tweets);
  const connectionAttemptedRef = useRef(false);

  // Update refs when state changes
  useEffect(() => {
    tweetsRef.current = tweets;
  }, [tweets]);

  // Update ref when selectedDisaster changes
  useEffect(() => {
    // Only reset state if disaster type actually changed
    if (selectedDisasterRef.current !== selectedDisaster) {
      console.log(`Disaster type changed from ${selectedDisasterRef.current} to ${selectedDisaster}`);
      selectedDisasterRef.current = selectedDisaster;

      // Clear tweets and pagination state when disaster type changes
      if (!isInitialMount.current) {
        setTweets([]);
        setNextToken(null);
        nextTokenRef.current = null;
        setHasMore(true);

        // Reset fetchingRef to allow new fetches
        fetchingRef.current = false;
      }
    }
  }, [selectedDisaster]);

  // FETCH TWEETS FUNCTION
  const fetchTweets = useCallback(async (isInitialLoad = false) => {
    // If tsunami is selected, don't fetch any tweets
    if (selectedDisasterRef.current === 'tsunami') {
      setLoading(false);
      setTweets([]);
      setHasMore(false);
      initialLoadComplete.current = true;
      return;
    }

    // Generate a unique operation ID to track this specific fetch
    const operationId = Date.now();
    currentOperationRef.current = operationId;

    // Prevent concurrent fetches or fetches while unmounting
    if (fetchingRef.current) {
      return;
    }

    fetchingRef.current = true;

    try {
      if (isInitialLoad) {
        setLoading(true);
        // Reset state for initial load
        setTweets([]);
        setNextToken(null);
        nextTokenRef.current = null;
        setHasMore(true);
      } else if (!hasMore) {
        // If there are no more tweets to load, exit early
        fetchingRef.current = false;
        return;
      }

      setError(null);

      const token = isInitialLoad ? null : nextTokenRef.current;

      // Force fresh data only on initial load
      const data = await api.getPosts(selectedDisasterRef.current, POSTS_PER_PAGE, token, isInitialLoad);

      // Check if this operation is still current (not superseded)
      if (currentOperationRef.current !== operationId) {
        fetchingRef.current = false;
        return;
      }

      if (!data || !data.posts || !Array.isArray(data.posts)) {
        throw new Error("Invalid data format returned from API");
      }

      // Format posts for display and filter out tsunami posts
      const formattedTweets = data.posts
          .filter(post => {
            const postType = post.disaster_type?.toLowerCase();
            return postType !== 'tsunami'; // Filter out tsunami posts
          })
          .map(post => ({
            uri: post.post_id,
            handle: post.handle || post.username || (post.user_id ? String(post.user_id).substring(0, 10) + '...' : ''),
            display_name: post.display_name?.trim() || post.handle || "Unknown User",
            text: post.original_text || post.clean_text || "",
            timestamp: post.created_at,
            avatar: post.avatar_url || "/default-avatar.jpg",
            disaster_type: post.disaster_type,
            confidence_score: post.confidence_score,
            is_disaster: true
          }));

      // Update state safely
      if (token && !isInitialLoad) {
        setTweets(prevTweets => {
          // Check for duplicates before adding
          const existingIds = new Set(prevTweets.map(t => t.uri));
          const newTweets = formattedTweets.filter(t => !existingIds.has(t.uri));
          return [...prevTweets, ...newTweets];
        });
      } else {
        setTweets(formattedTweets);
      }

      // Update pagination state
      if (data.next_token) {
        setNextToken(data.next_token);
        nextTokenRef.current = data.next_token;
        setHasMore(true);
      } else {
        setNextToken(null);
        nextTokenRef.current = null;
        setHasMore(false);
      }

      setLoading(false);
      initialLoadComplete.current = true;

    } catch (error) {
      console.error("Error fetching tweets:", error);
      setError(error.message || "Failed to load tweets. Please try again.");
      setLoading(false);
      setHasMore(false);
      initialLoadComplete.current = true;
    } finally {
      // Ensure we release the lock
      fetchingRef.current = false;
    }
  }, []); // Empty dependency array for stability

  // Connect to WebSocket once on component mount
  useEffect(() => {
    if (connectionAttemptedRef.current) return;
    connectionAttemptedRef.current = true;

    const connectToWebSocket = async () => {
      try {
        if (!connected && websocketService) {
          await websocketService.connect(process.env.REACT_APP_WEBSOCKET_URL || 'http://localhost:8000');
          setConnected(true);
          websocketService.subscribeToDisasterType(selectedDisasterRef.current);
        }
      } catch (error) {
        console.error("WebSocket connection error:", error);
        setConnected(false);
      }
    };

    connectToWebSocket();

    // Clean up on unmount
    return () => {
      setConnected(false);
    };
  }, []); // Empty dependency array - run once only

  // Update WebSocket subscription when disaster type changes
  useEffect(() => {
    if (connected && websocketService && websocketService.isSocketConnected()) {
      websocketService.subscribeToDisasterType(selectedDisaster);
    }
  }, [selectedDisaster, connected]);

  // Initial data load - only on mount
  useEffect(() => {
    // Set a small delay to avoid any race conditions with parent component renders
    const timer = setTimeout(() => {
      fetchTweets(true);
      isInitialMount.current = false;
    }, 100);

    return () => clearTimeout(timer);
  }, []); // Empty dependency array - run once on mount

  // Handle disaster type changes
  useEffect(() => {
    if (isInitialMount.current) return;

    // Small delay to avoid race conditions
    const timer = setTimeout(() => {
      // If we're already fetching, don't start another fetch
      if (fetchingRef.current) return;

      fetchTweets(true);
    }, 200);

    return () => clearTimeout(timer);
  }, [selectedDisaster, fetchTweets]);

  // Set up WebSocket event listeners
  useEffect(() => {
    if (!connected || !websocketService) {
      return () => {};
    }

    // Handler for new posts from WebSocket
    const handleNewPost = (post) => {
      if (!post) return;

      // Skip tsunami posts
      if (post.disaster_type && post.disaster_type.toLowerCase() === 'tsunami') {
        return;
      }

      // Check if this post matches our current filter
      if (!checkDisasterTypeMatch(post.disaster_type, selectedDisasterRef.current)) {
        return;
      }

      // Format post for display
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

      // Add to tweets if not a duplicate
      setTweets(prevTweets => {
        if (prevTweets.some(tweet => tweet.uri === formattedPost.uri)) {
          return prevTweets; // No change if already exists
        }
        return [formattedPost, ...prevTweets]; // Add to beginning
      });
    };

    // Register listener
    const unsubscribe = websocketService.addEventListener('new_post', handleNewPost);
    return unsubscribe;
  }, [connected]);

  // Load more tweets handler for infinite scrolling
  const handleLoadMore = useCallback(() => {
    if (loading || !hasMore || fetchingRef.current) return;
    fetchTweets(false);
  }, [loading, hasMore, fetchTweets]);

  // Set up intersection observer for infinite scrolling
  useEffect(() => {
    if (!loaderRef.current || loading || !hasMore || !initialLoadComplete.current) return;

    const currentLoader = loaderRef.current;
    const observer = new IntersectionObserver(
        entries => {
          if (entries[0].isIntersecting && hasMore && !loading && !fetchingRef.current) {
            handleLoadMore();
          }
        },
        { threshold: 0.5 }
    );

    observer.observe(currentLoader);
    return () => observer.unobserve(currentLoader);
  }, [loading, hasMore, handleLoadMore]);

  // Special case for tsunami - show empty state
  if (selectedDisaster === 'tsunami') {
    return (
        <div className="tweet-section">
          <div className="map-header">
            <h3> </h3>
          </div>
          <div className="tweet-feed">
            <div className="no-tweets-message">
              No disaster tweets found for this category
            </div>
          </div>
        </div>
    );
  }

  // Render loading state
  if (loading && tweets.length === 0) {
    return (
        <div className="tweet-section">
          <div className="map-header">
            <h3> </h3>
          </div>
          <div className="tweet-feed">
            <div className="loading-indicator">Loading disaster tweets...</div>
          </div>
        </div>
    );
  }

  // Render error state
  if (error && tweets.length === 0) {
    return (
        <div className="tweet-section">
          <div className="map-header">
            <h3> </h3>
          </div>
          <div className="tweet-feed">
            <div className="error-message">Error: {error}</div>
            <button onClick={() => fetchTweets(true)} className="retry-button">Retry</button>
          </div>
        </div>
    );
  }

  // Render main content
  return (
      <div className="tweet-section">
        <div className="map-header">
          <h3> </h3>
        </div>
        <div className="tweet-feed" id="tweet-feed">
          {tweets.length === 0 ? (
              <div className="no-tweets-message">
                No disaster tweets found for this category
              </div>
          ) : (
              <div className="tweet-content-wrapper">
                {tweets.map((tweet) => (
                    <div
                        className="tweet-container"
                        key={tweet.uri}
                    >
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

export default React.memo(TweetFeed);