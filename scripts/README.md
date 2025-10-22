# Scripts Directory

This directory contains startup scripts for the LLM Citation Verifier web application, blockchain components, and backend services.

## Files

- `start_services.py` - Main startup script that:
  - Manages private keys (uses Hardhat test account as admin)
  - Sets up Hardhat blockchain environment
  - Starts Hardhat local Ethereum node
  - Deploys CitationRegistry smart contract
  - Starts backend API server
  - Loads papers from rag_query/paper.json
  - Starts frontend development server automatically

- `startup_requirements.txt` - Python dependencies for the startup script (eth-account, requests)

- `backend_requirements.txt` - Python dependencies for the backend API service

## Installation

### Install Dependencies

**Node.js and npm:**
Visit https://nodejs.org/ to download and install Node.js (npm is included).

**Web Application Dependencies:**
```bash
# In the project root directory:
npm install
```

**Blockchain Dependencies:**
```bash
# In the blockchain directory:
npm install
cd ..
```

**Python Dependencies:**

```bash
# In the scripts directory
pip install -r startup_requirements.txt
pip install -r backend_requirements.txt
```

## Usage

### Run the Startup Script
```bash
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
5. **Frontend Service**:
   - Starts React development server on http://127.0.0.1:3000

## Configuration Files Created

- `.private_key.json` - Admin account private key and address
- `.env.local` - Environment variables including CONTRACT_ADDRESS

### MetaMask Setup

**Import Test Account**
- In MetaMask, click on your account icon and select "Import account"
- Paste this private key: `0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d`
- This account (0x70997970C51812dc3A010C7d01b50e0d17dc79C8) is granted REGISTRAR_ROLE during deployment

**Connect to Web Interface**
- Open http://127.0.0.1:3000 in your browser
- The app should connect automatically and detect the local test network
- If the network is not added automatically, add it manually in MetaMask:
  - Network Name: Hardhat Local
  - New RPC URL: http://127.0.0.1:8545
  - Chain ID: 1337
  - Currency Symbol: ETH

**Service URLs**
After startup, these services are available:
- Hardhat node (Ethereum): http://127.0.0.1:8545
- Backend API: http://127.0.0.1:8000
- Backend health: http://127.0.0.1:8000/
- Web interface (React): http://127.0.0.1:3000

Press `Ctrl+C` to stop all services gracefully.
