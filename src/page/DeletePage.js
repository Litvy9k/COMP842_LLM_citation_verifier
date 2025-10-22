import React, { useState, useRef, useEffect } from "react";
import CitationCard from "../component/CitationCard";
import { retractPaper, createContractInstance, createReadOnlyContractInstance } from "../utils/web3";
import { useWallet } from "../contexts/WalletContext";
import { hashHashedDoi, bytesToHex, calculateValidationHashes } from "../utils/merkle";
import "./AlterPage.css"; 

const CitationDeletePage = () => {
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
  const [statusMessage, setStatusMessage] = useState(
    "Please connect your wallet to manage citation retractions."
  );
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [retractionTxHash, setRetractionTxHash] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isVerified, setIsVerified] = useState(false);

  const inputRef = useRef(null);

  /**
   * Find paper data by DOI in the sample paper database
   */
  const findPaperByDoi = (doi) => {
    return samplePapers.find(paper => paper.doi === doi);
  };

  // Sample papers loaded from paper.json
  const samplePapers = [
    {
      doi: "arXiv:2510.00083",
      title: "Enhancing Certifiable Semantic Robustness via Robust Pruning of Deep Neural Networks",
      authors: "Hanjiang Hu, Bowei Li, Ziwei Wang, Tianhao Wei, Casidde Hutchison, Eric Sample, Changliu Liu",
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

  /**
   * Search for citation by DOI and check its retraction status using smart contract
   */
  const fetchCitationStatus = async (doi) => {
    try {
      if (!walletConnected || !signer) {
        setStatusMessage("Please connect your wallet first.");
        return;
      }

      setStatusMessage("Searching for citation...");

      // Create contract instance
      const contract = await createContractInstance(signer);

      // Hash the DOI to match blockchain storage format
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

        setFoundCitation({
          doi,
          title: realPaper ? realPaper.title : "",
          authors: realPaper ? realPaper.authors : "",
          date: realPaper ? realPaper.date : "",
          abstract: realPaper ? realPaper.abstract : "",
          journal: realPaper ? realPaper.journal : "",
          docId,
          isRetracted,
        });

        const retractionStatus = isRetracted ? "Citation is RETRACTED" : "Citation is ACTIVE";
        const dataStatus = realPaper ? "Citation details loaded from database." : "Fill in citation details manually for validation.";
        const allDataFilled = realPaper && realPaper.title && realPaper.authors && realPaper.date;
        setStatusMessage(`Citation found (ID: ${docId}). ${retractionStatus}. ${dataStatus} ${allDataFilled ? 'Click Validate to confirm before retraction.' : 'Fill in all required fields (Title, Authors, Date) to validate.'}`);
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
      }
    } catch (error) {
      console.error("Citation search error:", error);
      setStatusMessage(`Search failed: ${error.message}`);
    }
  };

  const handleSearchInput = (e) => {
  const value = e.target.value;
  setSearchDoi(value);

  // Generate suggestions from real paper data
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
  setStatusMessage("Fill in citation details manually.");
  setIsVerified(false);
};

const handleEnterDoi = () => {
  if (searchDoi.trim()) {
    fetchCitationStatus(searchDoi.trim());
  } else {
    setStatusMessage("Please enter a DOI to proceed.");
  }
};

const handleValidate = async () => {
  if (!foundCitation.doi) {
    setStatusMessage("Enter a DOI to verify.");
    return;
  }

  if (!foundCitation.title.trim() || !foundCitation.authors.trim() || !foundCitation.date.trim()) {
    setStatusMessage("Please fill in Title, Authors, and Date to validate citation identity before retraction.");
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
      setStatusMessage("Citation verification failed: This citation has already been retracted.");
      return;
    }

    // Verify metadata matches
    if (metadataRoot !== validationHashes.metadataRoot) {
      console.log("Metadata mismatch detected");
      setStatusMessage("Citation verification failed: Metadata does not match blockchain record.");
      return;
    }

    // Set docId for retraction
    setFoundCitation({
      ...foundCitation,
      docId: Number(existingDocId),
    });

    console.log("Verification successful");
    setIsVerified(true);
    setStatusMessage("Citation verified against blockchain. You can now retract this citation.");

  } catch (error) {
    console.error("Citation verification error:", error);
    setStatusMessage(`Verification failed: ${error.message}`);
  }
};

/**
 * Retract citation using direct smart contract interaction
 */
const handleRetractCitation = async () => {
  try {
    if (!walletConnected || !signer) {
      setStatusMessage("Please connect your wallet first.");
      return;
    }

    if (!foundCitation.doi) {
      setStatusMessage("Enter a DOI to verify.");
      return;
    }

    if (!isVerified) {
      setStatusMessage("Please validate the citation before retracting.");
      return;
    }

    if (foundCitation.isRetracted) {
      setStatusMessage("This citation has already been retracted.");
      return;
    }

    setIsLoading(true);
    setStatusMessage("Preparing retraction transaction...");

    // Call smart contract directly for retraction with metadata validation
    const validationHashes = calculateValidationHashes(foundCitation);
    const result = await retractPaper(foundCitation.docId, signer, validationHashes.metadataRoot);

    if (result.success) {
      // Update local state
      setFoundCitation({
        ...foundCitation,
        isRetracted: true,
      });

      setRetractionTxHash(result.transactionHash);
      setStatusMessage(
        `Citation successfully retracted! Transaction confirmed in block ${result.blockNumber}. Transaction Hash: ${result.transactionHash.slice(0, 10)}...${result.transactionHash.slice(-8)}`
      );
    } else {
      throw new Error("Retraction transaction failed");
    }
  } catch (error) {
    console.error("Citation retraction error:", error);

    // Provide more specific error messages based on common issues
    let errorMessage = error.message;
    if (error.message.includes('REGISTRAR_ROLE')) {
      errorMessage = "Permission denied: Your account needs the REGISTRAR_ROLE to retract citations.";
    } else if (error.message.includes('docId does not exist')) {
      errorMessage = "Paper not found: The citation ID does not exist in the registry.";
    } else if (error.message.includes('already retracted')) {
      errorMessage = "Already retracted: This citation has already been retracted.";
    } else if (error.message.includes('user rejected')) {
      errorMessage = "Transaction cancelled: You rejected the transaction in your wallet.";
    } else if (error.message.includes('insufficient funds')) {
      errorMessage = "Insufficient funds: Not enough ETH to pay for gas fees.";
    } else {
      errorMessage = `Retraction failed: ${error.message}`;
    }

    setStatusMessage(errorMessage);
  } finally {
    setIsLoading(false);
  }
};

  const handleCancel = () => {
    setSearchDoi("");
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
    setSuggestions([]);
    setShowSuggestions(false);
    setRetractionTxHash(null);
    if (walletConnected) {
      setStatusMessage("Operation cancelled. Enter DOI to search for citations.");
    } else {
      setStatusMessage("Please connect your wallet to manage citation retractions.");
    }
  };

  // Clear transaction details when any field changes
  const clearRetractionDetailsOnFieldChange = () => {
    if (retractionTxHash) {
      setRetractionTxHash(null);
    }
    setIsVerified(false); // Reset validation when fields change
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
        lowerMessage.includes('retracted') ||
        lowerMessage.includes('found') ||
        lowerMessage.includes('active')) {
      return 'success';
    }

    // Error indicators
    if (lowerMessage.includes('error') ||
        lowerMessage.includes('failed') ||
        lowerMessage.includes('denied') ||
        lowerMessage.includes('cancelled') ||
        lowerMessage.includes('already registered') ||
        lowerMessage.includes('does not exist') ||
        lowerMessage.includes('insufficient funds') ||
        (lowerMessage.includes('please') && lowerMessage.includes('connect')) ||
        lowerMessage.includes('already retracted') ||
        lowerMessage.includes('not found')) {
      return 'error';
    }

    // Warning indicators
    if (lowerMessage.includes('warning') ||
        lowerMessage.includes('checking') ||
        lowerMessage.includes('processing') ||
        lowerMessage.includes('waiting') ||
        lowerMessage.includes('searching') ||
        lowerMessage.includes('verifying') ||
        lowerMessage.includes('preparing')) {
      return 'warning';
    }

    return '';
  };

  // Update status message when wallet connection changes
  useEffect(() => {
    if (walletConnected) {
      if (statusMessage === "Please connect your wallet to manage citation retractions.") {
        setStatusMessage("Wallet connected. Enter DOI to search for citations.");
      }
    } else {
      setStatusMessage("Please connect your wallet to manage citation retractions.");
    }
  }, [walletConnected, statusMessage]);

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
    { name: "doi", label: "DOI", value: foundCitation.doi, onChange: (e) => { setFoundCitation({ ...foundCitation, doi: e.target.value }); clearRetractionDetailsOnFieldChange(); } },
    { name: "title", label: "Title", value: foundCitation.title, onChange: (e) => { setFoundCitation({ ...foundCitation, title: e.target.value }); clearRetractionDetailsOnFieldChange(); } },
    { name: "authors", label: "Authors", value: foundCitation.authors, onChange: (e) => { setFoundCitation({ ...foundCitation, authors: e.target.value }); clearRetractionDetailsOnFieldChange(); } },
    { name: "date", label: "Date", value: foundCitation.date, onChange: (e) => { setFoundCitation({ ...foundCitation, date: e.target.value }); clearRetractionDetailsOnFieldChange(); } },
    { name: "abstract", label: "Abstract", value: foundCitation.abstract, onChange: (e) => { setFoundCitation({ ...foundCitation, abstract: e.target.value }); clearRetractionDetailsOnFieldChange(); } },
    { name: "journal", label: "Journal", value: foundCitation.journal, onChange: (e) => { setFoundCitation({ ...foundCitation, journal: e.target.value }); clearRetractionDetailsOnFieldChange(); } },
  ];

  return (
    <div className="citation-alter-page">
      <h2 className="page-title">Retract Citation</h2>

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
              placeholder="Enter DOI (e.g., 10.1109/SUMMA64428.2024.10803746)"
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

      {/* Citation Details */}
      {walletConnected && (
        <CitationCard
          title="Citation Details"
          fields={fields}
          buttonText={foundCitation.doi && !isVerified ? "Validate" : ""}
          onActionClick={handleValidate}
          extraButtons={[
            { text: "Clear", onClick: handleCancel, disabled: isLoading, className: "clear-btn" },
            foundCitation.doi && isVerified && !foundCitation.isRetracted ?
              { text: isLoading ? "Retracting..." : "Retract Citation", onClick: handleRetractCitation, disabled: isLoading } :
              null
          ].filter(Boolean)}
          disabled={foundCitation.isRetracted || isLoading}
        />
      )}

      {/* Status Message */}
      {(statusMessage && !walletConnected) || (walletConnected && statusMessage) ? (
        <div className={`status-box ${getStatusType(statusMessage)}`}>
          <p>{statusMessage}</p>
        </div>
      ) : null}

      </div>
  );
};

export default CitationDeletePage;
