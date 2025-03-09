import React from "react";
import Header from "./components/Header";
import Filters from "./components/Filters";
import MapSection from "./components/MapSection";
import TweetFeed from "./components/TweetFeed";
import HelpSection from "./components/HelpSection";
import Scene from "./components/Scene"; // Import the Three.js background
import "./styles.css";

function App() {
  return (
    <>
      {/* Render the Three.js background */}
      <Scene />

      {/* Main application content */}
      <div className="container">
        <div class="earth-container">
            <div class="earth"></div>
        </div>
        <Header />
        <Filters />
        <div className="main-content">
          <MapSection />
          <TweetFeed />
        </div>
        <HelpSection />
      </div>
    </>
  );
}

export default App;