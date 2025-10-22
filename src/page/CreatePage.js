import React, { useState, useEffect } from "react";
import CitationCard from "../component/CitationCard";
import { createContractInstance } from "../utils/web3";
import { calculateRegistrationData } from "../utils/merkle";
import { useWallet } from "../contexts/WalletContext";
import "./AlterPage.css";

const CreatePage = () => {
  const { walletConnected, connectWallet, signer, formattedAddress } = useWallet();

  const [doi, setDoi] = useState("arXiv:1706.03762");
  const [title, setTitle] = useState("Attention Is All You Need");
  const [authors, setAuthors] = useState("Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin");
  const [date, setDate] = useState("2017-06-12");
  const [abstract, setAbstract] = useState("The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing both with large and limited training data.");
  const [journal, setJournal] = useState("N/A");

  const [statusMessage, setStatusMessage] = useState("Please connect your wallet to register citations.");

  const [isLoading, setIsLoading] = useState(false);
  const [transactionDetails, setTransactionDetails] = useState(null);

  // Removed local wallet connection logic - using global context

  /**
   * Register citation using local Merkle calculation and direct smart contract transaction
   */
  const registerCitationLocally = async (citationData) => {
    try {
      if (!signer) {
        throw new Error("Wallet not connected. Please connect your wallet first.");
      }

      setStatusMessage("Calculating Merkle tree data locally...");

      // Step 1: Calculate all required data locally
      const registrationData = await calculateRegistrationData(citationData, signer);

      setStatusMessage("Preparing transaction for wallet...");

      // Step 2: Create contract instance and send transaction
      const contract = await createContractInstance(signer);

      setStatusMessage("Waiting for wallet confirmation...");

      // Step 3: Send transaction
      const tx = await contract.registerPaper(
        registrationData.transactionData.hashedDoi,
        registrationData.transactionData.hashedTad,
        registrationData.transactionData.metadataRoot,
        registrationData.transactionData.fulltextRoot
      );

      setStatusMessage("Mining transaction on blockchain...");

      // Wait for transaction confirmation
      const receipt = await tx.wait();

      // Check if transaction was successful
      if (receipt.status !== 1) {
        throw new Error("Transaction failed: Smart contract reverted the transaction");
      }

      setStatusMessage("Verifying citation registration...");

      // Step 4: Get the docId from the transaction
      let docId = null;
      try {
        const hashedDoi = registrationData.transactionData.hashedDoi;
        const foundDocId = await contract.getDocIdByDoi(hashedDoi);
        docId = Number(foundDocId);

        // Additional verification: ensure the docId was actually created
        if (!docId || docId === 0) {
          throw new Error("Transaction failed: Citation was not registered on blockchain");
        }
      } catch (e) {
        console.warn("Could not retrieve docId:", e);
        throw new Error("Transaction verification failed: Could not confirm registration");
      }

      return {
        success: true,
        docId,
        transactionHash: tx.hash,
        metadataRoot: registrationData.transactionData.metadataRoot,
        fulltextRoot: registrationData.transactionData.fulltextRoot,
        message: "Citation successfully registered on blockchain!",
        blockNumber: receipt.blockNumber,
      };
    } catch (error) {
      console.error("Citation registration error:", error);
      throw error;
    }
  };

  const handleCreate = async () => {
    if (!walletConnected || !signer) {
      setStatusMessage("Please connect your wallet first.");
      return;
    }

    const citationData = { doi, title, authors, date, abstract, journal };

    // Validate required fields
    if (!doi.trim() || !title.trim() || !authors.trim() || !date.trim()) {
      setStatusMessage("Please fill in all required fields (DOI, Title, Authors, Date).");
      return;
    }

    try {
      setIsLoading(true);
      setTransactionDetails(null); // Clear any previous transaction details

      // Step 1: Check if DOI already exists via blockchain
      setStatusMessage("Validating citation details via blockchain...");
      console.log("CREATE PAGE: Starting validation for DOI:", doi);

      // Import required functions for canonicalization
      const { hashHashedDoi, hashHashedTAD, bytesToHex } = await import("../utils/merkle");

      // Hash DOI
      const hashedDoiBytes = hashHashedDoi(citationData.doi);
      const hashedDoi = bytesToHex(hashedDoiBytes);
      console.log("CREATE PAGE: hashedDoi =", hashedDoi);

      // Create contract instance for validation
      const contract = await createContractInstance(signer);

      // Check DOI existence via blockchain
      console.log("CREATE PAGE: Checking DOI existence on blockchain...");
      const existingDocId = await contract.getDocIdByDoi(hashedDoi);

      if (existingDocId && Number(existingDocId) > 0) {
        throw new Error(`DOI "${doi}" is already registered in the system.`);
      }

      // Step 2: Check if Title+Authors+Date combination already exists
      console.log("CREATE PAGE: Checking TAD existence on blockchain...");
      setStatusMessage("Checking for duplicate Title+Authors+Date combinations...");

      const hashedTadBytes = hashHashedTAD(title, authors, date);
      const hashedTad = bytesToHex(hashedTadBytes);
      console.log("CREATE PAGE: hashedTAD =", hashedTad);

      // Check TAD existence via blockchain
      const existingDocIdByTad = await contract.getDocIdByTAD(hashedTad);

      if (existingDocIdByTad && Number(existingDocIdByTad) > 0) {
        throw new Error("A paper with the same Title, Authors, and Date already exists in the system.");
      }

      console.log("CREATE PAGE: Validation passed - DOI and TAD are unique");

      // Step 3: Create transaction after validation passes
      setStatusMessage("Validation passed! Preparing transaction for wallet...");
      const result = await registerCitationLocally(citationData);

      if (result.success) {
        // Store transaction details permanently until user clears them
        setTransactionDetails({
          ...citationData,
          docId: result.docId,
          transactionHash: result.transactionHash,
          metadataRoot: result.metadataRoot,
          fulltextRoot: result.fulltextRoot,
          blockNumber: result.blockNumber,
        });

        setStatusMessage(
          `✅ Citation successfully registered! Document ID: ${result.docId}. Transaction confirmed in block ${result.blockNumber}. Transaction Hash: ${result.transactionHash.slice(0, 10)}...${result.transactionHash.slice(-8)}`
        );
        console.log("CREATE PAGE: Registration completed successfully, docId:", result.docId);
      } else {
        setStatusMessage(`Registration failed: ${result.message}`);
      }
    } catch (error) {
      console.error("CREATE PAGE: Citation registration error:", error);

      // Provide more specific error messages based on common issues
      let errorMessage = error.message;
      if (error.message.includes('REGISTRAR_ROLE')) {
        errorMessage = "Permission denied: Your account needs the REGISTRAR_ROLE to register citations.";
      } else if (error.message.includes('already registered')) {
        errorMessage = "Already registered: This DOI has already been registered in the system.";
      } else if (error.message.includes('user rejected')) {
        errorMessage = "Transaction cancelled: You rejected the transaction in your wallet.";
      } else if (error.message.includes('insufficient funds')) {
        errorMessage = "Insufficient funds: Not enough ETH to pay for gas fees.";
      } else {
        errorMessage = `Registration failed: ${error.message}`;
      }

      setStatusMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setDoi("");
    setTitle("");
    setAuthors("");
    setDate("");
    setAbstract("");
    setJournal("");
    setTransactionDetails(null);
    if (walletConnected) {
      setStatusMessage("Operation cancelled. Fill in citation details and click 'Create'.");
    } else {
      setStatusMessage("Please connect your wallet to register citations.");
    }
  };

  // Clear transaction details when user manually changes fields after successful registration
  const clearTransactionDetailsOnFieldChange = () => {
    // Only clear transaction details if user has successfully registered something
    // and is now manually changing the form fields
    if (transactionDetails && transactionDetails.docId) {
      console.log("CREATE PAGE: User modified form after successful registration - clearing transaction details");
      setTransactionDetails(null);
      setStatusMessage("Form modified. Previous transaction details cleared. Click 'Create' to register a new citation.");
    }
  };

  // Determine status type for styling
  const getStatusType = (message) => {
    if (!message) return '';

    const lowerMessage = message.toLowerCase();

    // Error indicators (check first to be more specific)
    if (lowerMessage.includes('already registered') ||
        lowerMessage.includes('error') ||
        lowerMessage.includes('failed') ||
        lowerMessage.includes('denied') ||
        lowerMessage.includes('cancelled') ||
        lowerMessage.includes('does not exist') ||
        lowerMessage.includes('insufficient funds') ||
        (lowerMessage.includes('please') && lowerMessage.includes('connect'))) {
      return 'error';
    }

    // Success indicators
    if (lowerMessage.includes('successfully') ||
        lowerMessage.includes('connected') ||
        lowerMessage.includes('verified') ||
        lowerMessage.includes('confirmed') ||
        lowerMessage.includes('altered') ||
        lowerMessage.includes('found') ||
        lowerMessage.includes('ready for editing') ||
        lowerMessage.includes('retracted') ||
        lowerMessage.includes('active')) {
      return 'success';
    }

    // Warning indicators
    if (lowerMessage.includes('warning') ||
        lowerMessage.includes('checking') ||
        lowerMessage.includes('processing') ||
        lowerMessage.includes('waiting') ||
        lowerMessage.includes('searching') ||
        lowerMessage.includes('verifying') ||
        lowerMessage.includes('retracting') ||
        lowerMessage.includes('validating') ||
        lowerMessage.includes('calculating')) {
      return 'warning';
    }

    return '';
  };

  // Update status message when wallet connection changes (but don't override success messages)
  useEffect(() => {
    if (walletConnected && !statusMessage.includes('successfully registered') && !statusMessage.includes('✅')) {
      if (!transactionDetails) {
        setStatusMessage("Wallet connected. Fill in the citation details and click 'Create'.");
      }
    } else if (!walletConnected) {
      setStatusMessage("Please connect your wallet to register citations.");
      setTransactionDetails(null); // Clear transaction details when wallet disconnects
    }
  }, [walletConnected, statusMessage, transactionDetails]);

  // No popup useEffect needed anymore

  const fields = [
    { name: "doi", label: "DOI", value: doi, onChange: (e) => { setDoi(e.target.value); clearTransactionDetailsOnFieldChange(); }, placeholder: "10.1109/SUMMA64428.2024.10803746" },
    { name: "title", label: "Title", value: title, onChange: (e) => { setTitle(e.target.value); clearTransactionDetailsOnFieldChange(); }, placeholder: "Utilizing Modern Large Language Models..." },
    { name: "authors", label: "Authors", value: authors, onChange: (e) => { setAuthors(e.target.value); clearTransactionDetailsOnFieldChange(); }, placeholder: "Andrei Lazarev, Dmitrii Sedov" },
    { name: "date", label: "Date", type: "date", value: date, onChange: (e) => { setDate(e.target.value); clearTransactionDetailsOnFieldChange(); } },
    { name: "abstract", label: "Abstract", value: abstract, onChange: (e) => { setAbstract(e.target.value); clearTransactionDetailsOnFieldChange(); }, placeholder: "Short summary of the paper..." },
    { name: "journal", label: "Journal", value: journal, onChange: (e) => { setJournal(e.target.value); clearTransactionDetailsOnFieldChange(); }, placeholder: "6th International Conference on Control Systems..." },
  ];

  return (
    <div className="citation-delete-page">
      <h2 className="page-title">Register New Citation</h2>

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

      {/* Citation Form */}
      <CitationCard
        title="Citation Details"
        fields={fields}
        buttonText={isLoading ? "Processing..." : "Create"}
        onActionClick={handleCreate}
        extraButtons={[
          { text: "Clear", onClick: handleCancel, disabled: isLoading, className: "clear-btn" }
        ]}
        disabled={!walletConnected || isLoading}
      />

      {/* Status Message - Moved to bottom */}
      {(statusMessage && !walletConnected) || (walletConnected && statusMessage) ? (
        <div className={`status-box ${getStatusType(statusMessage)}`}>
          <p>{statusMessage}</p>
        </div>
      ) : null}
    </div>
  );
};

export default CreatePage;
