/**
 * Canonicalization utilities
 */

import { keccak_256 } from 'js-sha3';

export function normalizeDoi(doi) {
  if (!doi) {
    return "";
  }
  let v = doi.trim();
  // Remove DOI prefixes if present
  const prefixes = ["doi:", "https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/"];
  for (const p of prefixes) {
    if (v.toLowerCase().startsWith(p)) {
      v = v.slice(p.length);
      break;
    }
  }
  return v;
}

// NFKC normalization helper
function nfkcNormalize(str) {
  if (str === null || str === undefined) {
    return '';
  }
  return String(str).normalize('NFKC').trim();
}

// Canonicalize string with NFKC normalization
export function canonStr(str, lower = false) {
  let normalized = nfkcNormalize(str);
  if (lower) {
    normalized = normalized.toLowerCase();
  }
  // Convert to bytes (UTF-8)
  return new TextEncoder().encode(normalized);
}

export function h00(bytes) {
  const prefixed = new Uint8Array([0x00, ...bytes]);
  return new Uint8Array(keccak_256.arrayBuffer(prefixed));
}

export function h01(leftBytes, rightBytes) {
  const prefixed = new Uint8Array([0x01, ...leftBytes, ...rightBytes]);
  return new Uint8Array(keccak_256.arrayBuffer(prefixed));
}

export function reducePairs(nodes) {
  if (!nodes || nodes.length === 0) {
    return h00(new Uint8Array());
  }

  let level = [...nodes];
  while (level.length > 1) {
    const next = [];
    for (let i = 0; i < level.length; i += 2) {
      const left = level[i];
      const right = (i + 1 < level.length) ? level[i + 1] : level[i];
      next.push(h01(left, right));
    }
    level = next;
  }
  return level[0];
}

export function authorsRoot(authors) {
  // Build author leaves with NFKC normalization
  const leaves = (authors || []).map(author => h00(canonStr(String(author))));
  return reducePairs(leaves);
}

export function hashHashedDoi(doi) {
  // Leaf hash of lowercased DOI
  return h00(canonStr(doi, true));
}

export function hashHashedTAD(title, authors, dateIso) {
  // Convert authors to array (accepts comma-separated string or array)
  const authorsArray = Array.isArray(authors)
    ? authors.map(a => String(a).trim())
    : String(authors || "").split(',').map(a => a.trim()).filter(a => a);

  // Compute TAD hash:
  // 1. Hash title with NFKC normalization
  const h_title = h00(canonStr(title || ""));

  // 2. Create Merkle tree of authors
  const h_auth = authorsRoot(authorsArray);

  // 3. Combine title+authors
  const n_ta = h01(h_title, h_auth);

  // 4. Hash date with NFKC normalization
  const h_date = h00(canonStr(dateIso));

  // 5. Final combination: (title+authors) + date
  return h01(n_ta, h_date);
}

export function metadataRootFrom(metadata) {
  const { doi = '', title = '', authors = [], date = '' } = metadata;

  // Convert authors to array format for consistency
  const authorsArray = Array.isArray(authors)
    ? authors.map(a => String(a).trim())
    : String(authors || "").split(',').map(a => a.trim()).filter(a => a);

  // Compute metadata root:
  // h_title = _h00(_canon_str(title))
  const h_title = h00(canonStr(title));
  
  // h_auth = _authors_root(authors)
  const h_auth = authorsRoot(authorsArray);
  
  // n_ta = _h01(h_title, h_auth)
  const n_ta = h01(h_title, h_auth);
  
  // h_doi = leaf hash of lowercased DOI
  const h_doi = h00(canonStr(doi, true));
  
  // h_date = _h00(_canon_str(norm_date))
  const h_date = h00(canonStr(date));
  
  // n_dd = _h01(h_doi, h_date)
  const n_dd = h01(h_doi, h_date);
  
  // return _h01(n_ta, n_dd)
  return h01(n_ta, n_dd);
}

export function fulltextRootFrom(text, chunkSize = 4096) {
  if (!text) {
    return new Uint8Array(32).fill(0); // 32 zero bytes
  }

  const encoder = new TextEncoder();
  const bytes = encoder.encode(text);
  const leaves = [];
  const cs = Math.max(1, parseInt(chunkSize) || 4096);

  for (let i = 0; i < bytes.length; i += cs) {
    const chunk = bytes.slice(i, i + cs);
    leaves.push(h00(chunk));
  }

  return reducePairs(leaves);
}

export function bytesToHex(bytes) {
  return '0x' + Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

export async function generateAuthSignature(doi, signer) {
  const message = `Register paper: ${doi}`;
  const signature = await signer.signMessage(message);
  return { message, signature };
}

export function calculateValidationHashes(citation) {
  const { doi, title, authors, date, abstract, journal } = citation;

  // Validate required fields
  if (!doi?.trim() || !title?.trim() || !authors?.trim() || !date?.trim()) {
    throw new Error('Please fill in all required fields (DOI, Title, Authors, Date).');
  }

  // Parse authors (handle both string and array)
  const authorsArray = Array.isArray(authors)
    ? authors
    : authors.split(',').map(a => a.trim()).filter(a => a);

  // Calculate hashes only - no signature
  const hashedDoi = hashHashedDoi(doi);
  const hashedTad = hashHashedTAD(title, authorsArray, date);
  const metadataRoot = metadataRootFrom({
    doi, title, authors: authorsArray, date, abstract, journal
  });
  const fulltextRoot = fulltextRootFrom('', 1024); // No full text for manual registration

  return {
    hashedDoi: bytesToHex(hashedDoi),
    hashedTad: bytesToHex(hashedTad),
    metadataRoot: bytesToHex(metadataRoot),
    fulltextRoot: bytesToHex(fulltextRoot),
  };
}

export async function calculateRegistrationData(citation, signer) {
  const { doi, title, authors, date, abstract, journal } = citation;

  // Validate required fields
  if (!doi?.trim() || !title?.trim() || !authors?.trim() || !date?.trim()) {
    throw new Error('Please fill in all required fields (DOI, Title, Authors, Date).');
  }

  // Parse authors (handle both string and array)
  const authorsArray = Array.isArray(authors)
    ? authors
    : authors.split(',').map(a => a.trim()).filter(a => a);

  // Calculate hashes
  const hashedDoi = hashHashedDoi(doi);
  const hashedTad = hashHashedTAD(title, authorsArray, date);
  const metadataRoot = metadataRootFrom({
    doi, title, authors: authorsArray, date, abstract, journal
  });
  const fulltextRoot = fulltextRootFrom('', 1024); // No full text for manual registration

  // Generate signature
  const { signature, message } = await generateAuthSignature(doi, signer);

  return {
    transactionData: {
      hashedDoi: bytesToHex(hashedDoi),
      hashedTad: bytesToHex(hashedTad),
      metadataRoot: bytesToHex(metadataRoot),
      fulltextRoot: bytesToHex(fulltextRoot),
    },
    auth: {
      signature,
      message,
    }
  };
}