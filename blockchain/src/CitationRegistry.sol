// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/access/AccessControl.sol";

contract CitationRegistry is AccessControl {
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");

    uint256 public nextDocId = 1;
    // Mapping: hashed(doi) → docId
    // doi = "10.xxxx/..." (e.g., "10.48550/arxiv.2311.05232")
    mapping(bytes32 => uint256) public doiToDocId;
    // Mapping: hashed({title, authors, date}) → docId
    mapping(bytes32 => uint256) public tadToDocId; // TAD = Title+Author+Date

    struct Paper {
        bytes32 metadataRoot;
        bytes32 fullTextRoot;
    }
    mapping(uint256 => Paper) public papers;

    event PaperRegistered(
        uint256 docId,
        bytes32 indexed hashedDoi,
        bytes32 indexed hashedTAD
    );

    constructor(address initialRegistrar) {
        // Grant the REGISTRAR_ROLE to the designated address during deployment
        _grantRole(REGISTRAR_ROLE, initialRegistrar);
        // Explicitly grant DEFAULT_ADMIN_ROLE to the deployer to ensure retention
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    function registerPaper(
        bytes32 hashedDoi,
        bytes32 hashedTAD,
        bytes32 metadataRoot,
        bytes32 fullTextRoot
    ) external onlyRole(REGISTRAR_ROLE) returns (uint256 docId) {
        // Require at least one identifier
        require(
            hashedDoi != bytes32(0) || hashedTAD != bytes32(0),
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
        if (hashedTAD != bytes32(0)) {
            require(
                tadToDocId[hashedTAD] == 0,
                "CitationRegistry: TAD already registered"
            );
        }
        docId = nextDocId++;
        if (hashedDoi != bytes32(0)) {
            doiToDocId[hashedDoi] = docId;
        }
        if (hashedTAD != bytes32(0)) {
            tadToDocId[hashedTAD] = docId;
        }
        papers[docId] = Paper({
            metadataRoot: metadataRoot,
            fullTextRoot: fullTextRoot
        });

        emit PaperRegistered(docId, hashedDoi, hashedTAD);
        return docId;
    }

    // --- ADMIN MANAGEMENT FUNCTIONS ---
    function grantRegistrarRole(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(REGISTRAR_ROLE, account);
    }

    function revokeRegistrarRole(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        revokeRole(REGISTRAR_ROLE, account);
    }

    // --- READ FUNCTIONS (for API) ---
    function getDocIdByDoi(bytes32 hashedDoi) external view returns (uint256) {
        return doiToDocId[hashedDoi];
    }

    function getDocIdByTAD(bytes32 hashedTAD) external view returns (uint256) {
        return tadToDocId[hashedTAD];
    }

    function getPaper(uint256 docId) external view returns (bytes32 metadataRoot, bytes32 fullTextRoot) {
        require(docId > 0 && docId < nextDocId, "CitationRegistry: invalid docId");
        Paper memory p = papers[docId];
        return (p.metadataRoot, p.fullTextRoot);
    }
}