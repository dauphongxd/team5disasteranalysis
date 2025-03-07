import React, { useEffect, useState } from "react";

function TweetFeed() {
  const [tweets, setTweets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchTweets() {
      try {
        setLoading(true);
        const response = await fetch("http://localhost:5000/api/posts");
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const data = await response.json();
        setTweets(data);
        setError(null);
      } catch (error) {
        console.error("Error fetching tweets:", error);
        setError("Failed to load disaster data. Please try again later.");
      } finally {
        setLoading(false);
      }
    }

    fetchTweets();
    
    // Set up polling to refresh data
    const interval = setInterval(fetchTweets, 60000); // Refresh every minute
    
    return () => clearInterval(interval); // Clean up on unmount
  }, []);

  if (loading) return <div className="loading">Loading disaster data...</div>;
  if (error) return <div className="error-message">{error}</div>;

  return (
    <div className="tweet-feed" id="tweet-feed">
      {tweets.length === 0 ? (
        <div className="no-data">No disaster posts available at this time.</div>
      ) : (
        tweets.map((tweet) => (
          <div className="tweet-container" key={tweet.post_id}>
            <div className="tweet-header">
              <img 
                src={tweet.media && tweet.media.length > 0 ? tweet.media[0].media_url : "/default-avatar.png"} 
                alt="Profile" 
                className="profile-pic" 
                onError={(e) => { e.target.src = "/default-avatar.png" }}
              />
              <div>
                <strong>{tweet.username || "Unknown User"}</strong>
                <br />
                <small>{new Date(tweet.created_at).toLocaleString()}</small>
              </div>
            </div>
            <div className="tweet-content">
              <p>{tweet.original_text}</p>
              {tweet.media && tweet.media.length > 0 && (
                <img 
                  src={tweet.media[0].media_url} 
                  alt="Media content" 
                  className="tweet-media"
                  onError={(e) => { e.target.style.display = 'none' }}
                />
              )}
            </div>
            <div className="disaster-tag">
              {tweet.disaster_type}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

export default TweetFeed;