import React, { useEffect, useState } from "react";

function TweetFeed() {
  const [tweets, setTweets] = useState([]);

  useEffect(() => {
    async function fetchTweets() {
      try {
        const response = await fetch("/posts.json");
        const data = await response.json();
        const disasterTweets = data.filter(tweet => tweet.is_disaster);
        setTweets(disasterTweets);
      } catch (error) {
        console.error("Error fetching tweets:", error);
      }
    }

    fetchTweets();
  }, []);

  return (
    <div className="tweet-feed" id="tweet-feed">
      {tweets.map((tweet) => (
        <div className="tweet-container" key={tweet.uri}>
          <div className="tweet-header">
            <img src={tweet.avatar} alt="Profile Picture" className="profile-pic" />
            <div>
              <div>
                <strong>{tweet.display_name || "Unknown User"}</strong>
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
          <div className="disaster-tag" style={{ display: "none" }}>
            {tweet.predicted_disaster_type}
          </div>
        </div>
      ))}
    </div>
  );
}

export default TweetFeed;
