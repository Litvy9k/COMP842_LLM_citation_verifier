/**
 * Global wallet context for sharing wallet state across pages
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { connectWallet, formatAddress, isMetaMaskInstalled, getContractConfig } from '../utils/web3';

const WalletContext = createContext();

export const useWallet = () => {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error('useWallet must be used within a WalletProvider');
  }
  return context;
};

export const WalletProvider = ({ children }) => {
  const [walletConnected, setWalletConnected] = useState(false);
  const [walletAddress, setWalletAddress] = useState('');
  const [signer, setSigner] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Disconnect wallet and clear state
   */
  const disconnectWallet = useCallback(() => {
    setWalletConnected(false);
    setWalletAddress('');
    setSigner(null);
    setIsLoading(false);
  }, []);

  /**
   * Check existing wallet connection on mount and handle account changes
   */
  useEffect(() => {
    const checkExistingConnection = async () => {
      if (!isMetaMaskInstalled()) {
        return;
      }

      try {
        const ethereum = window.ethereum;

        // Check if already connected
        const accounts = await ethereum.request({ method: 'eth_accounts' });

        if (accounts.length > 0) {
          // User is already connected, try to reconnect
          setIsLoading(true);
          try {
            const { signer: connectedSigner, address } = await connectWallet();
            setSigner(connectedSigner);
            setWalletAddress(address);
            setWalletConnected(true);
          } catch (connectError) {
            console.warn('Failed to reconnect to existing wallet:', connectError);
            // Don't throw error, just leave user disconnected
          } finally {
            setIsLoading(false);
          }
        }
      } catch (error) {
        console.error('Failed to check existing wallet connection:', error);
      }
    };

    // Check on mount
    checkExistingConnection();

    // Listen for account changes
    const ethereum = window.ethereum;
    if (ethereum) {
      const handleAccountsChanged = (accounts) => {
        if (accounts.length === 0) {
          // User disconnected all accounts
          disconnectWallet();
        } else {
          // Account changed, try to reconnect with new account
          checkExistingConnection();
        }
      };

      const handleChainChanged = () => {
        // Chain changed, check connection again
        checkExistingConnection();
      };

      // Subscribe to events
      ethereum.on('accountsChanged', handleAccountsChanged);
      ethereum.on('chainChanged', handleChainChanged);

      // Cleanup subscriptions
      return () => {
        if (ethereum.removeListener) {
          ethereum.removeListener('accountsChanged', handleAccountsChanged);
          ethereum.removeListener('chainChanged', handleChainChanged);
        }
      };
    }
  }, [disconnectWallet]);

  /**
   * Connect wallet and update global state
   */
  const connectWalletGlobal = useCallback(async () => {
    try {
      setIsLoading(true);
      const { signer: connectedSigner, address } = await connectWallet();

      setSigner(connectedSigner);
      setWalletAddress(address);
      setWalletConnected(true);

      // Pre-warm contract config cache to reduce backend calls
      try {
        await getContractConfig();
      } catch (configError) {
        console.warn('Failed to pre-warm contract config cache:', configError);
      }

      return {
        signer: connectedSigner,
        address,
      };
    } catch (error) {
      console.error('Wallet connection error:', error);
      disconnectWallet();
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [disconnectWallet]);

  /**
   * Check if wallet has necessary permissions for operations
   */
  const hasWalletPermissions = useCallback(() => {
    return walletConnected && signer;
  }, [walletConnected, signer]);

  const value = {
    // State
    walletConnected,
    walletAddress,
    signer,
    isLoading,

    // Computed
    formattedAddress: formatAddress(walletAddress),
    hasPermissions: hasWalletPermissions(),

    // Actions
    connectWallet: connectWalletGlobal,
    disconnectWallet,
  };

  return (
    <WalletContext.Provider value={value}>
      {children}
    </WalletContext.Provider>
  );
};

export default WalletContext;