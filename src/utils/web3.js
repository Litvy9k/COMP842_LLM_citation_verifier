/**
 * Web3 utility functions for wallet connection and smart contract interaction
 */

import detectEthereumProvider from '@metamask/detect-provider';
import { ethers } from 'ethers';

export const WEB3_CONFIG = {
  // Backend API endpoints
  BACKEND_URL: 'http://127.0.0.1:8000',

  // Ethereum network configuration
  NETWORK: {
    chainId: '0x539', // 1337 in hex (Hardhat local)
    chainName: 'Hardhat Local',
    rpcUrls: ['http://127.0.0.1:8545'],
    nativeCurrency: {
      name: 'ETH',
      symbol: 'ETH',
      decimals: 18,
    },
  },
};

/**
 * Connect to Web3 wallet and return provider/signer
 */
export const connectWallet = async () => {
  try {
    const ethereum = await detectEthereumProvider();

    if (!ethereum) {
      throw new Error('Web3 wallet is not installed. Please install a Web3 wallet to continue.');
    }

    // Check and switch network BEFORE requesting accounts to avoid network change error
    const currentChainId = await ethereum.request({ method: 'eth_chainId' });

    if (currentChainId !== WEB3_CONFIG.NETWORK.chainId) {
      try {
        // Try to switch to Hardhat network first
        await ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: WEB3_CONFIG.NETWORK.chainId }],
        });
      } catch (switchError) {
        // Network doesn't exist, try to add it
        if (switchError.code === 4902) {
          await ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [WEB3_CONFIG.NETWORK],
          });
        } else {
          throw new Error('Please switch to Hardhat local network (Chain ID: 1337)');
        }
      }
    }

    // Request account access after network is set up
    const accounts = await ethereum.request({
      method: 'eth_requestAccounts',
    });

    if (accounts.length === 0) {
      throw new Error('No accounts found. Please ensure your Web3 wallet is unlocked.');
    }

    // Create ethers provider and signer
    const provider = new ethers.BrowserProvider(ethereum);
    const signer = await provider.getSigner();
    const address = await signer.getAddress();

    // Verify we're on the correct network
    const network = await provider.getNetwork();
    if (Number(network.chainId) !== 1337) {
      throw new Error('Failed to switch to Hardhat local network (Chain ID: 1337)');
    }

    return {
      provider,
      signer,
      address,
      ethereum,
    };
  } catch (error) {
    console.error('Wallet connection error:', error);
    throw error;
  }
};

/**
 * Sign a message using the connected wallet
 */
export const signMessage = async (message, signer) => {
  try {
    const signature = await signer.signMessage(message);
    return signature;
  } catch (error) {
    console.error('Message signing error:', error);
    throw new Error('Failed to sign message. Please try again.');
  }
};

// Cache for contract configuration
let contractConfigCache = null;
let configCacheTimestamp = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

/**
 * Fetch contract configuration from backend (with caching)
 */
export const getContractConfig = async () => {
  // Return cached config if still valid
  if (contractConfigCache && (Date.now() - configCacheTimestamp) < CACHE_DURATION) {
    return contractConfigCache;
  }

  try {
    const response = await fetch(`${WEB3_CONFIG.BACKEND_URL}/`);
    if (!response.ok) {
      throw new Error('Failed to fetch contract configuration');
    }

    const data = await response.json();
    const config = {
      contractAddress: data.contract,
      chainId: data.chain_id,
    };

    // Cache the result
    contractConfigCache = config;
    configCacheTimestamp = Date.now();

    return config;
  } catch (error) {
    console.error('Contract config fetch error:', error);
    throw new Error('Unable to connect to backend service');
  }
};

/**
 * Clear contract config cache (useful for testing or when config changes)
 */
export const clearContractConfigCache = () => {
  contractConfigCache = null;
  configCacheTimestamp = 0;
};

/**
 * Create a contract instance for direct interaction
 */
export const createContractInstance = async (signer) => {
  try {
    // First get contract address from backend
    const { contractAddress } = await getContractConfig();

    // Minimal ABI for CitationRegistry functions we need
    const minimalABI = [
      // Read functions
      {
        inputs: [{ internalType: 'uint256', name: 'docId', type: 'uint256' }],
        name: 'getPaper',
        outputs: [
          { internalType: 'bytes32', name: 'metadataRoot', type: 'bytes32' },
          { internalType: 'bytes32', name: 'fullTextRoot', type: 'bytes32' },
          { internalType: 'bool', name: 'isRetracted', type: 'bool' }
        ],
        stateMutability: 'view',
        type: 'function',
      },
      {
        inputs: [{ internalType: 'bytes32', name: 'hashedDoi', type: 'bytes32' }],
        name: 'getDocIdByDoi',
        outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
        stateMutability: 'view',
        type: 'function',
      },
      {
        inputs: [{ internalType: 'bytes32', name: 'hashedTad', type: 'bytes32' }],
        name: 'getDocIdByTAD',
        outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
        stateMutability: 'view',
        type: 'function',
      },
      {
        inputs: [
          { internalType: 'bytes32', name: 'role', type: 'bytes32' },
          { internalType: 'address', name: 'account', type: 'address' }
        ],
        name: 'hasRole',
        outputs: [{ internalType: 'bool', name: '', type: 'bool' }],
        stateMutability: 'view',
        type: 'function',
      },
      // Write functions
      {
        inputs: [
          { internalType: 'bytes32', name: 'hashedDoi', type: 'bytes32' },
          { internalType: 'bytes32', name: 'hashedTad', type: 'bytes32' },
          { internalType: 'bytes32', name: 'metadataRoot', type: 'bytes32' },
          { internalType: 'bytes32', name: 'fullTextRoot', type: 'bytes32' }
        ],
        name: 'registerPaper',
        outputs: [{ internalType: 'uint256', name: 'docId', type: 'uint256' }],
        stateMutability: 'nonpayable',
        type: 'function',
      },
      {
        inputs: [{ internalType: 'uint256', name: 'docId', type: 'uint256' }],
        name: 'retractPaper',
        outputs: [],
        stateMutability: 'nonpayable',
        type: 'function',
      },
      // Events
      {
        anonymous: false,
        inputs: [
          { indexed: true, internalType: 'address', name: 'registrar', type: 'address' },
          { indexed: true, internalType: 'uint256', name: 'docId', type: 'uint256' },
          { indexed: true, internalType: 'bytes32', name: 'hashedDoi', type: 'bytes32' },
          { indexed: true, internalType: 'bytes32', name: 'hashedTad', type: 'bytes32' }
        ],
        name: 'PaperRegistered',
        type: 'event',
      },
      {
        anonymous: false,
        inputs: [
          { indexed: true, internalType: 'address', name: 'retractor', type: 'address' },
          { indexed: true, internalType: 'uint256', name: 'docId', type: 'uint256' }
        ],
        name: 'PaperRetracted',
        type: 'event',
      },
    ];

    return new ethers.Contract(contractAddress, minimalABI, signer);
  } catch (error) {
    console.error('Contract creation error:', error);
    throw new Error('Failed to create contract instance');
  }
};

/**
 * Create a read-only contract instance for validation (no signing required)
 */
export const createReadOnlyContractInstance = async () => {
  try {
    // First get contract address from backend
    const { contractAddress } = await getContractConfig();

    // Get provider without signer
    const ethereum = await detectEthereumProvider();
    if (!ethereum) {
      throw new Error('Web3 wallet is not installed');
    }
    const provider = new ethers.BrowserProvider(ethereum);

    // Read-only ABI (only view functions)
    const readOnlyABI = [
      {
        inputs: [{ internalType: 'uint256', name: 'docId', type: 'uint256' }],
        name: 'getPaper',
        outputs: [
          { internalType: 'bytes32', name: 'metadataRoot', type: 'bytes32' },
          { internalType: 'bytes32', name: 'fullTextRoot', type: 'bytes32' },
          { internalType: 'bool', name: 'isRetracted', type: 'bool' }
        ],
        stateMutability: 'view',
        type: 'function',
      },
      {
        inputs: [{ internalType: 'bytes32', name: 'hashedDoi', type: 'bytes32' }],
        name: 'getDocIdByDoi',
        outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
        stateMutability: 'view',
        type: 'function',
      },
      {
        inputs: [{ internalType: 'bytes32', name: 'hashedTad', type: 'bytes32' }],
        name: 'getDocIdByTAD',
        outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
        stateMutability: 'view',
        type: 'function',
      },
      {
        inputs: [
          { internalType: 'bytes32', name: 'role', type: 'bytes32' },
          { internalType: 'address', name: 'account', type: 'address' }
        ],
        name: 'hasRole',
        outputs: [{ internalType: 'bool', name: '', type: 'bool' }],
        stateMutability: 'view',
        type: 'function',
      }
    ];

    return new ethers.Contract(contractAddress, readOnlyABI, provider);
  } catch (error) {
    console.error('Read-only contract creation error:', error);
    throw new Error('Failed to create read-only contract instance');
  }
};

/**
 * Check if a paper is retracted by querying the smart contract directly
 */
export const checkRetractionStatus = async (docId, contract) => {
  try {
    // eslint-disable-next-line no-unused-vars
    const [metadataRoot, fullTextRoot, isRetracted] = await contract.getPaper(docId);
    return {
      docId,
      isRetracted,
      metadataRoot,
      fullTextRoot,
    };
  } catch (error) {
    console.error('Retraction status check error:', error);
    throw new Error('Failed to check retraction status');
  }
};

/**
 * Retract a paper by calling the smart contract directly
 */
export const retractPaper = async (docId, signer, expectedMetadataRoot = null) => {
  try {
    if (!docId || docId <= 0) {
      throw new Error('Invalid docId: must be a positive number');
    }

    const contract = await createContractInstance(signer);

    // Check if docId exists and validate metadata matches
    try {
      // eslint-disable-next-line no-unused-vars
      const [metadataRoot, fullTextRoot, isRetracted] = await contract.getPaper(docId);
      if (isRetracted) {
        throw new Error('This paper has already been retracted.');
      }

      // Validate metadata matches if provided (important security check)
      if (expectedMetadataRoot && metadataRoot !== expectedMetadataRoot) {
        console.log("Metadata mismatch - Expected:", expectedMetadataRoot, "Actual:", metadataRoot);
        throw new Error('Validation failed: Citation metadata does not match blockchain record.');
      }

      console.log("Paper validation successful - Metadata root matches");
    } catch (checkError) {
      if (checkError.message.includes('invalid docId')) {
        throw new Error('Paper with this ID does not exist in the registry.');
      }
      throw checkError;
    }

    // Send retraction transaction
    const tx = await contract.retractPaper(docId);

    if (!tx) {
      throw new Error('Failed to create retraction transaction');
    }

    // Wait for transaction confirmation
    const receipt = await tx.wait();

    // Check for the PaperRetracted event
    const retractionEvent = receipt.logs.find(log => {
      try {
        const parsed = contract.interface.parseLog(log);
        return parsed.name === 'PaperRetracted';
      } catch {
        return false;
      }
    });

    return {
      success: true,
      transactionHash: tx.hash,
      blockNumber: receipt.blockNumber,
      docId,
      eventFound: !!retractionEvent,
    };
  } catch (error) {
    console.error('Paper retraction error:', error);

    // Provide more specific error messages
    if (error.message.includes('REGISTRAR_ROLE')) {
      throw new Error('Your account does not have permission to retract papers. You need the REGISTRAR_ROLE.');
    }
    if (error.message.includes('docId does not exist') || error.message.includes('invalid docId')) {
      throw new Error('Paper with this ID does not exist in the registry.');
    }
    if (error.message.includes('already retracted')) {
      throw new Error('This paper has already been retracted.');
    }
    if (error.message.includes('user rejected')) {
      throw new Error('Transaction cancelled: You rejected the transaction in your wallet.');
    }
    if (error.message.includes('insufficient funds')) {
      throw new Error('Insufficient funds: Not enough ETH to pay for gas fees.');
    }

    throw new Error('Failed to retract paper: ' + error.message);
  }
};

/**
 * Format wallet address for display
 */
export const formatAddress = (address) => {
  if (!address) return '';
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
};

/**
 * Check if Web3 wallet is installed
 */
export const isMetaMaskInstalled = () => {
  return typeof window !== 'undefined' && typeof window.ethereum !== 'undefined';
};

/**
 * Check backend service health and contract configuration
 */
export const checkBackendHealth = async () => {
  try {
    const response = await fetch(`${WEB3_CONFIG.BACKEND_URL}/`);

    if (!response.ok) {
      throw new Error(`Backend unavailable: ${response.status}`);
    }

    const data = await response.json();

    return {
      ok: data.ok,
      chainId: data.chain_id,
      contractAddress: data.contract,
      hasPrivateKey: data.has_private_key,
      gasMode: data.gas_mode,
    };
  } catch (error) {
    console.error('Backend health check error:', error);
    throw new Error('Backend service is unavailable');
  }
};