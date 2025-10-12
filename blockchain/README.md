## The smart contract currently expects the following from the Merkle module (interface can be adjusted if needed):

Four bytes32 values, in this order (plus the initiating admin address):

1.  `originalAdmin`: The address of the admin who initiated the request (provided by the backend, recovered from the web signature).
2.  `hashedDoi`: SHA256(canonicaljson("10.3352/jeehp.2013.10.3")) (use the full DOI string; arXiv papers use DOI format 10.48550/arxiv.XXXXX)
3.  `hashedTAH`: SHA256(canonicaljson({"title": "...", "authors": [...], "year": 2023}))
4.  `metadataRoot`: Merkle root of full metadata
5.  `fullTextRoot`: Merkle root of text chunks

### For Backend Integration

1.  **Admin Authentication:**
    *   Admins authenticate with the backend API by signing a specific message using their Ethereum wallet within the web interface.
    *   The backend verifies the signature's validity and checks if the recovered address has the necessary permissions.
    *   The specific on-chain check involves calling the `hasRole(bytes32 role, address account)` function on the deployed contract instance. The backend verifies `contract.hasRole(REGISTRAR_ROLE, recovered_address)` returns `true`.

2.  **Register a paper**

    ```solidity
    function registerPaper(
        address originalAdmin,
        bytes32 hashedDoi,
        bytes32 hashedTAH,
        bytes32 metadataRoot,
        bytes32 fullTextRoot
    ) external returns (uint256 docId)
    ```

    *   Only callable by an account with the `REGISTRAR_ROLE`.
    *   Returns the assigned `docId` (e.g., 1, 2, ...).
    *   Emits `PaperRegistered` event including both the `registrar` (msg.sender) and the `originalAdmin`.

3.  **Look up by DOI**

    ```solidity
    function getDocIdByDoi(bytes32 hashedDoi) external view returns (uint256)
    ```

    *   Returns 0 if not found

4.  **Look up by Title+Author+Year**

    ```solidity
    function getDocIdByTAH(bytes32 hashedTAH) external view returns (uint256)
    ```

    *   Returns 0 if not found

5.  **Fetch paper roots**

    ```solidity
    function getPaper(uint256 docId) external view returns (bytes32 metadataRoot, bytes32 fullTextRoot)
    ```

    *   Reverts if `docId` is 0 or unregistered

### How to Test the Smart Contract (Direct Interaction)

1.  **Install Foundry (once)**
    ```bash
    curl -L https://foundry.paradigm.xyz | bash
    source ~/.bashrc  # or ~/.zshrc, depending on your shell
    foundryup
    ```

2.  **Initialize Foundry project in the blockchain folder**
    ```bash
    forge init
    ```

3.  **Ensure your contract is at: `blockchain/src/CitationRegistry.sol`**

4.  **Install OpenZeppelin dependencies in the blockchain folder**
    ```bash
    forge install OpenZeppelin/openzeppelin-contracts
    ```

5.  **Start local Ethereum node**
    ```bash
    anvil
    ```
    *Note: Take note of the accounts and private keys printed by `anvil`. You'll need one for deployment (deployer) and one to be granted the relayer role (relayer).*

6.  **Deploy the contract**
    *   Choose an account from `anvil` to act as the backend relayer. Let's call its address `RELAYER_ADDRESS`.
    *   Use the private key of *another* `anvil` account (or the same, if desired for testing) to deploy the contract. Let's call this deployer's private key `PK_DEPLOYER`.
    ```bash
    forge create src/CitationRegistry.sol:CitationRegistry \
      --constructor-args <RELAYER_ADDRESS> \
      --rpc-url http://127.0.0.1:8545 \
      --private-key <PK_DEPLOYER> \
      --broadcast
    ```
    *Replace `<RELAYER_ADDRESS>` with the address you want to authorize for registrations (e.g., the one associated with your backend's private key). Replace `<PK_DEPLOYER>` with the private key of the account used for deployment.*

7.  **Register a paper (replace `<CONTRACT_ADDR>` with the address printed in step 6, `<RELAYER_PRIVATE_KEY>` with the private key corresponding to `<RELAYER_ADDRESS>` from step 6, and `<INITIATING_ADMIN_ADDRESS>` with an address you want to log as the initiator)**
    *   The four test hashes correspond to:
        *   `hashedDoi`
        *   `hashedTAH`
        *   `metadataRoot`
        *   `fullTextRoot`
    ```bash
    cast send <CONTRACT_ADDR> "registerPaper(address,bytes32,bytes32,bytes32,bytes32)" \
      <INITIATING_ADMIN_ADDRESS> \
      0x1111111111111111111111111111111111111111111111111111111111111111 \
      0x2222222222222222222222222222222222222222222222222222222222222222 \
      0x3333333333333333333333333333333333333333333333333333333333333333 \
      0x4444444444444444444444444444444444444444444444444444444444444444 \
      --rpc-url http://127.0.0.1:8545 \
      --private-key <RELAYER_PRIVATE_KEY>
    ```

8.  **Test lookup**
    ```bash
    # Get docId by DOI
    cast call <CONTRACT_ADDR> "getDocIdByDoi(bytes32)" 0x1111111111111111111111111111111111111111111111111111111111111111
    # Get paper details by docId (assuming it was registered as ID 1)
    cast call <CONTRACT_ADDR> "getPaper(uint256)" 1
    ```
    *Note: The `PaperRegistered` event will now include the `registrar` (the backend relayer's address) and the `originalAdmin` (the address provided as `<INITIATING_ADMIN_ADDRESS>` in step 7).*
