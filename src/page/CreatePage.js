import React, { useState, useRef, useEffect } from "react";
import CitationCard from "../component/CitationCard";
import "./AlterPage.css";

const CreatePage = () => {
  const [doi, setDoi] = useState("");
  const [title, setTitle] = useState("");
  const [authors, setAuthors] = useState("");
  const [date, setDate] = useState("");
  const [abstract, setAbstract] = useState("");
  const [journal, setJournal] = useState("");

  const [statusMessage, setStatusMessage] = useState(
    "Fill in the citation details and click 'Create'."
  );

  const [showPopup, setShowPopup] = useState(false);
  const [popupData, setPopupData] = useState(null);
  const popupRef = useRef(null);

  const addCitationToBlockchain = async (citationData) => {
    try {
      console.log("Sending to blockchain API:", citationData);
      return true;
    } catch (error) {
      console.error("Blockchain error:", error);
      return false;
    }
  };

  const handleCreate = async () => {
    const citationData = { doi, title, authors, date, abstract, journal };
    setStatusMessage("Adding citation to blockchain...");
    const success = await addCitationToBlockchain(citationData);

    if (success) {
      setPopupData(citationData);
      setShowPopup(true);
      setStatusMessage(
        "Citation successfully added to blockchain! To continue, enter another citation’s details and click Create."
      );

      setDoi("");
      setTitle("");
      setAuthors("");
      setDate("");
      setAbstract("");
      setJournal("");
    } else {
      setStatusMessage("Failed to add citation. Please try again.");
    }
  };

  const handleCancel = () => {
    setDoi("");
    setTitle("");
    setAuthors("");
    setDate("");
    setAbstract("");
    setJournal("");
    setStatusMessage("Operation cancelled. Start again.");
  };

  const closePopup = () => setShowPopup(false);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (popupRef.current && !popupRef.current.contains(event.target)) {
        setShowPopup(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const fields = [
    { name: "doi", label: "DOI", value: doi, onChange: (e) => setDoi(e.target.value), placeholder: "10.1109/SUMMA64428.2024.10803746" },
    { name: "title", label: "Title", value: title, onChange: (e) => setTitle(e.target.value), placeholder: "Utilizing Modern Large Language Models..." },
    { name: "authors", label: "Authors", value: authors, onChange: (e) => setAuthors(e.target.value), placeholder: "Andrei Lazarev, Dmitrii Sedov" },
    { name: "date", label: "Date", type: "date", value: date, onChange: (e) => setDate(e.target.value) },
    { name: "abstract", label: "Abstract", value: abstract, onChange: (e) => setAbstract(e.target.value), placeholder: "Short summary of the paper..." },
    { name: "journal", label: "Journal", value: journal, onChange: (e) => setJournal(e.target.value), placeholder: "6th International Conference on Control Systems..." },
  ];

  return (
    <div className="citation-delete-page">
      <h2 className="page-title">Create New Citation</h2>

      <div className="status-box">
        <p>{statusMessage}</p>
      </div>

      <CitationCard
        title="Citation Details"
        fields={fields}
        buttonText="Create"
        onActionClick={handleCreate}
        extraButtons={[{ text: "Cancel", onClick: handleCancel }]}
      />

      {showPopup && popupData && (
        <div className="popup-overlay">
          <div className="popup-content" ref={popupRef}>
            <button onClick={closePopup} className="popup-close-x">×</button>
            <h3>Citation Added to Blockchain</h3>
            <p><strong>DOI:</strong> {popupData.doi}</p>
            <p><strong>Title:</strong> {popupData.title}</p>
            <p><strong>Authors:</strong> {popupData.authors}</p>
            <p><strong>Date:</strong> {popupData.date}</p>
            <p><strong>Journal:</strong> {popupData.journal}</p>
            <p><strong>Abstract:</strong> {popupData.abstract}</p>
            <button onClick={closePopup} className="popup-close-btn">Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CreatePage;
