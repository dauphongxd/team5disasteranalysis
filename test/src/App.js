import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import Filters from "./components/Filters";
import MapSection from "./components/MapSection";
import TweetFeed from "./components/TweetFeed";
import Footer from "./components/Footer"; // Changed from HelpSection
import NWSDataViewer from "./components/NWSDataViewer";
import Scene from "./components/Scene";
import Timechart from "./components/Timechart";
import Donutchart from "./components/Donutchart";
import api from "./services/api"; // Import your existing API service
import "./styles.css";
import "./media.css";
import HelpSection from "./components/HelpSection";

function App() {
    const [selectedDisaster, setSelectedDisaster] = useState("all");
    const [disasterTypes, setDisasterTypes] = useState([]);
    const [showDataViewer, setShowDataViewer] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch available disaster types on component mount
    useEffect(() => {
        fetchDisasterTypes();
    }, []);

    const fetchDisasterTypes = async () => {
        try {
            setLoading(true);
            setError(null);

            // Use your api module
            const types = await api.getDisasterTypes();
            setDisasterTypes(types);
            setLoading(false);
        } catch (err) {
            console.error("Error fetching disaster types:", err);
            setError(err.message);
            setLoading(false);
        }
    };

    const toggleDataViewer = () => {
        setShowDataViewer(prev => !prev);
    };

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

                <br />

                {/* Pass selectedDisaster and setSelectedDisaster to Filters */}
                <Filters
                    setSelectedDisaster={setSelectedDisaster}
                    selectedDisaster={selectedDisaster}
                    availableTypes={disasterTypes}
                />

                <div className="main-content">
                    <div className="map-and-controls">
                        <MapSection 
                            showDataViewer={showDataViewer} 
                            toggleDataViewer={toggleDataViewer} 
                            NWSDataViewerComponent={NWSDataViewer}
                        />
                    </div>

                    {/* Pass selectedDisaster to TweetFeed */}
                    <TweetFeed selectedDisaster={selectedDisaster} />
                </div>

                <div>
                    {/* Pass selectedDisaster to Timechart */}
                    <Timechart selectedDisaster={selectedDisaster} />
                </div>

                <div>
                    <HelpSection selectedDisaster={selectedDisaster}/>
                </div>

                {/* Pass selectedDisaster to Donutchart */}
                <Donutchart selectedDisaster={selectedDisaster}/>
            </div>

            {/* Replace HelpSection with Footer */}
            <Footer selectedDisaster={selectedDisaster} />
        </>
    );
}

export default App;