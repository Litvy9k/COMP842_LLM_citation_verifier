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
    *Note: Take note of the accounts and private keys printed by `anvil`. The first account (`0xf39...`) will be the deployer and initial admin. The second account (`0x709...`) will be used as an example for adding a new admin.*

6.  **Deploy the contract**
    *   This command deploys the contract and grants the `REGISTRAR_ROLE` to the deployer's address (`0xf39...`). The deployer automatically receives the `DEFAULT_ADMIN_ROLE`.
    ```bash
    # ABI-encode the constructor argument (initialRegistrar address)
    ENCODED_ARGS=$(cast abi-encode "function(address)" <ADMIN_ADDRESS>)
    # Deploy the contract
    cast send --rpc-url http://127.0.0.1:8545 \
      --private-key <ADMIN_PRIVATE_KEY> \
      --create $(forge inspect CitationRegistry bytecode) \
      $ENCODED_ARGS
    ```
    *Replace the address and private key if you intend to use a different `anvil` account for the initial admin and deployment. The `contractAddress` printed in the output is your deployed contract address.*

7.  **Register a paper directly (replace `<CONTRACT_ADDR>` with the address printed in step 6)**
    *   The four test hashes correspond to:
        *   `hashedDoi`
        *   `hashedTAD`
        *   `metadataRoot`
        *   `fullTextRoot`
    ```bash
    cast send <CONTRACT_ADDR> "registerPaper(bytes32,bytes32,bytes32,bytes32)" \
      0x1111111111111111111111111111111111111111111111111111111111111111 \
      0x2222222222222222222222222222222222222222222222222222222222222222 \
      0x3333333333333333333333333333333333333333333333333333333333333333 \
      0x4444444444444444444444444444444444444444444444444444444444444444 \
      --rpc-url http://127.0.0.1:8545 \
      --private-key <ADMIN_PRIVATE_KEY>
    ```

8.  **Grant `REGISTRAR_ROLE` to another admin (using `cast` after deployment)**
    *   Replace `<CONTRACT_ADDR>` with the address printed in step 6.
    *   Replace the private key in the command below with the private key of the *deployer* (who holds `DEFAULT_ADMIN_ROLE`).
    *   Replace `<NEW_ADMIN_ADDRESS>` with the address of the admin you want to add.
    ```bash
    cast send <CONTRACT_ADDR> "grantRegistrarRole(address)" <NEW_ADMIN_ADDRESS> \
      --rpc-url http://127.0.0.1:8545 \
      --private-key <ADMIN_PRIVATE_KEY>
    ```

9.  **Revoke `REGISTRAR_ROLE` from an admin (using `cast` after deployment)**
    *   Replace `<CONTRACT_ADDR>` with the address printed in step 6.
    *   Replace the private key in the command below with the private key of the *deployer* (who holds `DEFAULT_ADMIN_ROLE`).
    *   Replace `<ADMIN_TO_REVOKE>` with the address of the admin you want to remove.
    ```bash
    cast send <CONTRACT_ADDR> "revokeRegistrarRole(address)" <ADMIN_TO_REVOKE> \
      --rpc-url http://127.0.0.1:8545 \
      --private-key <ADMIN_PRIVATE_KEY>
    ```

10. **Retract a paper (replace `<CONTRACT_ADDR>` with the address printed in step 6)**
    *   Replace `<DOC_ID_TO_RETRACT>` with the `docId` of the paper you want to retract.
    *   Replace the private key in the command below with the private key of an *admin* holding `REGISTRAR_ROLE`.
    ```bash
    cast send <CONTRACT_ADDR> "retractPaper(uint256)" <DOC_ID_TO_RETRACT> \
      --rpc-url http://127.0.0.1:8545 \
      --private-key <ADMIN_PRIVATE_KEY>
    ```

11. **Test lookup**
    ```bash
    # Get docId by DOI (for the registration example)
    cast call <CONTRACT_ADDR> "getDocIdByDoi(bytes32)" 0x1111111111111111111111111111111111111111111111111111111111111111
    # Get paper details by docId (assuming the registration was ID 1), including retraction status
    cast call <CONTRACT_ADDR> "getPaper(uint256)" 1
    # Get docId by TAD (for the registration example)
    cast call <CONTRACT_ADDR> "getDocIdByTAD(bytes32)" 0x2222222222222222222222222222222222222222222222222222222222222222
    ```
