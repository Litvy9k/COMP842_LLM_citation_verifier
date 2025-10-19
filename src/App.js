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
    <div className="min-h-screen bg-gray-50 flex flex-col items-center">
      {/* Navbar at the top */}
      <Navbar setActivePage={setActivePage} />

      {/* Page container: content in middle, responsive width */}
      <div className="page-container p-6">
        {renderPage()}
      </div>
    </div>
  );
}

export default App;
