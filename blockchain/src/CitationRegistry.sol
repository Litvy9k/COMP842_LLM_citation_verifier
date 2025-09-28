// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/access/Ownable.sol";

contract CitationRegistry is Ownable {
    constructor() Ownable(msg.sender) {}

    uint256 public nextDocId = 1;

    // Mapping: hashed(externalId) → docId
    // externalId = "doi:10.xxxx/..." OR "arxiv:xxxx.xxxxx"
    mapping(bytes32 => uint256) public externalIdToDocId;

    // Mapping: hashed({title, authors, year}) → docId
    mapping(bytes32 => uint256) public tahToDocId; // TAH = Title+Author+Year

    struct Paper {
        bytes32 metadataRoot;
        bytes32 fullTextRoot;
    }

    mapping(uint256 => Paper) public papers;

    event PaperRegistered(
        uint256 docId,
        bytes32 indexed hashedExternalId,
        bytes32 indexed hashedTAH
    );

    function registerPaper(
        bytes32 hashedExternalId,
        bytes32 hashedTAH,
        bytes32 metadataRoot,
        bytes32 fullTextRoot
    ) external onlyOwner returns (uint256 docId) {
        // Require at least one identifier
        require(
            hashedExternalId != bytes32(0) || hashedTAH != bytes32(0),
            "CitationRegistry: at least one identifier required"
        );
        // Require non-zero roots
        require(metadataRoot != bytes32(0), "CitationRegistry: metadataRoot required");

        // Prevent duplicates
        if (hashedExternalId != bytes32(0)) {
            require(
                externalIdToDocId[hashedExternalId] == 0,
                "CitationRegistry: externalId already registered"
            );
        }
        if (hashedTAH != bytes32(0)) {
            require(
                tahToDocId[hashedTAH] == 0,
                "CitationRegistry: TAH already registered"
            );
        }

        docId = nextDocId++;
        if (hashedExternalId != bytes32(0)) {
            externalIdToDocId[hashedExternalId] = docId;
        }
        if (hashedTAH != bytes32(0)) {
            tahToDocId[hashedTAH] = docId;
        }

        papers[docId] = Paper({
            metadataRoot: metadataRoot,
            fullTextRoot: fullTextRoot
        });

        emit PaperRegistered(docId, hashedExternalId, hashedTAH);
        return docId;
    }

    // --- READ FUNCTIONS (for API) ---

    function getDocIdByExternalId(bytes32 hashedExternalId) external view returns (uint256) {
        return externalIdToDocId[hashedExternalId];
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
