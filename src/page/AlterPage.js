import React, { useState, useRef, useEffect } from "react";
import CitationCard from "../component/CitationCard";
import { useWallet } from "../contexts/WalletContext";
import { retractPaper, createContractInstance } from "../utils/web3";
import { hashHashedDoi, calculateRegistrationData, bytesToHex } from "../utils/merkle";
import "./AlterPage.css";

const CitationAlterPage = () => {
  const { walletConnected, connectWallet, signer, formattedAddress } = useWallet();

  const [searchDoi, setSearchDoi] = useState("");
  const [foundCitation, setFoundCitation] = useState({
    doi: "",
    docId: null,
    isRetracted: false,
  });
  const [newCitation, setNewCitation] = useState({
    doi: "",
    title: "",
    author: "",
    date: "",
    abstract: "",
    journal: "",
  });
  const [statusMessage, setStatusMessage] = useState(
    walletConnected ? "Enter DOI to search for existing citation." : "Please connect your wallet to edit citations."
  );

  const [isLoading, setIsLoading] = useState(false);

  const inputRef = useRef(null);

  // Search functionality for finding papers by DOI
  const handleSearchInput = (e) => {
    const value = e.target.value;
    setSearchDoi(value);
  };

  /**
   * Search for citation by DOI using smart contract
   */
  const fetchCitation = async (doi) => {
    try {
      if (!walletConnected || !signer) {
        setStatusMessage("Please connect your wallet first.");
        return;
      }

      setStatusMessage("Searching for citation...");
      setIsLoading(true);

      // Create contract instance
      const contract = await createContractInstance(signer);

      // Hash the DOI to match blockchain storage format (using new canonicalization)
      const hashedDoiBytes = hashHashedDoi(doi);
      const hashedDoiHex = bytesToHex(hashedDoiBytes);

      // Query smart contract for docId
      const docIdBigInt = await contract.getDocIdByDoi(hashedDoiHex);
      const docId = Number(docIdBigInt);

      if (docId && docId > 0) {
        // Get paper details including retraction status
        const [, , isRetracted] = await contract.getPaper(docId);

        setFoundCitation({
          doi,
          docId,
          isRetracted,
        });

        setStatusMessage(`Citation found (ID: ${docId}). Ready for update.`);
      } else {
        setFoundCitation({
          doi: "",
          docId: null,
          isRetracted: false,
        });
        setStatusMessage("Citation not found in registry.");
      }
    } catch (error) {
      console.error("Citation search error:", error);
      setStatusMessage(`Search failed: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEnterDoi = () => {
    if (searchDoi.trim()) {
      fetchCitation(searchDoi.trim());
    } else {
      setStatusMessage("Please enter a DOI to proceed.");
    }
  };

  // add alter function
  const handleAlter = async () => {
    if (!walletConnected || !signer) {
      setStatusMessage("Please connect your wallet first.");
      return;
    }

    if (!foundCitation.docId) {
      setStatusMessage("No citation found to alter.");
      return;
    }

    // Check if current citation is already retracted
    if (foundCitation.isRetracted) {
      setStatusMessage("This paper has already been retracted. Cannot alter an already retracted citation.");
      return;
    }

    // Validate new citation fields
    if (!newCitation.doi.trim() || !newCitation.title.trim() || !newCitation.author.trim() || !newCitation.date.trim()) {
      setStatusMessage("Please fill in all required fields (DOI, Title, Author, Date) for the new citation.");
      return;
    }

    // Check if new DOI is the same as old DOI
    if (newCitation.doi.trim() === foundCitation.doi.trim()) {
      setStatusMessage("New DOI must be different from the current DOI. Use a different DOI for the updated citation.");
      return;
    }

    try {
      setIsLoading(true);
      setStatusMessage("Validating new citation...");

      // Pre-validate new citation by checking if DOI already exists
      const registrationData = await calculateRegistrationData(newCitation, signer);
      const contract = await createContractInstance(signer);

      // Check if new DOI would conflict
      const existingDocId = await contract.getDocIdByDoi(registrationData.transactionData.hashedDoi);
      if (existingDocId && Number(existingDocId) > 0) {
        throw new Error(`DOI "${newCitation.doi}" is already registered in the system. Use a different DOI.`);
      }

      setStatusMessage("Retracting original citation...");

      // Get the current paper's metadata root from blockchain for validation
      const [currentMetadataRoot] = await contract.getPaper(foundCitation.docId);

      // Step 1: Retract the original citation with proper metadata validation
      const retractResult = await retractPaper(foundCitation.docId, signer, currentMetadataRoot);

      if (!retractResult.success) {
        throw new Error("Failed to retract original citation");
      }

      setStatusMessage("Registering new citation...");

      // Step 2: Register the new citation
      const tx = await contract.registerPaper(
        registrationData.transactionData.hashedDoi,
        registrationData.transactionData.hashedTad,
        registrationData.transactionData.metadataRoot,
        registrationData.transactionData.fulltextRoot
      );

      await tx.wait();

      // Success
      setStatusMessage(
        `Citation successfully altered! Original citation retracted and new citation registered. Retraction Hash: ${retractResult.transactionHash.slice(0, 10)}...${retractResult.transactionHash.slice(-8)}. Addition Hash: ${tx.hash.slice(0, 10)}...${tx.hash.slice(-8)}`
      );
    } catch (error) {
      console.error("Citation alteration error:", error);

      // Provide more specific error messages based on common issues
      let errorMessage = error.message;
      if (error.message.includes('REGISTRAR_ROLE')) {
        errorMessage = "Permission denied: Your account needs the REGISTRAR_ROLE to alter citations.";
      } else if (error.message.includes('DOI already registered')) {
        errorMessage = "The new DOI is already registered in the system. Use a different DOI.";
      } else if (error.message.includes('already retracted')) {
        errorMessage = "The original citation has already been retracted. Cannot alter an already retracted citation.";
      } else if (error.message.includes('user rejected')) {
        errorMessage = "Transaction cancelled: You rejected the transaction in your wallet.";
      } else if (error.message.includes('insufficient funds')) {
        errorMessage = "Insufficient funds: Not enough ETH to pay for gas fees.";
      } else {
        errorMessage = `Alteration failed: ${error.message}`;
      }

      setStatusMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Cancel function
  const handleCancel = () => {
    setSearchDoi("");
    setFoundCitation({ doi: "", docId: null, isRetracted: false });
    setNewCitation({ doi: "", title: "", author: "", date: "", abstract: "", journal: "" });
    setStatusMessage("Operation cancelled. Start again.");
  };

  // Determine status type for styling
  const getStatusType = (message) => {
    if (!message) return '';

    const lowerMessage = message.toLowerCase();

    // Success indicators
    if (lowerMessage.includes('successfully') ||
        lowerMessage.includes('registered') ||
        lowerMessage.includes('connected') ||
        lowerMessage.includes('verified') ||
        lowerMessage.includes('confirmed') ||
        lowerMessage.includes('altered') ||
        lowerMessage.includes('found') ||
        lowerMessage.includes('ready for editing')) {
      return 'success';
    }

    // Error indicators
    if (lowerMessage.includes('error') ||
        lowerMessage.includes('failed') ||
        lowerMessage.includes('denied') ||
        lowerMessage.includes('cancelled') ||
        lowerMessage.includes('already registered') ||
        lowerMessage.includes('does not exist') ||
        lowerMessage.includes('not found') ||
        lowerMessage.includes('insufficient funds') ||
        (lowerMessage.includes('please') && lowerMessage.includes('connect')) ||
        lowerMessage.includes('already retracted') ||
        lowerMessage.includes('different from')) {
      return 'error';
    }

    // Warning indicators
    if (lowerMessage.includes('warning') ||
        lowerMessage.includes('checking') ||
        lowerMessage.includes('processing') ||
        lowerMessage.includes('waiting') ||
        lowerMessage.includes('searching') ||
        lowerMessage.includes('verifying') ||
        lowerMessage.includes('retracting') ||
        lowerMessage.includes('validating')) {
      return 'warning';
    }

    return '';
  };

  // Update status message when wallet connection changes
  useEffect(() => {
    if (walletConnected) {
      if (statusMessage === "Please connect your wallet to edit citations.") {
        setStatusMessage("Enter DOI to search for existing citation.");
      }
    } else {
      setStatusMessage("Please connect your wallet to edit citations.");
    }
  }, [walletConnected, statusMessage]);

  const currentFields = [
    { name: "doi", label: "DOI", value: foundCitation.doi, onChange: (e) => { setFoundCitation({ ...foundCitation, doi: e.target.value }); } },
  ];

  const newFields = [
    { name: "doi", label: "DOI", value: newCitation.doi, onChange: (e) => { setNewCitation({ ...newCitation, doi: e.target.value }); } },
    { name: "title", label: "Title", value: newCitation.title, onChange: (e) => { setNewCitation({ ...newCitation, title: e.target.value }); } },
    { name: "author", label: "Author", value: newCitation.author, onChange: (e) => { setNewCitation({ ...newCitation, author: e.target.value }); } },
    { name: "date", label: "Date", type: "date", value: newCitation.date, onChange: (e) => { setNewCitation({ ...newCitation, date: e.target.value }); } },
    { name: "abstract", label: "Abstract", value: newCitation.abstract, onChange: (e) => { setNewCitation({ ...newCitation, abstract: e.target.value }); } },
    { name: "journal", label: "Journal", value: newCitation.journal, onChange: (e) => { setNewCitation({ ...newCitation, journal: e.target.value }); } },
  ];

  return (
    <div className="citation-alter-page">
      <h2 className="page-title">Update Citation</h2>

      {/* Wallet Connection Section */}
      {!walletConnected ? (
        <div className="wallet-section">
          <button
            onClick={connectWallet}
            disabled={isLoading}
            className="wallet-connect-btn"
          >
            {isLoading ? "Connecting..." : "Connect Wallet"}
          </button>
        </div>
      ) : (
        <div className="wallet-section">
          <div className="wallet-connected-info">
            <p>
              <strong>Connected:</strong> {formattedAddress}
            </p>
            <button
              onClick={connectWallet}
              disabled={isLoading}
              className="wallet-reconnect-btn"
            >
              Reconnect Wallet
            </button>
          </div>
        </div>
      )}

      
      {/* DOI Entry Section */}
      {walletConnected && (
        <div className="citation-search" ref={inputRef}>
          <label>Enter DOI</label>
          <div className="search-input-container">
            <input
              type="text"
              placeholder="Enter DOI (e.g., arXiv:2510.00294)"
              value={searchDoi}
              onChange={handleSearchInput}
              onKeyPress={(e) => e.key === 'Enter' && handleEnterDoi()}
              className="search-input-field"
            />
          </div>
        </div>
      )}

      {/* Citation Cards */}
      {walletConnected && (
        <div className="citation-cards-container">
          <div className="citation-card-left">
            <CitationCard
              title="Current Citation"
              fields={currentFields}
              extraButtons={[{ text: "Clear", onClick: handleCancel, className: "clear-btn" }]}
            />
          </div>
          <div className="citation-card-right">
            <CitationCard
              title="New Citation"
              fields={newFields}
              buttonText="Update"
              onActionClick={handleAlter}
              extraButtons={[{ text: "Clear", onClick: handleCancel, className: "clear-btn" }]}
            />
          </div>
        </div>
      )}

      {/* Status Message - Moved to bottom */}
      {(statusMessage && !walletConnected) || (walletConnected && statusMessage) ? (
        <div className={`status-box ${getStatusType(statusMessage)}`}>
          <p>{statusMessage}</p>
        </div>
      ) : null}
    </div>
  );
};

export default CitationAlterPage;