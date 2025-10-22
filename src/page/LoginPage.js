import React, { useState, useEffect } from "react";
import { ethers } from 'ethers';
import { createContractInstance } from "../utils/web3";
import { useWallet } from "../contexts/WalletContext";
import "./LoginPage.css";

const LoginPage = () => {
  const { walletConnected, connectWallet: connectGlobalWallet, formattedAddress, signer } = useWallet();
  const [statusMessage, setStatusMessage] = useState("Connect your wallet to authenticate as an administrator.");
  const [errorMessage, setErrorMessage] = useState("");
  const [isAdminVerified, setIsAdminVerified] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  
  /**
   * Connect wallet and verify admin permissions
   */
  const handleConnectWallet = async () => {
    try {
      setIsLoading(true);
      setErrorMessage("");
      setStatusMessage("Connecting to wallet...");

      await connectGlobalWallet();
    } catch (error) {
      console.error("Login error:", error);
      setErrorMessage(`Authentication failed: ${error.message}`);
      setStatusMessage("Connect your wallet to authenticate as an administrator.");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Disconnect wallet
   */
  const handleDisconnect = () => {
    setIsAdminVerified(false);
    setErrorMessage("");
    setStatusMessage("Wallet disconnected. Connect your wallet to authenticate as an administrator.");
  };

  // Check admin permissions when wallet connects
  useEffect(() => {
    const checkAdminPermissions = async (signer) => {
      try {
        setStatusMessage("Verifying permissions...");

        // Check if user has REGISTRAR_ROLE
        const contract = await createContractInstance(signer);

        // Calculate REGISTRAR_ROLE hash (keccak256("REGISTRAR_ROLE"))
        const REGISTRAR_ROLE_HASH = ethers.keccak256(ethers.toUtf8Bytes("REGISTRAR_ROLE"));

        const address = await signer.getAddress();
        const hasRegistrarRole = await contract.hasRole(REGISTRAR_ROLE_HASH, address);

        if (!hasRegistrarRole) {
          throw new Error("Your account does not have REGISTRAR_ROLE permissions. Only authorized administrators can access this system.");
        }

        setIsAdminVerified(true);
        setStatusMessage(
          `Successfully authenticated as ${formattedAddress}. Administrator access verified.`
        );
      } catch (error) {
        console.error("Admin verification error:", error);
        setErrorMessage(`Authentication failed: ${error.message}`);
        setStatusMessage("Connect your wallet to authenticate as an administrator.");
        setIsAdminVerified(false);
      }
    };

    if (walletConnected && !isAdminVerified && signer) {
      checkAdminPermissions(signer);
    } else if (!walletConnected) {
      setIsAdminVerified(false);
      setErrorMessage("");
    }
  }, [walletConnected, signer, isAdminVerified, formattedAddress]);

  // Determine status type for styling
  const getStatusType = (message) => {
    if (!message) return '';

    const lowerMessage = message.toLowerCase();

    // Success indicators
    if (lowerMessage.includes('successfully') ||
        lowerMessage.includes('connected') ||
        lowerMessage.includes('verified') ||
        lowerMessage.includes('authenticated') ||
        lowerMessage.includes('granted')) {
      return 'success';
    }

    // Error indicators
    if (lowerMessage.includes('error') ||
        lowerMessage.includes('failed') ||
        lowerMessage.includes('denied') ||
        lowerMessage.includes('cancelled') ||
        lowerMessage.includes('authentication failed') ||
        lowerMessage.includes('permission denied') ||
        lowerMessage.includes('does not have') ||
        lowerMessage.includes('insufficient funds') ||
        (lowerMessage.includes('please') && lowerMessage.includes('connect'))) {
      return 'error';
    }

    // Warning indicators
    if (lowerMessage.includes('warning') ||
        lowerMessage.includes('checking') ||
        lowerMessage.includes('processing') ||
        lowerMessage.includes('waiting') ||
        lowerMessage.includes('connecting') ||
        lowerMessage.includes('verifying')) {
      return 'warning';
    }

    return '';
  };


  return (
    <div className="login-page">
      <h2 className="login-title">Administrator Authentication</h2>

      {/* Wallet Connection Section */}
      {!walletConnected ? (
        <div className="login-section">
          <div className="status-box wallet-box">
            <p>{statusMessage}</p>
            <button
              onClick={handleConnectWallet}
              disabled={isLoading}
              className="connect-wallet-btn"
            >
              {isLoading ? "Connecting..." : "Connect Wallet"}
            </button>
          </div>
          <div className="login-field">
            <label>Information</label>
            <div className="wallet-connect-info">
              <p>Connect your Web3 wallet to authenticate as an administrator.</p>
              <p>Ensure your wallet has REGISTRAR_ROLE permissions on the smart contract.</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="login-section connected">
          <div className="status-box wallet-connected">
            <p>
              <strong>Connected:</strong> {formattedAddress}
            </p>
            <button
              onClick={handleDisconnect}
              disabled={isLoading}
              className="disconnect-wallet-btn"
            >
              Disconnect
            </button>
            <button
              onClick={handleConnectWallet}
              disabled={isLoading}
              className="reconnect-wallet-btn"
            >
              Reauthenticate
            </button>
          </div>
          <div className="login-field">
            <label>Authentication Status</label>
            <div className="wallet-info">
              <p><strong>Status:</strong> Authenticated as Administrator</p>
              <p className="auth-note">You can now use Register, Update, and Retract citation functions.</p>
            </div>
          </div>
        </div>
      )}

      {/* Error Message Display */}
      {errorMessage && (
        <div className="status-box error">
          <p>{errorMessage}</p>
        </div>
      )}

      {/* Dynamic Status Message (only shows when wallet is connected for operations) */}
      {walletConnected && statusMessage.includes("Successfully connected") && (
        <div className={`status-box ${getStatusType(statusMessage)}`}>
          <p>{statusMessage}</p>
        </div>
      )}

      {/* Instructions */}
      <div className="login-instructions">
        <h3>Instructions</h3>
        <ul>
          <li>Install a Web3 wallet browser extension (e.g., MetaMask)</li>
          <li>Ensure your wallet is configured for the Hardhat local network (Chain ID: 1337)</li>
          <li>Your wallet address must have REGISTRAR_ROLE on the CitationRegistry smart contract</li>
          <li>Click "Connect Wallet" to authenticate and sign a login message</li>
        </ul>
      </div>
    </div>
  );
};

export default LoginPage;
