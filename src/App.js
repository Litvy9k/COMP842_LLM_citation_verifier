import React, { useState } from "react";
import Navbar from "./component/Navbar";
import WelcomePage from "./page/WelcomePage";
import CreatePage from "./page/CreatePage";
import AlterPage from "./page/AlterPage";
import DeletePage from "./page/DeletePage";
import LoginPage from "./page/LoginPage";
import './App.css';


function App() {
  const [activePage, setActivePage] = useState("welcome");

  // Decide which page to render
  const renderPage = () => {
    switch (activePage) {
      case "create":
        return <CreatePage />;
      case "alter":
        return <AlterPage />;
      case "delete":
        return <DeletePage />;
      case "login":
        return <LoginPage />;
      default:
        return <WelcomePage />;
    }
  };

  return (
    <div className="nav">
      <Navbar setActivePage={setActivePage} />
      <div className="page-container">
        {renderPage()}
      </div>
    </div>
  );
}

export default App;
