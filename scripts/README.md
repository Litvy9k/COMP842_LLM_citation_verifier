# Scripts Directory

This directory contains startup scripts for the LLM Citation Verifier.

## Files

- `start_services.py` - Main startup script that:
  - Manages private keys (uses Hardhat test account as admin)
  - Sets up Hardhat blockchain environment
  - Starts Hardhat local Ethereum node
  - Deploys CitationRegistry smart contract
  - Starts backend API server
  - Loads papers from rag_query/paper.json

- `startup_requirements.txt` - Python dependencies for the startup script (eth-account, requests)

- `backend_requirements.txt` - Python dependencies for the backend API service

## Installation

### 1. Install Dependencies

**Python Dependencies:**
```bash
pip install -r scripts/startup_requirements.txt
pip install -r scripts/backend_requirements.txt
```

**Node.js and npm (Blockchain Development):**
```bash
# Visit https://nodejs.org/ to download and install Node.js
# npm is included with Node.js installation

# Navigate to blockchain directory and install Hardhat dependencies
cd blockchain
npm install
cd ..
```

## Usage

### Run the Startup Script
```bash
# From the project root directory:
python3 scripts/start_services.py

# OR from the scripts directory:
cd scripts
python3 start_services.py
```

## Script Operations

The script performs the following operations:

1. **Dependency Check**: Ensures Python3, Node.js, and npm are installed
2. **Private Key Management**:
   - Uses Hardhat test account as admin account
   - Saves credentials to `.private_key.json` in project root
3. **Blockchain Setup**:
   - Initializes Hardhat project in `blockchain/` directory
   - Installs OpenZeppelin contracts via npm
   - Starts Hardhat node on http://127.0.0.1:8545
   - Deploys CitationRegistry contract with admin role
4. **Backend Service**:
   - Starts FastAPI backend on http://127.0.0.1:8000
   - Loads all papers from rag_query/paper.json into the contract

## Configuration Files Created

- `.private_key.json` - Admin account private key and address
- `.env.local` - Environment variables including CONTRACT_ADDRESS

## Service URLs

After startup, the following services are available:

- **Hardhat Node (Ethereum)**: http://127.0.0.1:8545
- **Backend API**: http://127.0.0.1:8000
- **Backend Health Check**: http://127.0.0.1:8000/

## Testing

After startup, you can test the services:

```bash
# Test backend health
curl http://127.0.0.1:8000/

# Test contract interaction using ethers.js or web3.js
# The contract ABI is available in blockchain/artifacts/contracts/CitationRegistry.sol/CitationRegistry.json
```

## Stopping Services

Press `Ctrl+C` to stop all services gracefully.
