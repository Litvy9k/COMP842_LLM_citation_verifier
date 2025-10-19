import React, { useState, useRef, useEffect } from "react";
import CitationCard from "../component/CitationCard";
import "./AlterPage.css"; 

const CitationDeletePage = () => {
  const [searchDoi, setSearchDoi] = useState("");
  const [foundCitation, setFoundCitation] = useState({
    doi: "",
    title: "",
    authors: "",
    date: "",
    abstract: "",
    journal: "",
  });
  const [statusMessage, setStatusMessage] = useState(
    "Enter DOI to search or manually enter citation details."
  );
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showPopup, setShowPopup] = useState(false);

  const inputRef = useRef(null);

  const mockDatabase = [
    "10.1109/SUMMA64428.2024.10803746",
    "10.2000/Blockchain-Research-Test",
    "10.3000/Citation-Example-2025",
  ];

  const handleSearchInput = (e) => {
  const value = e.target.value;
  setSearchDoi(value);

  const filtered = mockDatabase.filter((doi) =>
    doi.toLowerCase().includes(value.toLowerCase())
  );
  setSuggestions(filtered);
  setShowSuggestions(true);
};

  const handleSelectSuggestion = (doi) => {
    setSearchDoi(doi);
    setShowSuggestions(false);
    fetchCitation(doi);
  };

  const fetchCitation = (doi) => {
    setStatusMessage("Fetching citation...");
    setTimeout(() => {
      setFoundCitation({
        doi,
        title: "Sample Blockchain Citation",
        authors: "Jane Smith",
        date: "2025-10-20",
        abstract: "Short sample abstract for deletion demo.",
        journal: "6th International Conference on Control Systems",
      });
      setStatusMessage("Citation found. You may delete it below.");
    }, 700);
  };


  //add delete function if need remove time out
  const handleDelete = () => {
    setStatusMessage("Deleting citation...");
      setShowPopup(true);
      setStatusMessage("Citation deleted successfully.");
      setFoundCitation({ doi: "", title: "", authors: "", date: "", abstract: "", journal: "" });
      setSearchDoi("");

  };

  const handleCancel = () => {
    setSearchDoi("");
    setFoundCitation({ doi: "", title: "", authors: "", date: "", abstract: "", journal: "" });
    setSuggestions([]);
    setShowSuggestions(false);
    setShowPopup(false);
    setStatusMessage("Operation cancelled. Start again.");
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (inputRef.current && !inputRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const fields = [
    { name: "doi", label: "DOI", value: foundCitation.doi, onChange: (e) => setFoundCitation({ ...foundCitation, doi: e.target.value }) },
    { name: "title", label: "Title", value: foundCitation.title, onChange: (e) => setFoundCitation({ ...foundCitation, title: e.target.value }) },
    { name: "authors", label: "Authors", value: foundCitation.authors, onChange: (e) => setFoundCitation({ ...foundCitation, authors: e.target.value }) },
    { name: "date", label: "Date", value: foundCitation.date, onChange: (e) => setFoundCitation({ ...foundCitation, date: e.target.value }) },
    { name: "abstract", label: "Abstract", value: foundCitation.abstract, onChange: (e) => setFoundCitation({ ...foundCitation, abstract: e.target.value }) },
    { name: "journal", label: "Journal", value: foundCitation.journal, onChange: (e) => setFoundCitation({ ...foundCitation, journal: e.target.value }) },
  ];

  return (
    <div className="citation-alter-page">
      <h2 className="page-title">Delete Citation</h2>

      <div className="status-box">
        <p>{statusMessage}</p>
      </div>

      <div className="citation-search" ref={inputRef}>
        <label>Search DOI</label>
        <input
          type="text"
          placeholder="Enter DOI to search (e.g., 10.1109 or arXiv)"
          value={searchDoi}
          onChange={handleSearchInput}
        />
        {showSuggestions && suggestions.length > 0 && (
          <div className="suggestion-dropdown">
            {suggestions.map((s, i) => (
              <div key={i} className="suggestion-item" onClick={() => handleSelectSuggestion(s)}>
                {s}
              </div>
            ))}
          </div>
        )}
      </div>

      <CitationCard
        title="Citation Details"
        fields={fields}
        buttonText="Delete"
        onActionClick={handleDelete}
        extraButtons={[{ text: "Cancel", onClick: handleCancel }]}
      />

      {showPopup && (
        <div className="popup-overlay">
          <div className="popup-content">
            <button onClick={handleCancel} className="popup-close-x">×</button>
            <h3>Citation Deleted</h3>
            <p>The citation has been successfully removed from the registry.</p>
            <button onClick={handleCancel} className="popup-close-btn">Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CitationDeletePage;
