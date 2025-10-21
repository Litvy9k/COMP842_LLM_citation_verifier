# Citation Registry Backend (FastAPI + Web3)

> Backend to **register**, **retract** (one‑way), and **edit** papers on an EVM-compatible contract using domain‑separated Keccak Merkle hashing and role‑gated admin (EIP‑191 signature recovery).

## Repository layout

```
├─ backend_domainsep_nopartial_date_role/
│  ├─ README_retract_edit_EN.md
│  ├─ requirements.txt
│  ├─ run_backend.py
│  ├─ __pycache__/
│  ├─ app/
│  ├─ citationregistry-hardhat-kit/
```

Key paths:
- **backend_domainsep_nopartial_date_role/app/main.py** — FastAPI app and on‑chain integration
- **backend_domainsep_nopartial_date_role/app/models.py** — Pydantic schemas (Auth, Metadata, DTOs)
- **backend_domainsep_nopartial_date_role/app/canonical.py** & **merkle_sha256.py** — legacy helpers
- **backend_domainsep_nopartial_date_role/citationregistry-hardhat-kit/deployments/localhost.json** — local deployed address
- **backend_domainsep_nopartial_date_role/requirements.txt** — Python dependencies
- **backend_domainsep_nopartial_date_role/run_backend.py** — convenience runner

## Features

- **Add** a paper (`/register`)
- **Retract** a paper (`/retraction/set`) — marks a paper as retracted on‑chain (documentation covers retraction only; reversing a retraction is **not** documented/supported here)
- **Check retraction status** (`/retraction/status`)
- **Edit** a paper (`/papers/edit`) — create a new version with updated metadata/full text
- **Auto‑detect ABI**: finds a 4×`bytes32` “register-like” function by signature or common names (`register`, `registerPaper`, `addDoc`, …)
- **Role check**: verifies `hasRole(keccak256("REGISTRAR_ROLE"), recovered)` from an **EIP‑191** signature
- **Deterministic hashing** for DOI/TAD/metadata/full text using **Keccak‑256 Merkle** with domain separation

## Prerequisites

- Python **3.11+**
- A running JSON‑RPC node (Anvil/Hardhat/Ganache). Default: `http://127.0.0.1:8545`
- A deployed **CitationRegistry** contract exposing:
  - `hasRole(bytes32,address)`
  - lookup by DOI/TAD (`getDocIdByDoi(bytes32)`, `getDocIdByTAD(bytes32)`)
  - getters such as `getPaper(uint256)`
  - a 4×`bytes32` register‑like method (e.g. `register(bytes32,bytes32,bytes32,bytes32)`)

## Installation

```bash
cd backend_domainsep_nopartial_date_role
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration (env vars)

| Name | Default | Purpose |
| --- | --- | --- |
| `ETH_RPC_URL` | `http://127.0.0.1:8545` | RPC endpoint |
| `CONTRACT_ADDRESS` | — | Deployed `CitationRegistry` address. If unset, `run_backend.py` will read `citationregistry-hardhat-kit/deployments/localhost.json` |
| `CONTRACT_ABI_PATH` | *(auto)* | Path to Hardhat artifact JSON `.../artifacts/contracts/CitationRegistry.sol/CitationRegistry.json` |
| `PRIVATE_KEY` | — | EOA used to send transactions (required for state‑changing endpoints) |
| `GAS_PRICE_GWEI` | `1` | Uses **legacy** gas mode with fixed `gasPrice` |

> The app forces legacy gas (sets `gasPrice` and strips EIP‑1559 fields).

## Run

Quick start (auto‑reads local deployment address):

```bash
python run_backend.py
# → serves at http://127.0.0.1:8000
```

Or with Uvicorn manually:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/docs** for Swagger UI.

## Data model

**Metadata**:
```json
{
  "doi": "10.1000/xyz456",           // optional
  "title": "Your Title",
  "authors": ["Alice","Bob"],        // list of strings
  "date": "2024-01-05"               // ISO YYYY-MM-DD
}
```

**Auth envelope (EIP‑191)** for admin actions:
```json
{
  "address": "0xYourEOA",
  "message": "I am registrar",       // arbitrary message you signed
  "signature": "0x…"                 // 65‑byte ECDSA sig
}
```

## Hashing summary

- `hashedDoi = keccak(0x00 || lower(NFKC(doi)))`
- `authors_root = reduce(keccak(0x00 || NFKC(author_i)))`
- `hashedTAD = keccak(0x01 || keccak(0x01 || keccak(0x00||title) || authors_root) || keccak(0x00||date))`
- `metadata_root = keccak(0x01 || keccak(0x01 || keccak(0x00||title) || authors_root) || keccak(0x01 || keccak(0x00||lower(doi)) || keccak(0x00||date)))`
- `fulltext_root`:
  - UTF‑8 bytes of full text → chunk by `chunk_size` (default 4096)
  - leaf hash each chunk with `0x00` prefix, then pairwise reduce

## API

### `GET /` — health
Returns chain info and config hints:
```json
{
  "ok": true,
  "chain_id": 31337,
  "contract": "0x…",
  "has_private_key": true,
  "gas_mode": "legacy gasPrice 1 gwei"
}
```

### `POST /register` — add paper (admin)
Request:
```json
{
  "auth": { "address":"0x…", "message":"I am registrar", "signature":"0x…" },
  "metadata": {
    "doi": "10.1000/xyz456",
    "title": "My Paper",
    "authors": ["Alice","Bob"],
    "date": "2024-01-05"
  },
  "full_text": "optional…",
  "chunk_size": 4096
}
```
Response includes tx hash and computed roots/hashes.

### `POST /retraction/status` — public
Query by `doc_id` **or** full metadata:
```json
{ "doc_id": 123 }
```
→ `{ "doc_id": 123, "is_retracted": true }`

### `POST /retraction/set` — admin (one‑way retraction)
Marks a paper as **retracted** on‑chain. This documentation covers marking as retracted only.
```json
{
  "auth": { "address":"0x…", "message":"I am registrar", "signature":"0x…" },
  "doc_id": 123,
  "is_retracted": true
}
```

### `POST /papers/edit` — edit (admin)
Create a new version of an existing paper with updated metadata and/or full text:
```json
{
  "auth": { "address":"0x…", "message":"I am registrar", "signature":"0x…" },
  "old_doc_id": 123,
  "new_metadata": {
    "doi": "10.1000/xyz456",
    "title": "New Title",
    "authors": ["Alice","Bob","Carol"],
    "date": "2024-01-05"
  },
  "new_full_text": "optional",
  "chunk_size": 4096
}
```

## Troubleshooting

- **`register tx failed: The function 'register' was not found in this contract's abi.`** — set the correct ABI via `CONTRACT_ABI_PATH` or ensure your contract exposes a 4×`bytes32` register‑like method. The backend will auto‑discover common names.
- **`ABI not found at …`** — compile the contract with Hardhat and point `CONTRACT_ABI_PATH` to the artifact JSON.
- **`CONTRACT_ADDRESS not set and deployments/localhost.json missing 'CitationRegistry'`** — set `CONTRACT_ADDRESS` or update `backend_domainsep_nopartial_date_role/citationregistry-hardhat-kit/deployments/localhost.json`.
- **`no PRIVATE_KEY (dry-run cannot send tx)`** — export a funded key.
- **`metadata.date must be YYYY-MM-DD`** — supply an ISO date string.
- **`paper not found / paper not found by DOI`** — the on‑chain index has no such doc; double‑check metadata or register first.
- **`attempt to reverse a retraction`** — reversing/undoing a retraction is **not** documented/supported in this build.

## License
MIT (placeholder — update as needed).
