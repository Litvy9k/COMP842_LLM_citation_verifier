// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/access/Ownable.sol";

contract CitationRegistry is Ownable {
    constructor() Ownable(msg.sender) {}

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
        uint256 docId,
        bytes32 indexed hashedDoi,
        bytes32 indexed hashedTAH
    );

    function registerPaper(
        bytes32 hashedDoi,
        bytes32 hashedTAH,
        bytes32 metadataRoot,
        bytes32 fullTextRoot
    ) external onlyOwner returns (uint256 docId) {
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

        emit PaperRegistered(docId, hashedDoi, hashedTAH);
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