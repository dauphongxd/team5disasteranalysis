// src/App.js
import React, { useState, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import Header from "./components/Header";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Scene from "./components/Scene";
import Dashboard from "./pages/Dashboard";
import NWSMapExplorer from "./pages/NWSMapExplorer";
import TweetFeedPage from "./pages/TweetFeedPage";
import Analytics from "./pages/Analytics";
import "./styles.css";

function App() {
    const [disasterData, setDisasterData] = useState([]);
    const [selectedDisaster, setSelectedDisaster] = useState("all");

    useEffect(() => {
        // Fetch the JSON file from the public folder for fallback data
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
    }, []);

    return (
        <>
            {/* Three.js background */}
            <Scene />

            <div className="app-container">
                <div className="content-wrapper">
                    {/* Earth animation */}
                    <div className="earth-container">
                        <div className="earth"></div>
                    </div>

                    <Header />
                    <Navbar />

                    <main className="main-container">
                        <Routes>
                            <Route
                                path="/"
                                element={
                                    <Dashboard
                                        disasterData={disasterData}
                                        selectedDisaster={selectedDisaster}
                                        setSelectedDisaster={setSelectedDisaster}
                                    />
                                }
                            />
                            <Route
                                path="/map"
                                element={
                                    <NWSMapExplorer />
                                }
                            />
                            <Route
                                path="/tweets"
                                element={
                                    <TweetFeedPage
                                        selectedDisaster={selectedDisaster}
                                        setSelectedDisaster={setSelectedDisaster}
                                    />
                                }
                            />
                            <Route
                                path="/analytics"
                                element={
                                    <Analytics
                                        disasterData={disasterData}
                                        selectedDisaster={selectedDisaster}
                                        setSelectedDisaster={setSelectedDisaster}
                                    />
                                }
                            />
                        </Routes>
                    </main>
                </div>

                {/* Footer with emergency resources */}
                <Footer selectedDisaster={selectedDisaster} />
            </div>
        </>
    );
}

export default App;