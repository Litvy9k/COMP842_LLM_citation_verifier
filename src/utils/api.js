/**
 * API utility functions for backend communication
 */

import { WEB3_CONFIG } from './web3';

/**
 * Prepare citation registration data through backend API
 * Backend calculates Merkle trees, frontend sends the transaction
 */
export const prepareCitationRegistration = async (citationData, signer) => {
  try {
    // Create authentication message for signature
    const message = `Register paper: ${citationData.doi}`;

    // Sign the message with the user's wallet
    const signature = await signer.signMessage(message);

    // Prepare the request payload
    const payload = {
      auth: {
        message,
        signature,
        sig_type: 'eip191',
      },
      metadata: {
        doi: citationData.doi,
        title: citationData.title,
        authors: citationData.authors.split(',').map(author => author.trim()),
        date: citationData.date,
        abstract: citationData.abstract,
        journal: citationData.journal,
      },
      full_text: null, // Can be added later if needed
      chunk_size: 1024,
    };

    const response = await fetch(`${WEB3_CONFIG.BACKEND_URL}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    // Backend returns prepared data for frontend to send transaction
    return {
      success: result.ok,
      hashedDoi: result.hashed_doi,
      hashedTad: result.hashed_tad,
      metadataRoot: result.metadata_root,
      fulltextRoot: result.fulltext_root,
      // Frontend will send the transaction using these parameters
      transactionData: {
        hashedDoi: result.hashed_doi,
        hashedTad: result.hashed_tad,
        metadataRoot: result.metadata_root,
        fulltextRoot: result.fulltext_root,
      },
      message: result.message,
    };
  } catch (error) {
    console.error('Citation preparation error:', error);

    // Provide more specific error messages
    if (error.message.includes('permission denied')) {
      throw new Error('Your account does not have permission to register papers. You need the REGISTRAR_ROLE.');
    }
    if (error.message.includes('already registered')) {
      throw new Error('This paper has already been registered.');
    }
    if (error.message.includes('signature')) {
      throw new Error('Authentication failed. Please ensure you are using the correct wallet.');
    }

    throw new Error('Failed to prepare citation: ' + error.message);
  }
};

/**
 * Check retraction status through the backend API
 */
export const checkRetractionStatusAPI = async (docId, metadata = null) => {
  try {
    const payload = docId ? { doc_id: docId } : { metadata };

    const response = await fetch(`${WEB3_CONFIG.BACKEND_URL}/retraction/status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    return {
      docId: result.doc_id,
      isRetracted: result.is_retracted,
    };
  } catch (error) {
    console.error('Retraction status check error:', error);
    throw new Error('Failed to check retraction status: ' + error.message);
  }
};

/**
 * Enhanced DOI lookup with API fallback to smart contract
 */
export const lookupCitationWithFallback = async (doi, signer) => {
  try {
    // Try API first
    return await checkRetractionStatusAPI(null, { doi });
  } catch (apiError) {
    console.warn('API lookup failed, trying smart contract fallback:', apiError.message);

    try {
      // Fallback to smart contract directly
      const { createContractInstance } = await import('./web3');
      const contract = await createContractInstance(signer);

      // For direct smart contract lookup, use proper DOI canonicalization
      const { normalizeDoi, hashHashedDoi, bytesToHex } = await import('./merkle');
      const hashedDoi = bytesToHex(hashHashedDoi(doi));

      const docId = await contract.functions.getDocIdByDoi(hashedDoi);

      if (docId && docId > 0) {
        const [, , isRetracted] = await contract.functions.getPaper(docId);

        return {
          docId: Number(docId),
          isRetracted,
        };
      } else {
        throw new Error('Citation not found in blockchain');
      }
    } catch (scError) {
      console.error('Smart contract fallback also failed:', scError);
      throw new Error(`Citation not found. API error: ${apiError.message}. Smart contract error: ${scError.message}`);
    }
  }
};

/**
 * Set retraction status through the backend API
 * Note: For actual retraction, we prefer direct smart contract calls
 */
export const setRetractionStatus = async (docId, retract, signer, metadata = null) => {
  try {
    // Create authentication message for signature
    const identifier = docId ? `doc_id: ${docId}` : `metadata: ${metadata?.doi || 'unknown'}`;
    const message = `Set retraction status for ${identifier}: ${retract}`;

    // Sign the message with the user's wallet
    const signature = await signer.signMessage(message);

    const payload = {
      auth: {
        message,
        signature,
        sig_type: 'eip191',
      },
      doc_id: docId,
      metadata,
      retract,
    };

    const response = await fetch(`${WEB3_CONFIG.BACKEND_URL}/retraction/set`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    return {
      success: true,
      docId: result.doc_id,
      retract: result.retract,
      transactionHash: result.tx,
      method: result.method,
      recoveredAddress: result.recovered,
    };
  } catch (error) {
    console.error('Retraction status set error:', error);

    // Provide more specific error messages
    if (error.message.includes('permission denied')) {
      throw new Error('Your account does not have permission to modify retraction status.');
    }
    if (error.message.includes('not found')) {
      throw new Error('Paper not found.');
    }

    throw new Error('Failed to set retraction status: ' + error.message);
  }
};

/**
 * Edit a paper (retract old and register new) through the backend API
 */
export const editPaper = async (oldDocId, newCitationData, signer, oldMetadata = null) => {
  try {
    // Create authentication message for signature
    const oldIdentifier = oldDocId ? `doc_id: ${oldDocId}` : `metadata: ${oldMetadata?.doi || 'unknown'}`;
    const message = `Edit paper from ${oldIdentifier} to DOI: ${newCitationData.doi}`;

    // Sign the message with the user's wallet
    const signature = await signer.signMessage(message);

    const payload = {
      auth: {
        message,
        signature,
        sig_type: 'eip191',
      },
      old_doc_id: oldDocId,
      old_metadata: oldMetadata,
      new_metadata: {
        doi: newCitationData.doi,
        title: newCitationData.title,
        authors: newCitationData.authors.split(',').map(author => author.trim()),
        date: newCitationData.date,
        abstract: newCitationData.abstract,
        journal: newCitationData.journal,
      },
      new_full_text: null, // Can be added later if needed
      chunk_size: 1024,
    };

    const response = await fetch(`${WEB3_CONFIG.BACKEND_URL}/papers/edit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    return {
      success: result.ok,
      txRetract: result.tx_retract,
      txAdd: result.tx_add,
      newHashedDoi: result.new_hashed_doi,
      newHashedTad: result.new_hashed_tad,
      newMetadataRoot: result.new_metadata_root,
      newFulltextRoot: result.new_fulltext_root,
      recoveredAddress: result.recovered_admin,
    };
  } catch (error) {
    console.error('Paper edit error:', error);

    // Provide more specific error messages
    if (error.message.includes('permission denied')) {
      throw new Error('Your account does not have permission to edit papers.');
    }
    if (error.message.includes('not found')) {
      throw new Error('Original paper not found.');
    }

    throw new Error('Failed to edit paper: ' + error.message);
  }
};

// Cache for backend health data
let healthCache = null;
let healthCacheTimestamp = 0;
const HEALTH_CACHE_DURATION = 2 * 60 * 1000; // 2 minutes

/**
 * Check backend service health (with caching)
 */
export const checkBackendHealth = async () => {
  // Return cached health data if still valid
  if (healthCache && (Date.now() - healthCacheTimestamp) < HEALTH_CACHE_DURATION) {
    return healthCache;
  }

  try {
    const response = await fetch(`${WEB3_CONFIG.BACKEND_URL}/`);

    if (!response.ok) {
      throw new Error(`Backend unavailable: ${response.status}`);
    }

    const data = await response.json();
    const health = {
      ok: data.ok,
      chainId: data.chain_id,
      contractAddress: data.contract,
      hasPrivateKey: data.has_private_key,
      gasMode: data.gas_mode,
    };

    // Cache the result
    healthCache = health;
    healthCacheTimestamp = Date.now();

    return health;
  } catch (error) {
    console.error('Backend health check error:', error);
    throw new Error('Backend service is unavailable');
  }
};

/**
 * Clear backend health cache
 */
export const clearHealthCache = () => {
  healthCache = null;
  healthCacheTimestamp = 0;
};