import React, { useState, useRef, useEffect } from "react";
import CitationCard from "../component/CitationCard";
import { retractPaper, createContractInstance } from "../utils/web3";
import { useWallet } from "../contexts/WalletContext";
import { hashHashedDoi, bytesToHex } from "../utils/merkle";
import "./AlterPage.css"; 

const CitationDeletePage = () => {
  const { walletConnected, connectWallet, signer, formattedAddress } = useWallet();

    const [foundCitation, setFoundCitation] = useState({
    doi: "",
    docId: null,
    isRetracted: false,
    metadataRoot: null,
  });
  const [statusMessage, setStatusMessage] = useState(
    "Please connect your wallet to manage citation retractions."
  );

  const [isLoading, setIsLoading] = useState(false);

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
        // Get paper details including retraction status and metadata root
        const [, , isRetracted, metadataRoot] = await contract.getPaper(docId);

        setFoundCitation({
          doi,
          docId,
          isRetracted,
          metadataRoot,
        });

        const retractionStatus = isRetracted ? "Citation is RETRACTED" : "Citation is ACTIVE";
        setStatusMessage(`Citation found (ID: ${docId}). ${retractionStatus}. Ready for retraction.`);
      } else {
        setFoundCitation({
          doi: "",
          docId: null,
          isRetracted: false,
          metadataRoot: null,
        });
        setStatusMessage("Citation not found in registry.");
      }
    } catch (error) {
      console.error("Citation search error:", error);
      setStatusMessage(`Search failed: ${error.message}`);
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
      setStatusMessage("Enter a DOI to retract.");
      return;
    }

    // First, check if citation exists and get its status
    await fetchCitationStatus(foundCitation.doi);

    // Wait a bit for state to update
    await new Promise(resolve => setTimeout(resolve, 100));

    // Check if citation was found after the search
    if (!foundCitation.docId) {
      setStatusMessage("Citation not found in registry.");
      return;
    }

    if (foundCitation.isRetracted) {
      setStatusMessage("This citation has already been retracted.");
      return;
    }

    setIsLoading(true);
    setStatusMessage("Preparing retraction transaction...");

    // Call smart contract directly for retraction using the actual metadata root
    const result = await retractPaper(foundCitation.docId, signer, foundCitation.metadataRoot);

    if (result.success) {
      // Update local state
      setFoundCitation({
        ...foundCitation,
        isRetracted: true,
      });


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
    setFoundCitation({
      doi: "",
      docId: null,
      isRetracted: false,
      metadataRoot: null,
    });
    if (walletConnected) {
      setStatusMessage("Operation cancelled. Enter DOI to retract citation.");
    } else {
      setStatusMessage("Please connect your wallet to manage citation retractions.");
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
        setStatusMessage("Wallet connected. Enter DOI to retract citation.");
      }
    } else {
      setStatusMessage("Please connect your wallet to manage citation retractions.");
    }
  }, [walletConnected, statusMessage]);

  const fields = [
    { name: "doi", label: "DOI", value: foundCitation.doi, onChange: (e) => { setFoundCitation({ ...foundCitation, doi: e.target.value }); } },
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

      
      {/* Citation Details */}
      {walletConnected && (
        <CitationCard
          title="Citation Details"
          fields={fields}
          extraButtons={[
            { text: "Clear", onClick: handleCancel, disabled: isLoading, className: "clear-btn" },
            foundCitation.doi && !foundCitation.isRetracted ?
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
