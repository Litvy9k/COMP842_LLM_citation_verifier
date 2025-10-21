## The smart contract currently expects the following from the Merkle module (interface can be adjusted if needed):

Four bytes32 values, in this order:

1.  `hashedDoi`: SHA256(canonicaljson("10.3352/jeehp.2013.10.3")) (use the full DOI string; arXiv papers use DOI format 10.48550/arxiv.XXXXX)
2.  `hashedTAD`: SHA256(canonicaljson({"title": "...", "authors": [...], "date": "YYYY-MM-DD"}))
3.  `metadataRoot`: Merkle root of full metadata
4.  `fullTextRoot`: Merkle root of text chunks

### For Backend Integration

1.  **Admin Authentication (for API Access):**
    *   Verify admin's signature using `Account.recover_message`.
    *   Check permissions via `hasRole(REGISTRAR_ROLE, recovered_address)`.

2.  **Register a paper (Backend Signs):**
    *   Call `registerPaper(bytes32 hashedDoi, bytes32 hashedTAD, bytes32 metadataRoot, bytes32 fullTextRoot)`.
    *   Transaction `msg.sender` must hold `REGISTRAR_ROLE`.

3.  **Look up by DOI**

    ```solidity
    function getDocIdByDoi(bytes32 hashedDoi) external view returns (uint256)
    ```

    *   Returns 0 if not found

4.  **Look up by Title+Author+Date**

    ```solidity
    function getDocIdByTAD(bytes32 hashedTAD) external view returns (uint256)
    ```

    *   Returns 0 if not found

5.  **Fetch paper roots and status**

    ```solidity
    function getPaper(uint256 docId) external view returns (bytes32 metadataRoot, bytes32 fullTextRoot, bool isRetractedStatus)
    ```

    *   Reverts if `docId` is 0 or unregistered.
    *   Returns the Merkle roots and the retraction status.

6.  **Grant Admin Role**

    ```solidity
    function grantRegistrarRole(address account) external
    ```

    *   Only callable by an account with `DEFAULT_ADMIN_ROLE`.

7.  **Revoke Admin Role**

    ```solidity
    function revokeRegistrarRole(address account) external
    ```

    *   Only callable by an account with `DEFAULT_ADMIN_ROLE`.

### For Web Integration (Wallet)

1.  **Admin Authentication:**
    *   Verify signature using wallet provider (e.g., MetaMask).
    *   Check permissions via `hasRole(REGISTRAR_ROLE, connected_wallet_address)`.

2.  **Register a paper (Web Interface Signs):**
    *   Get `metadataRoot`, `fullTextRoot`, `hashedDoi`, `hashedTAD` from backend API.
    *   Call `registerPaper(bytes32 hashedDoi, bytes32 hashedTAD, bytes32 metadataRoot, bytes32 fullTextRoot)`.
    *   Transaction `msg.sender` (connected wallet) must hold `REGISTRAR_ROLE`.

3.  **Retract a paper (Web Interface Signs):**
    *   Call `retractPaper(uint256 docId)`.
    *   Transaction `msg.sender` (connected wallet) must hold `REGISTRAR_ROLE`.
    *   Emits `PaperRetracted` event.

### How to Test the Smart Contract (Direct Interaction)

1.  **Install Node.js and npm (once)**
    ```bash
    # Visit: https://nodejs.org/ to download and install
    # npm is included with Node.js installation
    ```

2.  **Initialize Hardhat project in the blockchain folder**
    ```bash
    npm init -y
    npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
    npm install @openzeppelin/contracts
    ```

3.  **Ensure your contract is at: `blockchain/contracts/CitationRegistry.sol`**

4.  **Start local Ethereum node**
    ```bash
    npx hardhat node
    ```
    *Note: Take note of the accounts and private keys printed by `hardhat node`. The first account (`0xf39...`) will be the deployer and initial admin. The second account (`0x709...`) will be used as an example for adding a new admin.*

5.  **Deploy the contract**
    ```bash
    npx hardhat run scripts/deploy.js --network localhost
    ```
    *This command deploys the contract and grants the `REGISTRAR_ROLE` to the deployer's address (`0xf39...`). The deployer automatically receives the `DEFAULT_ADMIN_ROLE`. The `contractAddress` will be printed in the output.*

6.  **Register a paper directly (replace `<CONTRACT_ADDR>` with the address printed in step 5)**
    *   The four test hashes correspond to:
        *   `hashedDoi`
        *   `hashedTAD`
        *   `metadataRoot`
        *   `fullTextRoot`

    Create a test script `scripts/register_paper.js`:
    ```javascript
    const { ethers } = require("hardhat");

    async function main() {
      const contractAddress = "<CONTRACT_ADDR>";
      const [deployer] = await ethers.getSigners();

      const CitationRegistry = await ethers.getContractFactory("CitationRegistry");
      const contract = CitationRegistry.attach(contractAddress);

      const tx = await contract.registerPaper(
        "0x1111111111111111111111111111111111111111111111111111111111111111", // hashedDoi
        "0x2222222222222222222222222222222222222222222222222222222222222222", // hashedTAD
        "0x3333333333333333333333333333333333333333333333333333333333333333", // metadataRoot
        "0x4444444444444444444444444444444444444444444444444444444444444444"  // fullTextRoot
      );

      await tx.wait();
      console.log("Paper registered with docId: 1");
    }

    main().catch(console.error);
    ```

    Then run:
    ```bash
    npx hardhat run scripts/register_paper.js --network localhost
    ```

7.  **Grant `REGISTRAR_ROLE` to another admin (using a custom script after deployment)**
    *   Replace `<CONTRACT_ADDR>` with the address printed in step 5.
    *   Replace `<NEW_ADMIN_ADDRESS>` with the address of the admin you want to add (e.g., `0x70997970C51812dc3A010C7d01b50e0d17dc79C8`).

    Create a test script `scripts/grant_role.js`:
    ```javascript
    const { ethers } = require("hardhat");

    async function main() {
      const contractAddress = "<CONTRACT_ADDR>";
      const [deployer] = await ethers.getSigners();

      const CitationRegistry = await ethers.getContractFactory("CitationRegistry");
      const contract = CitationRegistry.attach(contractAddress);

      const tx = await contract.grantRegistrarRole("<NEW_ADMIN_ADDRESS>");
      await tx.wait();

      console.log("REGISTRAR_ROLE granted to:", "<NEW_ADMIN_ADDRESS>");
    }

    main().catch(console.error);
    ```

    Then run:
    ```bash
    npx hardhat run scripts/grant_role.js --network localhost
    ```

8.  **Revoke `REGISTRAR_ROLE` from an admin (using a custom script after deployment)**
    *   Replace `<CONTRACT_ADDR>` with the address printed in step 5.
    *   Replace `<ADMIN_TO_REVOKE>` with the address of the admin you want to remove.

    Create a test script `scripts/revoke_role.js`:
    ```javascript
    const { ethers } = require("hardhat");

    async function main() {
      const contractAddress = "<CONTRACT_ADDR>";
      const [deployer] = await ethers.getSigners();

      const CitationRegistry = await ethers.getContractFactory("CitationRegistry");
      const contract = CitationRegistry.attach(contractAddress);

      const tx = await contract.revokeRegistrarRole("<ADMIN_TO_REVOKE>");
      await tx.wait();

      console.log("REGISTRAR_ROLE revoked from:", "<ADMIN_TO_REVOKE>");
    }

    main().catch(console.error);
    ```

    Then run:
    ```bash
    npx hardhat run scripts/revoke_role.js --network localhost
    ```

9.  **Retract a paper (replace `<CONTRACT_ADDR>` with the address printed in step 5)**
    *   Replace `<DOC_ID_TO_RETRACT>` with the `docId` of the paper you want to retract (e.g., `1`).

    Create a test script `scripts/retract_paper.js`:
    ```javascript
    const { ethers } = require("hardhat");

    async function main() {
      const contractAddress = "<CONTRACT_ADDR>";
      const [deployer] = await ethers.getSigners();

      const CitationRegistry = await ethers.getContractFactory("CitationRegistry");
      const contract = CitationRegistry.attach(contractAddress);

      const tx = await contract.retractPaper(<DOC_ID_TO_RETRACT>);
      await tx.wait();

      console.log("Paper retracted with docId:", <DOC_ID_TO_RETRACT>);
    }

    main().catch(console.error);
    ```

    Then run:
    ```bash
    npx hardhat run scripts/retract_paper.js --network localhost
    ```

10. **Test lookup**
    *   Create a test script `scripts/test_lookup.js`:
    ```javascript
    const { ethers } = require("hardhat");

    async function main() {
      const contractAddress = "<CONTRACT_ADDR>";
      const [deployer] = await ethers.getSigners();

      const CitationRegistry = await ethers.getContractFactory("CitationRegistry");
      const contract = CitationRegistry.attach(contractAddress);

      // Get docId by DOI
      const docIdByDoi = await contract.getDocIdByDoi("0x1111111111111111111111111111111111111111111111111111111111111111");
      console.log("docId by DOI:", docIdByDoi.toString());

      // Get paper details by docId
      const paper = await contract.getPaper(1);
      console.log("Paper details:", {
        metadataRoot: paper.metadataRoot,
        fullTextRoot: paper.fullTextRoot,
        isRetracted: paper.isRetracted
      });

      // Get docId by TAD
      const docIdByTAD = await contract.getDocIdByTAD("0x2222222222222222222222222222222222222222222222222222222222222222");
      console.log("docId by TAD:", docIdByTAD.toString());
    }

    main().catch(console.error);
    ```

    Then run:
    ```bash
    npx hardhat run scripts/test_lookup.js --network localhost
    ```
