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
          <button onClick={() => setActivePage("welcome")}>Welcome</button>
          <button onClick={() => setActivePage("create")}>Create</button>
          <button onClick={() => setActivePage("alter")}>Alter</button>
          <button onClick={() => setActivePage("delete")}>Delete</button>
          <button onClick={() => setActivePage("login")}>Login</button>
        </nav>
      </div>
    </header>
  );
};

export default Navbar;
