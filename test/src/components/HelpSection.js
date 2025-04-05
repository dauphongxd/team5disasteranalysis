import React from "react";

function HelpSection({ selectedDisaster }) {
  // Note: The prop name should be selectedDisaster to match what App.js is passing

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

  // Always show general disaster resources
  const generalResources = resources.all;

  return (
      <div className="help-section">
        <h2>Emergency Resources & Help</h2>
        <div className="help-grid">
          <div className="help-category">
            <h3>{generalResources.title}</h3>
            {generalResources.links.length > 0 ? (
                <ul>
                  {generalResources.links.map((link, index) => (
                      <li key={index}>
                        <a href={link.url} target="_blank" rel="noopener noreferrer">
                          {link.text}
                        </a>
                      </li>
                  ))}
                </ul>
            ) : (
                <p>No resources available for this category.</p>
            )}
          </div>
        </div>
      </div>
  );
}

export default HelpSection;