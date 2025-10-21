# Scripts Directory

This directory contains startup scripts for the LLM Citation Verifier.

## Files

- `start_services.py` - Main startup script that:
  - Manages private keys (uses Anvil test account as admin)
  - Sets up Foundry blockchain environment
  - Starts Anvil local Ethereum node
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

**Foundry (Blockchain Development):**
```bash
# Visit https://getfoundry.sh/ and follow installation instructions
```

## Usage

### Run the Startup Script
```bash
cd scripts
python3 start_services.py
```

## Script Operations

The script performs the following operations:

1. **Dependency Check**: Ensures Python3 and Foundry are installed
2. **Private Key Management**:
   - Uses Anvil test account as admin account
   - Saves credentials to `.private_key.json` in project root
3. **Blockchain Setup**:
   - Initializes Foundry project in `blockchain/` directory
   - Installs OpenZeppelin contracts
   - Starts Anvil on http://127.0.0.1:8545
   - Deploys CitationRegistry contract with admin role
4. **Backend Service**:
   - Starts FastAPI backend on http://127.0.0.1:8000
   - Loads all papers from rag_query/paper.json into the contract

## Configuration Files Created

- `.private_key.json` - Admin account private key and address
- `.env.local` - Environment variables including CONTRACT_ADDRESS

## Service URLs

After startup, the following services are available:

- **Anvil (Ethereum Node)**: http://127.0.0.1:8545
- **Backend API**: http://127.0.0.1:8000
- **Backend Health Check**: http://127.0.0.1:8000/health

## Testing

After startup, you can test the services:

```bash
# Test backend health
curl http://127.0.0.1:8000/health

# Test contract interaction (retract a paper)
cast send --rpc-url http://127.0.0.1:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 <CONTRACT_ADDRESS> "retractPaper(uint256)" <DOC_ID>
```

## Stopping Services

Press `Ctrl+C` to stop all services gracefully.
