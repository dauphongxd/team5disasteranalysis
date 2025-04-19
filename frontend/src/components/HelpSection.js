import React from "react";

function HelpSection({ selectedDisaster }) {
  // Define the resource links with titles and links
  // Removed tsunami resources
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

  // Show generic resources if tsunami is selected
  if (selectedDisaster === 'tsunami') {
    selectedDisaster = 'all';
  }

  // Get resources for the selected disaster type (or default to general resources)
  const selectedResources = resources[selectedDisaster] || resources.all;

  return (
      <div className="help-section">
        <h2>Emergency Resources & Help</h2>
        <div className="help-grid">
          <div className="help-category">
            <h3>{selectedResources.title}</h3>
            {selectedResources.links.length > 0 ? (
                <ul>
                  {selectedResources.links.map((link, index) => (
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