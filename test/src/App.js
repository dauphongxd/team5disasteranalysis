import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import Filters from "./components/Filters";
import MapSection from "./components/MapSection";
import TweetFeed from "./components/TweetFeed";
import HelpSection from "./components/HelpSection";
import NWSDataViewer from "./components/NWSDataViewer";

import Scene from "./components/Scene"; // Import the Three.js background
import Timechart from "./components/Timechart";
import "./styles.css";

function App() {
  const [disasterData, setDisasterData] = useState([]); // State to store JSON data
  const [selectedDisaster, setSelectedDisaster] = useState("all");
  const [showDataViewer, setShowDataViewer] = useState(false);

  const toggleDataViewer = () => {
    setShowDataViewer(prev => !prev);
  };

  useEffect(() => {
    // Fetch the JSON file from the public folder
    fetch("/posts.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to fetch disaster data");
        }
        return response.json();
      })
      
      .then((data) => {
        const filteredData = data.filter((post) => post.is_disaster === true);
        setDisasterData(filteredData);
      })
      .catch((error) => {
        console.error("Error fetching disaster data:", error);
      });
  }, []); // Runs once when the component mounts

  console.log("Currently Selected Disaster:", selectedDisaster);

  return (
    <>
      {/* Render the Three.js background */}
      <Scene />

      {/* Main application content */}
      <div className="container">
        <div className="earth-container">
            <div className="earth"></div>
        </div>
        <Header />
        <div className="app-controls">
          <button 
            className={`control-button ${showDataViewer ? 'active' : ''}`} 
            onClick={toggleDataViewer}
          >
            {showDataViewer ? 'Hide NWS Data Viewer' : 'Show NWS Data Viewer'}
          </button>
        </div>
        <Filters setSelectedDisaster={setSelectedDisaster} />
        {showDataViewer && <NWSDataViewer />}
        <div className="main-content">
          <MapSection />
          <TweetFeed />
        </div>
        <div>
          <Timechart disasterData={disasterData} selectedDisaster={selectedDisaster} />
        </div>
        
        {/* Add the HelpSection component here */}
        <HelpSection disasterType={selectedDisaster} />
      </div>
    </>
  );
}

export default App;
