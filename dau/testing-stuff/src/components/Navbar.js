// components/Navbar.js
import React, { useState } from "react";
import { NavLink } from "react-router-dom";

function Navbar() {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    const toggleMobileMenu = () => {
        setMobileMenuOpen(!mobileMenuOpen);
    };

    return (
        <nav className="navbar">
            <div className="navbar-container">
                {/* Main navigation links */}
                <div className={`nav-links ${mobileMenuOpen ? 'mobile-open' : ''}`}>
                    <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'} end>
                        Dashboard
                    </NavLink>
                    <NavLink to="/map" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                        Map & NWS Data
                    </NavLink>
                    <NavLink to="/tweets" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                        Disaster Tweets
                    </NavLink>
                    <NavLink to="/analytics" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                        Analytics
                    </NavLink>
                </div>

                {/* Mobile menu toggle button */}
                <button className="mobile-menu-button" onClick={toggleMobileMenu}>
                    {mobileMenuOpen ? '✕' : '☰'}
                </button>
            </div>
        </nav>
    );
}

export default Navbar;