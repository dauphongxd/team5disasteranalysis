// components/Footer.js
import React from "react";

function Footer({ selectedDisaster = "all" }) {
    // Define the resource links with titles and links
    const resources = {
        fire: {
            title: "🔥 Wildfire Safety",
            links: [
                { text: "Wildfire Safety Tips (Ready.gov)", url: "https://www.ready.gov/wildfires" },
                { text: "Red Cross Wildfire Safety", url: "https://www.redcross.org/get-help/how-to-prepare-for-emergencies/types-of-emergencies/wildfire.html" },
            ],
        },
        storm: {
            title: "🌩 Storm Safety",
            links: [
                { text: "Storm Preparedness (Ready.gov)", url: "https://www.ready.gov/storms" },
                { text: "NOAA Storm Resources", url: "https://www.noaa.gov/" },
            ],
        },
        earthquake: {
            title: "🌍 Earthquake Safety",
            links: [
                { text: "Earthquake Safety (Ready.gov)", url: "https://www.ready.gov/earthquakes" },
                { text: "USGS Earthquake Hazards", url: "https://earthquake.usgs.gov/" },
            ],
        },
        tsunami: {
            title: "🌊 Tsunami Safety",
            links: [
                { text: "Tsunami Preparedness (Ready.gov)", url: "https://www.ready.gov/tsunamis" },
                { text: "NOAA Tsunami Program", url: "https://www.tsunami.noaa.gov/" },
            ],
        },
        volcano: {
            title: "🌋 Volcano Safety",
            links: [
                { text: "Volcano Preparedness (Ready.gov)", url: "https://www.ready.gov/volcanoes" },
                { text: "USGS Volcano Hazards", url: "https://volcanoes.usgs.gov/" },
            ],
        },
        flood: {
            title: "🌊 Flood Safety",
            links: [
                { text: "Flood Safety Tips (Ready.gov)", url: "https://www.ready.gov/floods" },
                { text: "Red Cross Flood Preparedness", url: "https://www.redcross.org/get-help/how-to-prepare-for-emergencies/types-of-emergencies/flood.html" },
            ],
        },
        landslide: {
            title: "⛰ Landslide Safety",
            links: [
                { text: "Landslide Safety Tips (Ready.gov)", url: "https://www.ready.gov/landslides-debris-flow" },
                { text: "USGS Landslide Hazards", url: "https://www.usgs.gov/natural-hazards/landslide-hazards" },
            ],
        },
        other: {
            title: "📋 General Disaster Preparedness",
            links: [
                { text: "General Disaster Preparedness (Ready.gov)", url: "https://www.ready.gov/" },
                { text: "Red Cross Emergency Preparedness", url: "https://www.redcross.org/get-help/how-to-prepare-for-emergencies.html" },
            ],
        },
        all: {
            title: "📋 General Disaster Resources",
            links: [
                { text: "General Disaster Preparedness (Ready.gov)", url: "https://www.ready.gov/" },
                { text: "Red Cross Emergency Preparedness", url: "https://www.redcross.org/get-help/how-to-prepare-for-emergencies.html" },
            ],
        },
    };

    // Get the resources for the selected disaster type
    const selectedResources = resources[selectedDisaster] || resources.all;

    // Add emergency hotlines that are always shown
    const emergencyHotlines = [
        { text: "National Emergency: 911", url: null },
        { text: "FEMA Helpline: 1-800-621-3362", url: "https://www.fema.gov/about/contact" },
        { text: "Disaster Distress Helpline: 1-800-985-5990", url: "https://www.samhsa.gov/find-help/disaster-distress-helpline" },
    ];

    return (
        <footer className="app-footer">
            <div className="footer-content">
                <div className="emergency-resources">
                    <div className="resources-column emergency-hotlines">
                        <h3>Emergency Hotlines</h3>
                        <ul>
                            {emergencyHotlines.map((link, index) => (
                                <li key={index}>
                                    {link.url ? (
                                        <a href={link.url} target="_blank" rel="noopener noreferrer">
                                            {link.text}
                                        </a>
                                    ) : (
                                        <span>{link.text}</span>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className="resources-column disaster-specific">
                        <h3>{selectedResources.title}</h3>
                        <ul>
                            {selectedResources.links.map((link, index) => (
                                <li key={index}>
                                    <a href={link.url} target="_blank" rel="noopener noreferrer">
                                        {link.text}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className="resources-column all-disasters">
                        <h3>Other Disaster Types</h3>
                        <div className="disaster-buttons">
                            {Object.keys(resources).map((type) =>
                                    type !== selectedDisaster && type !== 'all' && (
                                        <a
                                            key={type}
                                            href={resources[type].links[0].url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="disaster-type-btn"
                                        >
                                            {type.charAt(0).toUpperCase() + type.slice(1)}
                                        </a>
                                    )
                            )}
                        </div>
                    </div>
                </div>

                <div className="footer-info">
                    <p className="footer-note">
                        Disaster Watch provides real-time updates on natural disasters from various sources.
                        This information is intended for educational and awareness purposes only.
                    </p>
                    <p className="copyright">
                        © {new Date().getFullYear()} Disaster Watch
                    </p>
                </div>
            </div>
        </footer>
    );
}

export default Footer;