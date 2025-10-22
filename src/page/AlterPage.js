import React, { useState, useRef, useEffect } from "react";
import CitationCard from "../component/CitationCard";
import { useWallet } from "../contexts/WalletContext";
import { retractPaper, createContractInstance, createReadOnlyContractInstance } from "../utils/web3";
import { hashHashedDoi, calculateValidationHashes, calculateRegistrationData, bytesToHex } from "../utils/merkle";
import "./AlterPage.css";

const CitationAlterPage = () => {
  const { walletConnected, connectWallet, signer, formattedAddress } = useWallet();

  const [searchDoi, setSearchDoi] = useState("");
  const [foundCitation, setFoundCitation] = useState({
    doi: "",
    title: "",
    authors: "",
    date: "",
    abstract: "",
    journal: "",
    docId: null,
    isRetracted: false,
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
    walletConnected ? "Enter DOI to search for existing citation." : "Please connect your wallet to edit citations."
  );
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
    const [isVerified, setIsVerified] = useState(false);
  const [alterTransactions, setAlterTransactions] = useState({ txRetract: null, txAdd: null });
  const [isLoading, setIsLoading] = useState(false);

  const inputRef = useRef(null);

  /**
   * Find paper data by DOI in the sample paper database for suggestions
   */
  const findPaperByDoi = (doi) => {
    return samplePapers.find(paper => paper.doi === doi);
  };

  // Search functionality for finding papers by DOI
  const handleSearchInput = (e) => {
    const value = e.target.value;
    setSearchDoi(value);

    // Generate suggestions from sample paper data
    if (value.trim()) {
      const filteredSuggestions = samplePapers
        .filter(paper => paper.doi.toLowerCase().includes(value.toLowerCase()))
        .map(paper => paper.doi)
        .slice(0, 5); // Limit to 5 suggestions
      setSuggestions(filteredSuggestions);
      setShowSuggestions(filteredSuggestions.length > 0);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  };

  // Sample papers loaded from paper.json
  const samplePapers = [
    {
      doi: "arXiv:2510.00083",
      title: "Enhancing Certifiable Semantic Robustness via Robust Pruning of Deep Neural Networks",
      authors: "Hanjiang Hu, Bowei Li, Ziwei Wang, Tianhao Wei, Casidhe Hutchison, Eric Sample, Changliu Liu",
      date: "2025-09-30",
      abstract: "Deep neural networks have been widely adopted in many vision and robotics applications with visual inputs. It is essential to verify its robustness against semantic transformation perturbations, such as brightness and contrast.",
      journal: "N/A"
    },
    {
      doi: "10.1109/SUMMA64428.2024.10803746",
      title: "Utilizing Modern Large Language Models (LLM) for Financial Trend Analysis and Digest Creation",
      authors: "Andrei Lazarev, Dmitrii Sedov",
      date: "2025-09-22",
      abstract: "The exponential growth of information presents a significant challenge for researchers and professionals seeking to remain at the forefront of their fields and this paper introduces an innovative framework for automatically generating insightful financial digests using the power of Large Language Models (LLMs), specifically Google's Gemini Pro.",
      journal: "2024 6th International Conference on Control Systems, Mathematical Modeling, Automation and Energy Efficiency (SUMMA), Lipetsk, Russian Federation, 2024, pp. 317-321"
    },
    {
      doi: "arXiv:2510.00442",
      title: "Randomized Matrix Sketching for Neural Network Training and Gradient Monitoring",
      authors: "Harbir Antil, Deepanshu Verma",
      date: "2025-10-01",
      abstract: "Neural network training relies on gradient computation through backpropagation, yet memory requirements for storing layer activations present significant scalability challenges. We present the first adaptation of control-theoretic matrix sketching to neural network layer activations, enabling memory-efficient gradient reconstruction in backpropagation.",
      journal: "N/A"
    }
  ];

  const handleQuickDemo = (samplePaper) => {
    setSearchDoi(samplePaper.doi);
    setShowSuggestions(false);
    setFoundCitation({
      doi: samplePaper.doi,
      title: samplePaper.title,
      authors: samplePaper.authors,
      date: samplePaper.date,
      abstract: samplePaper.abstract,
      journal: samplePaper.journal,
      docId: null,
      isRetracted: false,
    });
    setStatusMessage("Fill in all required fields (Title, Authors, Date) to validate.");
    setIsVerified(false);
  };

  const handleSelectSuggestion = (doi) => {
    setSearchDoi(doi);
    setShowSuggestions(false);
    setFoundCitation({
      doi: doi,
      title: "",
      authors: "",
      date: "",
      abstract: "",
      journal: "",
      docId: null,
      isRetracted: false,
    });
    setStatusMessage("Fill in all required fields (Title, Authors, Date) to validate.");
    setIsVerified(false);
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

        // Try to find real paper data for this DOI
        const realPaper = findPaperByDoi(doi);

        const fetchedCitation = {
          doi,
          title: realPaper ? realPaper.title : "",
          authors: realPaper ? realPaper.authors : "",
          date: realPaper ? realPaper.date : "",
          abstract: realPaper ? realPaper.abstract : "",
          journal: realPaper ? realPaper.journal : "",
          docId,
          isRetracted,
        };

        setFoundCitation(fetchedCitation);
        const dataStatus = realPaper ? "Citation details loaded from database." : "Fill in citation details manually for validation.";
        const allDataFilled = realPaper && realPaper.title && realPaper.authors && realPaper.date;
        setStatusMessage(`Citation found (ID: ${docId}). ${dataStatus} ${allDataFilled ? 'Click Validate to verify citation.' : 'Fill in all required fields (Title, Authors, Date) to validate.'}`);
        setIsVerified(false);
      } else {
        setFoundCitation({
          doi: "",
          title: "",
          authors: "",
          date: "",
          abstract: "",
          journal: "",
          docId: null,
          isRetracted: false,
        });
        setStatusMessage("Citation not found in registry.");
        setIsVerified(false);
      }
    } catch (error) {
      console.error("Citation search error:", error);
      setStatusMessage(`Search failed: ${error.message}`);
      setIsVerified(false);
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

  //add funtion to check if the manual enter citaion match the record
  const handleCheck = async () => {
    if (!foundCitation.doi) {
      setStatusMessage("Enter a DOI to verify.");
      return;
    }

    if (!foundCitation.title.trim() || !foundCitation.authors.trim() || !foundCitation.date.trim()) {
      setStatusMessage("Please fill in Title, Authors, and Date to verify citation identity.");
      return;
    }

    if (!walletConnected || !signer) {
      setStatusMessage("Please connect your wallet first.");
      return;
    }

    try {
      setStatusMessage("Verifying citation against blockchain...");

      // Calculate hashes for the entered citation data (no signature required for validation)
      const validationHashes = calculateValidationHashes(foundCitation);
      console.log("Validation hashes calculated:", validationHashes);

      // Use read-only contract for validation (no signing required)
      const contract = await createReadOnlyContractInstance();
      console.log("Read-only contract instance created");

      // Check if DOI matches the blockchain record
      const existingDocId = await contract.getDocIdByDoi(validationHashes.hashedDoi);
      console.log("Existing docId:", existingDocId.toString());

      if (!existingDocId || Number(existingDocId) === 0) {
        console.log("DOI not found in blockchain");
        setStatusMessage("Citation verification failed: DOI not found in blockchain registry.");
        return;
      }

      // Get the paper from blockchain
      const [metadataRoot, fullTextRoot, isRetracted] = await contract.getPaper(Number(existingDocId));
      console.log("Blockchain paper data:", { metadataRoot, fullTextRoot, isRetracted });
      console.log("Calculated metadataRoot:", validationHashes.metadataRoot);

      if (isRetracted) {
        setStatusMessage("Citation verification failed: This citation has been retracted.");
        return;
      }

      // Verify metadata matches
      if (metadataRoot !== validationHashes.metadataRoot) {
        console.log("Metadata mismatch detected");
        setStatusMessage("Citation verification failed: Metadata does not match blockchain record.");
        return;
      }

      console.log("Verification successful");
      setIsVerified(true);
      setStatusMessage("Current citation verified against blockchain. You can now update the citation.");

    } catch (error) {
      console.error("Citation verification error:", error);
      setStatusMessage(`Verification failed: ${error.message}`);
    }
  };

  // add alter funtion
  const handleAlter = async () => {
    if (!isVerified) {
      setStatusMessage("Verify the current citation before altering.");
      return;
    }

    if (!walletConnected || !signer) {
      setStatusMessage("Please connect your wallet first.");
      return;
    }

    if (!foundCitation.docId) {
      setStatusMessage("No citation found to alter.");
      return;
    }

    // Check if current citation is already retracted (no wallet operation needed)
    if (foundCitation.isRetracted) {
      setStatusMessage("This paper has already been retracted. Cannot alter an already retracted citation.");
      return;
    }

    // Validate new citation fields
    if (!newCitation.doi.trim() || !newCitation.title.trim() || !newCitation.authors.trim() || !newCitation.date.trim()) {
      setStatusMessage("Please fill in all required fields (DOI, Title, Authors, Date) for the new citation.");
      return;
    }

    // Check if new DOI is the same as old DOI
    if (newCitation.doi.trim() === foundCitation.doi.trim()) {
      setStatusMessage("New DOI must be different from the current DOI. Use a different DOI for the updated citation.");
      return;
    }

    // Additional validation: Check if Title+Authors+Date combination is the same
    const oldAuthors = Array.isArray(foundCitation.authors)
      ? foundCitation.authors.join(', ').trim()
      : foundCitation.authors.trim();
    const newAuthors = Array.isArray(newCitation.authors)
      ? newCitation.authors.join(', ').trim()
      : newCitation.authors.trim();

    if (newCitation.title.trim() === foundCitation.title.trim() &&
        newAuthors === oldAuthors &&
        newCitation.date.trim() === foundCitation.date.trim()) {
      setStatusMessage("New citation must have different Title, Authors, or Date than the current citation.");
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

      // Step 1: Retract the original citation with metadata validation
      const validationHashes = calculateValidationHashes(foundCitation);
      const retractResult = await retractPaper(foundCitation.docId, signer, validationHashes.metadataRoot);

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
      setAlterTransactions({
        txRetract: retractResult.transactionHash,
        txAdd: tx.hash
      });
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
    setFoundCitation({ doi: "", title: "", authors: "", date: "", abstract: "", journal: "" });
    setNewCitation({ doi: "", title: "", authors: "", date: "", abstract: "", journal: "" });
    setSuggestions([]);
    setShowSuggestions(false);
    setIsVerified(false);
    setAlterTransactions({ txRetract: null, txAdd: null });
    setStatusMessage("Operation cancelled. Start again.");
  };

  // Clear transaction details when any field changes
  const clearTransactionsOnFieldChange = () => {
    if (alterTransactions.txRetract || alterTransactions.txAdd) {
      setAlterTransactions({ txRetract: null, txAdd: null });
    }
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

  // pop up closing function
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (inputRef.current && !inputRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const currentFields = [
    { name: "doi", label: "DOI", value: foundCitation.doi, onChange: (e) => { setFoundCitation({ ...foundCitation, doi: e.target.value }); clearTransactionsOnFieldChange(); }, placeholder: "Enter or select DOI" },
    { name: "title", label: "Title", value: foundCitation.title, onChange: (e) => { setFoundCitation({ ...foundCitation, title: e.target.value }); clearTransactionsOnFieldChange(); } },
    { name: "authors", label: "Authors", value: foundCitation.authors, onChange: (e) => { setFoundCitation({ ...foundCitation, authors: e.target.value }); clearTransactionsOnFieldChange(); } },
    { name: "date", label: "Date", value: foundCitation.date, onChange: (e) => { setFoundCitation({ ...foundCitation, date: e.target.value }); clearTransactionsOnFieldChange(); } },
    { name: "abstract", label: "Abstract", value: foundCitation.abstract, onChange: (e) => { setFoundCitation({ ...foundCitation, abstract: e.target.value }); clearTransactionsOnFieldChange(); } },
    { name: "journal", label: "Journal", value: foundCitation.journal, onChange: (e) => { setFoundCitation({ ...foundCitation, journal: e.target.value }); clearTransactionsOnFieldChange(); } },
  ];

  const newFields = [
    { name: "doi", label: "DOI", value: newCitation.doi, onChange: (e) => { setNewCitation({ ...newCitation, doi: e.target.value }); clearTransactionsOnFieldChange(); }, disabled: !isVerified },
    { name: "title", label: "Title", value: newCitation.title, onChange: (e) => { setNewCitation({ ...newCitation, title: e.target.value }); clearTransactionsOnFieldChange(); }, disabled: !isVerified },
    { name: "authors", label: "Authors", value: newCitation.authors, onChange: (e) => { setNewCitation({ ...newCitation, authors: e.target.value }); clearTransactionsOnFieldChange(); }, disabled: !isVerified },
    { name: "date", label: "Date", type: "date", value: newCitation.date, onChange: (e) => { setNewCitation({ ...newCitation, date: e.target.value }); clearTransactionsOnFieldChange(); }, disabled: !isVerified },
    { name: "abstract", label: "Abstract", value: newCitation.abstract, onChange: (e) => { setNewCitation({ ...newCitation, abstract: e.target.value }); clearTransactionsOnFieldChange(); }, disabled: !isVerified },
    { name: "journal", label: "Journal", value: newCitation.journal, onChange: (e) => { setNewCitation({ ...newCitation, journal: e.target.value }); clearTransactionsOnFieldChange(); }, disabled: !isVerified },
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
              onFocus={() => setShowSuggestions(true)}
              onKeyPress={(e) => e.key === 'Enter' && handleEnterDoi()}
              className="search-input-field"
            />
            {showSuggestions && (
              <div className="search-dropdown">
                <div className="dropdown-section">
                  <div className="dropdown-header">Quick examples:</div>
                  {samplePapers.map((paper, index) => (
                    <div
                      key={index}
                      className="dropdown-item"
                      onClick={() => handleQuickDemo(samplePapers[index])}
                    >
                      <strong>{paper.doi}</strong> - {paper.title.slice(0, 60)}...
                    </div>
                  ))}
                </div>
                {suggestions.length > 0 && (
                  <div className="dropdown-section">
                    <div className="dropdown-header">Matching papers:</div>
                    {suggestions.map((s, i) => (
                      <div key={i} className="dropdown-item" onClick={() => handleSelectSuggestion(s)}>
                        {s}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
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
              buttonText={foundCitation.doi && !isVerified && foundCitation.title.trim() && foundCitation.authors.trim() && foundCitation.date.trim() ? "Validate" : ""}
              onActionClick={handleCheck}
              extraButtons={[{ text: "Clear", onClick: handleCancel, className: "clear-btn" }]}
            />
          </div>
          <div className="citation-card-right">
            <CitationCard
              title="New Citation"
              fields={newFields}
              buttonText="Update"
              onActionClick={handleAlter}
              disabled={!isVerified}
              tooltip={!isVerified ? "Validate current citation first" : ""}
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
