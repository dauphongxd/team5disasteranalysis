// components/Footer.js
import React from "react";
import githubLogo from "./github.svg";
import email from "./mail.svg";


function Footer({ selectedDisaster = "all" }) {
    // Add emergency hotlines that are always shown
    const emergencyHotlines = [
        { text: "Emergency: 911", url: null },
        { text: "FEMA Helpline: 1-800-621-3362", url: "https://www.fema.gov/about/contact" },
        { text: "Disaster Distress Helpline: 1-800-985-5990", url: "https://www.samhsa.gov/find-help/disaster-distress-helpline" },
        { text: "Red Cross: 1-800-RED-CROSS", url: "https://www.redcross.org/contact-us.html" },
    ];

    return (
        <footer className="app-footer">
            <div className="footer-content">
                <div className="emergency-row">
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
                    <div className="connect-section">
                        <h3>Connect with Us</h3>
                        <div className="about-info">
                            <p>Learn more about our team and our projects.</p>
                        </div>
                        <div className="logo-container">
                            <a href="/Team5.pdf" target="_blank" rel="noopener noreferrer" className="logo-link about-link">
                                About
                            </a>
                            <a href="https://github.com/dauphongxd/team5disasteranalysis" target="_blank" rel="noopener noreferrer" className="logo-link">
                                <img src={githubLogo} alt="GitHub Logo" className="logo" />
                            </a> 
                            <a
                                href="#"
                                onClick={(e) => {
                                    e.preventDefault();
                                    navigator.clipboard.writeText("axd200083@utdallas.edu"); //Ashish email

                                    // Create banner
                                    const banner = document.createElement("div");
                                    banner.textContent = "Email copied!";
                                    banner.className = "banner-message"; // Add class for styling
                                    document.body.appendChild(banner);

                                    // Remove banner after 2 seconds
                                    setTimeout(() => banner.remove(), 2000);
                                }}
                                className="logo-link"
                                >
                                <img src={email} alt="copy email" className="logo" />
                                </a>

                        </div>
                        
                    </div>
                            
                    
                </div>

                <div className="footer-info">
                    <p className="footer-note">
                        Disaster Watch provides real-time updates on natural disasters from various sources.
                        This information is intended for educational and awareness purposes only. Always follow
                        official guidance from local authorities during emergencies.
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