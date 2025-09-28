### The smart contract currently expects the following from the Merkle module (interface can be adjusted if needed):

Four `bytes32` values, in this order:
1. `hashedExternalId` → `SHA256(canonicaljson("doi:10.xxxx/..."))`
2. `hashedTAH` → `SHA256(canonicaljson({"title": "...", "authors": [...], "year": 2023}))`
3. `metadataRoot` → Merkle root of full metadata
4. `fullTextRoot` → Merkle root of text chunks

---

### For API Integration

#### 1. **Register a paper**
```solidity
function registerPaper(
    bytes32 hashedExternalId,
    bytes32 hashedTAH,
    bytes32 metadataRoot,
    bytes32 fullTextRoot
) external returns (uint256 docId)
```
- **Only callable by the contract owner** (i.e., the account that deployed it)
- Returns the assigned `docId` (e.g., `1`, `2`, ...)

#### 2. **Look up by external ID (DOI/arXiv)**
```solidity
function getDocIdByExternalId(bytes32 hashedExternalId) external view returns (uint256)
```
- Returns `0` if not found

#### 3. **Look up by Title+Author+Year**
```solidity
function getDocIdByTAH(bytes32 hashedTAH) external view returns (uint256)
```
- Returns `0` if not found

#### 4. **Fetch paper roots**
```solidity
function getPaper(uint256 docId) external view returns (bytes32 metadataRoot, bytes32 fullTextRoot)
```
- Reverts if `docId` is `0` or unregistered

---

### How to Test the Smart Contract

```bash
# 1. Install Foundry (once)
curl -L https://foundry.paradigm.xyz | bash
source ~/.bashrc  # or ~/.zshrc
foundryup

# 2. Initialize Foundry project in the blockchain folder
forge init

# 3. Ensure your contract is at: blockchain/src/CitationRegistry.sol

# 4. Install OpenZeppelin dependencies in the blockchain folder 
forge install OpenZeppelin/openzeppelin-contracts

# 5. Start local Ethereum node
anvil

# 6. Deploy the contract
forge create src/CitationRegistry.sol:CitationRegistry \
  --rpc-url http://127.0.0.1:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --broadcast

# 7. Register a paper (replace <CONTRACT_ADDR> with the address printed in step 6)
cast send <CONTRACT_ADDR> "registerPaper(bytes32,bytes32,bytes32,bytes32)" \
  0x1111111111111111111111111111111111111111111111111111111111111111 \
  0x2222222222222222222222222222222222222222222222222222222222222222 \
  0x3333333333333333333333333333333333333333333333333333333333333333 \
  0x4444444444444444444444444444444444444444444444444444444444444444 \
  --rpc-url http://127.0.0.1:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# 8. Test lookup
cast call <CONTRACT_ADDR> "getDocIdByExternalId(bytes32)" 0x1111111111111111111111111111111111111111111111111111111111111111
cast call <CONTRACT_ADDR> "getPaper(uint256)" 1
```

> The four test hashes in step 7 correspond to:  
> 1. `hashedExternalId`  
> 2. `hashedTAH`  
> 3. `metadataRoot`  
> 4. `fullTextRoot`

---