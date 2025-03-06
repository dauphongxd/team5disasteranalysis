import React from "react";

function HelpSection() {
  return (
    <div className="help-section">
      <h2>Emergency Resources & Help</h2>
      <div className="help-grid">
        <div className="help-category">
          <h3>🌪 Hurricane Safety</h3>
          <ul>
            <li>
              <a href="https://www.ready.gov/hurricanes">FEMA Hurricane Preparedness</a>
            </li>
            <li>
              <a href="https://www.nhc.noaa.gov/">National Hurricane Center</a>
            </li>
            <li>
              <a href="https://www.redcross.org/get-help/how-to-prepare-for-emergencies/types-of-emergencies/hurricane.html">
                Red Cross Hurricane Safety
              </a>
            </li>
          </ul>
        </div>
        {/* Add other categories as needed */}
      </div>
    </div>
  );
}

export default HelpSection;
