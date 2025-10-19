import React, { useState, useRef, useEffect } from "react";
import CitationCard from "../component/CitationCard";
import "./AlterPage.css";

const CitationAlterPage = () => {
  const [searchDoi, setSearchDoi] = useState("");
  const [foundCitation, setFoundCitation] = useState({
    doi: "",
    title: "",
    authors: "",
    date: "",
    abstract: "",
    journal: "",
  });
  const [newCitation, setNewCitation] = useState({
    doi: "",
    title: "",
    authors: "",
    date: "",
    abstract: "",
    journal: "",
  });
  const [statusMessage, setStatusMessage] = useState(
    "Enter DOI to search or manually enter citation details. If enter DOI manually please click 'Check' to verify."
  );
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showPopup, setShowPopup] = useState(false);
  const [isVerified, setIsVerified] = useState(false);
  const [popupData, setPopupData] = useState(null);

  const inputRef = useRef(null);
  const popupRef = useRef(null);

  //removable
  const mockDatabase = [
    "10.1109/SUMMA64428.2024.10803746",
    "10.2000/Blockchain-Research-Test",
    "10.3000/Citation-Example-2025",
  ];

  //same with delete add serch funtion
  const handleSearchInput = (e) => {
    const value = e.target.value;
    setSearchDoi(value);

    // this test on the mock data 
    const filtered = mockDatabase.filter((doi) =>
      doi.toLowerCase().includes(value.toLowerCase())
    );
    setSuggestions(filtered);
    setShowSuggestions(true);
  };

  const handleSelectSuggestion = (doi) => {
    setSearchDoi(doi);
    setShowSuggestions(false);
    fetchCitation(doi, true);
  };

  //add funtion to get citation
  const fetchCitation = (doi, autoVerify = false) => {
    setStatusMessage("Fetching citation from blockchain...");

    // replace function
    setTimeout(() => { 
      const fetchedCitation = {
        doi,
        title: "Sample Blockchain Citation",
        authors: "Jane Smith",
        date: "2025-10-20",
        abstract: "Short sample abstract for demonstration.",
        journal: "6th International Conference on Control Systems",
      };
      setFoundCitation(fetchedCitation);
      setStatusMessage(autoVerify
        ? "Citation found and verified. You can now edit the new citation."
        : "Citation found. Click Check to verify.");
      setIsVerified(autoVerify);
    }, 700);
  };

  //add funtion to check if the manual enter citaion match the record
  const handleCheck = () => {
    if (!foundCitation.doi) {
      setStatusMessage("Enter a DOI to verify.");
      return;
    }
    setStatusMessage("Verifying citation...");
      setIsVerified(true);
      setStatusMessage("Citation verified. You can now edit the new citation.");

  };

  // add alter funtion
  const handleAlter = () => {
    if (!isVerified) {
      setStatusMessage("Verify the current citation before altering.");
      return;
    }

    setStatusMessage("Altering citation on blockchain...");

    setTimeout(() => {
      // delete old citation
      console.log("Deleting old citation:", foundCitation);
      // create new citation
      console.log("Creating new citation:", newCitation);

      setPopupData(newCitation);
      setShowPopup(true);
      setStatusMessage("Citation successfully altered!");

      setFoundCitation({ doi: "", title: "", authors: "", date: "", abstract: "", journal: "" });
      setNewCitation({ doi: "", title: "", authors: "", date: "", abstract: "", journal: "" });
      setSearchDoi("");
      setIsVerified(false);
    }, 1000);
  };

  // Cancel function
  const handleCancel = () => {
    setSearchDoi("");
    setFoundCitation({ doi: "", title: "", authors: "", date: "", abstract: "", journal: "" });
    setNewCitation({ doi: "", title: "", authors: "", date: "", abstract: "", journal: "" });
    setSuggestions([]);
    setShowSuggestions(false);
    setIsVerified(false);
    setShowPopup(false);
    setPopupData(null);
    setStatusMessage("Operation cancelled. Start again.");
  };

  // pop up closing function
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (inputRef.current && !inputRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
      if (popupRef.current && !popupRef.current.contains(event.target)) {
        setShowPopup(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const currentFields = [
    { name: "doi", label: "DOI", value: foundCitation.doi, onChange: (e) => setFoundCitation({ ...foundCitation, doi: e.target.value }), placeholder: "Enter or select DOI" },
    { name: "title", label: "Title", value: foundCitation.title, onChange: (e) => setFoundCitation({ ...foundCitation, title: e.target.value }) },
    { name: "authors", label: "Authors", value: foundCitation.authors, onChange: (e) => setFoundCitation({ ...foundCitation, authors: e.target.value }) },
    { name: "date", label: "Date", value: foundCitation.date, onChange: (e) => setFoundCitation({ ...foundCitation, date: e.target.value }) },
    { name: "abstract", label: "Abstract", value: foundCitation.abstract, onChange: (e) => setFoundCitation({ ...foundCitation, abstract: e.target.value }) },
    { name: "journal", label: "Journal", value: foundCitation.journal, onChange: (e) => setFoundCitation({ ...foundCitation, journal: e.target.value }) },
  ];

  const newFields = [
    { name: "doi", label: "DOI", value: newCitation.doi, onChange: (e) => setNewCitation({ ...newCitation, doi: e.target.value }), disabled: !isVerified },
    { name: "title", label: "Title", value: newCitation.title, onChange: (e) => setNewCitation({ ...newCitation, title: e.target.value }), disabled: !isVerified },
    { name: "authors", label: "Authors", value: newCitation.authors, onChange: (e) => setNewCitation({ ...newCitation, authors: e.target.value }), disabled: !isVerified },
    { name: "date", label: "Date", type: "date", value: newCitation.date, onChange: (e) => setNewCitation({ ...newCitation, date: e.target.value }), disabled: !isVerified },
    { name: "abstract", label: "Abstract", value: newCitation.abstract, onChange: (e) => setNewCitation({ ...newCitation, abstract: e.target.value }), disabled: !isVerified },
    { name: "journal", label: "Journal", value: newCitation.journal, onChange: (e) => setNewCitation({ ...newCitation, journal: e.target.value }), disabled: !isVerified },
  ];

  return (
    <div className="citation-alter-page">
      <h2 className="page-title">Alter Citation</h2>

      <div className="status-box"><p>{statusMessage}</p></div>

      <div className="citation-search" ref={inputRef}>
        <label>Search DOI</label>
        <input
          type="text"
          placeholder="Enter DOI to search..."
          value={searchDoi}
          onChange={handleSearchInput}
        />
        {showSuggestions && suggestions.length > 0 && (
          <div className="suggestion-dropdown">
            {suggestions.map((s, i) => (
              <div key={i} className="suggestion-item" onClick={() => handleSelectSuggestion(s)}>{s}</div>
            ))}
          </div>
        )}
      </div>

      <CitationCard
        title="Current Citation"
        fields={currentFields}
        buttonText={foundCitation.doi && !isVerified ? "Check" : ""}
        onActionClick={handleCheck}
        extraButtons={[{ text: "Cancel", onClick: handleCancel }]}
      />

      <CitationCard
        title="New Citation"
        fields={newFields}
        buttonText="Alter"
        onActionClick={handleAlter}
        extraButtons={[{ text: "Cancel", onClick: handleCancel }]}
      />

      {showPopup && popupData && (
        <div className="popup-overlay">
          <div className="popup-content" ref={popupRef}>
            <button onClick={handleCancel} className="popup-close-x">×</button>
            <h3>Citation Successfully Altered</h3>
            <p>The new citation details:</p>
            <div className="popup-citation-details">
              <p><strong>DOI:</strong> {popupData.doi}</p>
              <p><strong>Title:</strong> {popupData.title}</p>
              <p><strong>Authors:</strong> {popupData.authors}</p>
              <p><strong>Date:</strong> {popupData.date}</p>
              <p><strong>Abstract:</strong> {popupData.abstract}</p>
              <p><strong>Journal:</strong> {popupData.journal}</p>
            </div>
            <button onClick={handleCancel} className="popup-close-btn">Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CitationAlterPage;
