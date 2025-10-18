from datetime import date
import os, json
from functools import lru_cache
from typing import Optional, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException
from web3 import Web3
from eth_utils import keccak, to_checksum_address
from eth_account.messages import encode_defunct
from eth_account import Account
from eth_account import Account as LocalAccount

from app.models import RegisterRequest, CompleteValidateRequest, ValidateResponse
from app.canonical import canonical_json_bytes, hash_hashedDoi, hash_hashedTAD
from app.merkle_sha256 import build_merkle

# ---------------- Contract ABI (minimal) ----------------
MIN_ABI = [
    {"inputs":[{"internalType":"bytes32","name":"role","type":"bytes32"},{"internalType":"address","name":"account","type":"address"}],
     "name":"hasRole","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"hashedDoi","type":"bytes32"},{"internalType":"bytes32","name":"hashedTAD","type":"bytes32"},
               {"internalType":"bytes32","name":"metadataRoot","type":"bytes32"},{"internalType":"bytes32","name":"fullTextRoot","type":"bytes32"}],
     "name":"registerPaper","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"hashedDoi","type":"bytes32"}],"name":"getDocIdByDoi","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"hashedTAD","type":"bytes32"}],"name":"getDocIdByTAD","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"docId","type":"uint256"}],"name":"getPaper","outputs":[{"internalType":"bytes32","name":"metadataRoot","type":"bytes32"},{"internalType":"bytes32","name":"fullTextRoot","type":"bytes32"},{"internalType":"bool","name":"isRetractedStatus","type":"bool"}],"stateMutability":"view","type":"function"}
]

# ---------------- Web3 helpers ----------------
def _auto_contract_address() -> str:
    """ENV 优先；否则读取 backend/citationregistry-hardhat-kit/deployments/localhost.json"""
    addr = os.getenv("CONTRACT_ADDRESS")
    if addr:
        return addr
    maybe = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "citationregistry-hardhat-kit", "deployments", "localhost.json"))
    if os.path.exists(maybe):
        with open(maybe, "r", encoding="utf-8") as fh:
            j = json.load(fh)
        if j.get("CitationRegistry"):
            return j["CitationRegistry"]
    raise RuntimeError("CONTRACT_ADDRESS not set and deployments/localhost.json not found")

@lru_cache(maxsize=1)
def get_web3() -> Web3:
    rpc = os.getenv("ETH_RPC_URL", "http://127.0.0.1:8545")
    return Web3(Web3.HTTPProvider(rpc))

@lru_cache(maxsize=1)
def get_contract():
    w3 = get_web3()
    addr = _auto_contract_address()
    # 兼容 web3 v6 的校验和方法
    caddr = Web3.to_checksum_address(addr) if hasattr(Web3, "to_checksum_address") else w3.to_checksum_address(addr)
    return w3.eth.contract(address=caddr, abi=MIN_ABI)

@lru_cache(maxsize=1)
def get_registrar_role_id() -> bytes:
    return keccak(text="REGISTRAR_ROLE")

def _get_sender_acct() -> Optional[LocalAccount]:
    """从 ENV 读取 ETH_PRIVATE_KEY，返回本地签名账户；没有就返回 None（保持 dry-run）"""
    pk = os.getenv("ETH_PRIVATE_KEY")
    if not pk:
        return None
    try:
        return Account.from_key(pk)
    except Exception:
        return None

# ---------------- Auth / Role ----------------
def recover_eip191_address(message: str, signature: str) -> str:
    """同时兼容对字符串签名和对 0x 十六进制 bytes 签名"""
    try:
        if isinstance(message, str) and message.startswith("0x"):
            # 若客户端是对 bytes(hex) 做的 signMessage
            msg = encode_defunct(hexstr=message)
        else:
            msg = encode_defunct(text=message)
    except Exception:
        # 兜底当作普通字符串
        msg = encode_defunct(text=message)
    addr = Account.recover_message(msg, signature=signature)
    return to_checksum_address(addr)

def assert_registrar_role(auth) -> str:
    if auth is None:
        raise HTTPException(status_code=401, detail="auth required")
    if not getattr(auth, "signature", None) or not getattr(auth, "message", None):
        raise HTTPException(status_code=400, detail="auth.signature and auth.message required")

    try:
        recovered = recover_eip191_address(auth.message, auth.signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"signature recover failed: {e}")

    c = get_contract()
    role = get_registrar_role_id()

    # 允许“请求签名者”或“后端发交易者”任意一方拥有角色
    try:
        ok_recovered = c.functions.hasRole(role, recovered).call()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"hasRole(recovered) failed: {e}")

    ok_backend = False
    acct = _get_sender_acct()
    if acct:
        try:
            ok_backend = c.functions.hasRole(role, acct.address).call()
        except Exception:
            ok_backend = False

    if not (ok_recovered or ok_backend):
        raise HTTPException(status_code=403, detail="permission denied: REGISTRAR_ROLE required")
    return recovered

# ---------------- Merkle inputs ----------------
def make_metadata_leaves(md: dict) -> list[bytes]:
    leaves = []
    for k in sorted(md.keys()):
        payload = {k: md[k]}
        leaves.append(canonical_json_bytes(payload))
    return leaves

def make_fulltext_leaves(full_text: str | None, chunk_size: int) -> list[bytes]:
    if not full_text:
        return []
    data = full_text.encode("utf-8")
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

# ---------------- TX: registerPaper ----------------
def _send_register_tx(hashed_doi: bytes, hashed_tad: bytes,
                      metadata_root: bytes, fulltext_root: bytes):
    """
    有 ETH_PRIVATE_KEY 时：真实发交易；否则返回 (None, None) 表示 dry-run
    """
    w3 = get_web3()
    c = get_contract()
    acct = _get_sender_acct()
    if not acct:
        return None, None  # no private key => stay dry-run

    # 发送前确保“后端发交易账号”也有角色，避免链上 revert
    role = get_registrar_role_id()
    if not c.functions.hasRole(role, acct.address).call():
        raise HTTPException(status_code=403, detail=f"backend sender {acct.address} lacks REGISTRAR_ROLE")

    fn = c.functions.registerPaper(hashed_doi, hashed_tad, metadata_root, fulltext_root)
    nonce = w3.eth.get_transaction_count(acct.address)

    # 尽量估算 gas；失败就用兜底
    try:
        gas_est = fn.estimate_gas({'from': acct.address})
    except Exception:
        gas_est = 500_000

    tx = fn.build_transaction({
        'from': acct.address,
        'nonce': nonce,
        'gas': int(gas_est * 1.2),
        'maxFeePerGas': w3.to_wei(2, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(1, 'gwei'),
        'chainId': w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=acct.key)
    raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
    tx_hash = w3.eth.send_raw_transaction(raw)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # 上链后给出 docId，方便后续验证
    doc_id = c.functions.getDocIdByDoi(hashed_doi).call()
    if doc_id == 0:
        doc_id = c.functions.getDocIdByTAD(hashed_tad).call()
    return tx_hash.hex(), int(doc_id)

# ---------------- FastAPI ----------------
app = FastAPI(title="Citation Registry Backend")

@app.get("/health")
def health():
    addr = _auto_contract_address()
    acct = _get_sender_acct()
    return {
        "ok": True,
        "rpc": os.getenv("ETH_RPC_URL", "http://127.0.0.1:8545"),
        "contract": addr,
        "sender": acct.address if acct else None
    }

@app.post("/register", response_model=ValidateResponse)
def register(req: RegisterRequest):
    # 1) 认证（签名者 or 后端 sender 拥有 REGISTRAR_ROLE）
    recovered_admin = assert_registrar_role(req.auth)

    # 2) 基本校验
    md = dict(req.metadata or {})
    doi = md.get("doi")
    title = md.get("title")
    authors = md.get("authors") or []
    date_str = md.get("date")
    if not doi or not title or not isinstance(authors, list) or date_str is None:
        raise HTTPException(status_code=400, detail="metadata must include doi, title, authors(list), date(YYYY-MM-DD)")

    # 3) 计算 hashedDoi / hashedTAD / roots
    hashed_doi = hash_hashedDoi(doi)  # bytes32
    norm_date = date.fromisoformat(date_str).isoformat()
    hashed_tad = hash_hashedTAD(title, authors, norm_date)  # bytes32

    meta_leaves = make_metadata_leaves(md)
    metadata_root, _ = build_merkle(meta_leaves)  # bytes32

    full_leaves = make_fulltext_leaves(req.full_text, req.chunk_size)
    fulltext_root, _ = build_merkle(full_leaves) if full_leaves else (b"\x00" * 32, [])

    # 4) 有私钥就真实上链；没有就保持 dry-run
    tx_hash, doc_id = _send_register_tx(hashed_doi, hashed_tad, metadata_root, fulltext_root)

    if tx_hash:
        on_md, on_ft, _ = get_contract().functions.getPaper(doc_id).call()
        ok = (on_md == metadata_root) and (on_ft == fulltext_root)
        return ValidateResponse(
            ok=bool(ok),
            message="on-chain registerPaper OK" if ok else "on-chain roots mismatch (still registered)",
            tx_hash=tx_hash,
            doc_id=doc_id,
            hashed_doi="0x" + hashed_doi.hex(),
            hashed_tad="0x" + hashed_tad.hex(),
            metadata_root="0x" + metadata_root.hex(),
            fulltext_root="0x" + fulltext_root.hex(),
            onchain_metadata_root=Web3.to_hex(on_md),
            onchain_fulltext_root=Web3.to_hex(on_ft),
            details={"checked_fields": ["doi","title","authors","date"],
                     "recovered_admin": recovered_admin,
                     "sender": _get_sender_acct().address}
        )

    # Dry-run fallback（与旧版一致）
    return ValidateResponse(
        ok=True,
        message="computed (no PRIVATE_KEY: dry-run)",
        hashed_doi="0x" + hashed_doi.hex(),
        hashed_tad="0x" + hashed_tad.hex(),
        metadata_root="0x" + metadata_root.hex(),
        fulltext_root="0x" + fulltext_root.hex(),
        details={"checked_fields": ["doi","title","authors","date"], "recovered_admin": recovered_admin}
    )

@app.post("/validate/complete-metadata", response_model=ValidateResponse)
def validate_complete(req: CompleteValidateRequest):
    # 1) 计算同样的哈希/根
    md = dict(req.metadata or {})
    doi = md.get("doi")
    title = md.get("title")
    authors = md.get("authors") or []
    date_str = md.get("date")
    if not doi or not title or not isinstance(authors, list) or date_str is None:
        raise HTTPException(status_code=400, detail="metadata must include doi, title, authors(list), date(YYYY-MM-DD)")

    hashed_doi = hash_hashedDoi(doi)
    norm_date = date.fromisoformat(date_str).isoformat()
    hashed_tad = hash_hashedTAD(title, authors, norm_date)

    meta_leaves = make_metadata_leaves(md)
    metadata_root, _ = build_merkle(meta_leaves)
    full_leaves = make_fulltext_leaves(req.full_text, req.chunk_size)
    fulltext_root, _ = build_merkle(full_leaves) if full_leaves else (b"\x00"*32, [])

    # 2) 在链上查找 docId
    c = get_contract()
    try:
        doc_id = c.functions.getDocIdByDoi(hashed_doi).call()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"getDocIdByDoi failed: {e}")
    if doc_id == 0:
        try:
            doc_id = c.functions.getDocIdByTAD(hashed_tad).call()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"getDocIdByTAD failed: {e}")
        if doc_id == 0:
            raise HTTPException(status_code=404, detail="paper not found by DOI or TAD")

    # 3) 读回 roots 对比
    try:
        on_metadata_root, on_fulltext_root, _isRetracted = c.functions.getPaper(doc_id).call()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"getPaper failed: {e}")

    ok = (on_metadata_root == metadata_root) and (on_fulltext_root == fulltext_root)

    return ValidateResponse(
        ok=bool(ok),
        message="match" if ok else "mismatch",
        doc_id=doc_id,
        hashed_doi="0x" + hashed_doi.hex(),
        hashed_tad="0x" + hashed_tad.hex(),
        metadata_root="0x" + metadata_root.hex(),
        fulltext_root="0x" + fulltext_root.hex(),
        onchain_metadata_root=Web3.to_hex(on_metadata_root),
        onchain_fulltext_root=Web3.to_hex(on_fulltext_root),
        details={"checked_fields": ["doi","title","authors","date"]}
    )
