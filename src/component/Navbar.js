import React from "react";
import "./Navbar.css";

const Navbar = ({ setActivePage }) => {
  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-logo">
          Citation Verifier
        </div>
        <nav className="navbar-links">
          <button onClick={() => setActivePage("create")}>Register</button>
          <button onClick={() => setActivePage("alter")}>Update</button>
          <button onClick={() => setActivePage("delete")}>Retract</button>
          <button onClick={() => setActivePage("login")}>Admin</button>
        </nav>
      </div>
    </header>
  );
};

export default Navbar;
