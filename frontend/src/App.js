import React from "react";
import Header from "./components/Header";
import Filters from "./components/Filters";
import MapSection from "./components/MapSection";
import TweetFeed from "./components/TweetFeed";
import HelpSection from "./components/HelpSection";
import "./styles.css";

function App() {
  return (
    <div className="container">
      <Header />
      <Filters />
      <div className="main-content">
        <MapSection />
        <TweetFeed />
      </div>
      <HelpSection />
    </div>
  );
}

export default App;
