// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/access/AccessControl.sol";

contract CitationRegistry is AccessControl {
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");

    uint256 public nextDocId = 1;
    // Mapping: hashed(doi) → docId
    // doi = "10.xxxx/..." (e.g., "10.48550/arxiv.2311.05232")
    mapping(bytes32 => uint256) public doiToDocId;
    // Mapping: hashed({title, authors, year}) → docId
    mapping(bytes32 => uint256) public tahToDocId; // TAH = Title+Author+Year

    struct Paper {
        bytes32 metadataRoot;
        bytes32 fullTextRoot;
    }
    mapping(uint256 => Paper) public papers;

    event PaperRegistered(
        address indexed registrar,      // The backend server (msg.sender)
        address indexed originalAdmin,  // The admin who initiated the request
        uint256 docId,
        bytes32 indexed hashedDoi,
        bytes32 hashedTAH
    );

    constructor(address initialRegistrar) {
        // Grant the REGISTRAR_ROLE to the backend server's address during deployment
        _grantRole(REGISTRAR_ROLE, initialRegistrar);
        // Grant DEFAULT_ADMIN_ROLE to the deployer for future role management
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    function registerPaper(
        address originalAdmin, // The admin who initiated the request
        bytes32 hashedDoi,
        bytes32 hashedTAH,
        bytes32 metadataRoot,
        bytes32 fullTextRoot
    ) external onlyRole(REGISTRAR_ROLE) returns (uint256 docId) {
        // Require at least one identifier
        require(
            hashedDoi != bytes32(0) || hashedTAH != bytes32(0),
            "CitationRegistry: at least one identifier required"
        );
        // Require non-zero roots
        require(metadataRoot != bytes32(0), "CitationRegistry: metadataRoot required");
        // Prevent duplicates
        if (hashedDoi != bytes32(0)) {
            require(
                doiToDocId[hashedDoi] == 0,
                "CitationRegistry: DOI already registered"
            );
        }
        if (hashedTAH != bytes32(0)) {
            require(
                tahToDocId[hashedTAH] == 0,
                "CitationRegistry: TAH already registered"
            );
        }
        docId = nextDocId++;
        if (hashedDoi != bytes32(0)) {
            doiToDocId[hashedDoi] = docId;
        }
        if (hashedTAH != bytes32(0)) {
            tahToDocId[hashedTAH] = docId;
        }
        papers[docId] = Paper({
            metadataRoot: metadataRoot,
            fullTextRoot: fullTextRoot
        });

        emit PaperRegistered(msg.sender, originalAdmin, docId, hashedDoi, hashedTAH);
        return docId;
    }

    // --- READ FUNCTIONS (for API) ---
    function getDocIdByDoi(bytes32 hashedDoi) external view returns (uint256) {
        return doiToDocId[hashedDoi];
    }

    function getDocIdByTAH(bytes32 hashedTAH) external view returns (uint256) {
        return tahToDocId[hashedTAH];
    }

    function getPaper(uint256 docId) external view returns (bytes32 metadataRoot, bytes32 fullTextRoot) {
        require(docId > 0 && docId < nextDocId, "CitationRegistry: invalid docId");
        Paper memory p = papers[docId];
        return (p.metadataRoot, p.fullTextRoot);
    }
}
