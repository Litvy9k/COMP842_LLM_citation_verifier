# app/main.py
import os
import json
import unicodedata
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

from app.models import RegisterRequest, CompleteValidateRequest, ValidateResponse
from app.canonical import canonical_json_bytes, hash_hashedDoi, hash_hashedTAD
from app.merkle_sha256 import build_merkle

# ========== 兼容导入你现有的 app.models，如果缺少类名就用内置后备 ==========
AuthEnvelope: Any = None
Metadata: Any = None
RegisterRequest: Any = None
RetractionStatusRequest: Any = None
RetractionSetRequest: Any = None
EditRequest: Any = None

try:
    import app.models as _models
    print("### models.py loaded from:", _models.__file__)
    AuthEnvelope = getattr(_models, "AuthEnvelope", None)
    Metadata = getattr(_models, "Metadata", None)
    RegisterRequest = getattr(_models, "RegisterRequest", None)
    RetractionStatusRequest = getattr(_models, "RetractionStatusRequest", None)
    RetractionSetRequest = getattr(_models, "RetractionSetRequest", None)
    EditRequest = getattr(_models, "EditRequest", None)
except Exception as e:
    print("### app.models import failed, will use fallback models:", e)

# ---------- 后备模型（当上面任意一个为 None 时启用） ----------
class _AuthEnvelopeFallback(BaseModel):
    message: str
    signature: str
    sig_type: Optional[str] = "eip191"

class _MetadataFallback(BaseModel):
    doi: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    date: Optional[str] = None  # YYYY-MM-DD

class _RegisterRequestFallback(BaseModel):
    auth: _AuthEnvelopeFallback
    metadata: _MetadataFallback
    full_text: Optional[str] = None
    chunk_size: Optional[int] = 4096

class _RetractionStatusRequestFallback(BaseModel):
    doc_id: Optional[int] = None
    metadata: Optional[_MetadataFallback] = None

class _RetractionSetRequestFallback(BaseModel):
    auth: _AuthEnvelopeFallback
    doc_id: Optional[int] = None
    metadata: Optional[_MetadataFallback] = None
    retract: bool

class _EditRequestFallback(BaseModel):
    auth: _AuthEnvelopeFallback
    old_doc_id: Optional[int] = None
    old_metadata: Optional[_MetadataFallback] = None
    new_metadata: _MetadataFallback
    new_full_text: Optional[str] = None
    chunk_size: Optional[int] = 4096

AuthEnvelope = AuthEnvelope or _AuthEnvelopeFallback
Metadata = Metadata or _MetadataFallback
RegisterRequest = RegisterRequest or _RegisterRequestFallback
RetractionStatusRequest = RetractionStatusRequest or _RetractionStatusRequestFallback
RetractionSetRequest = RetractionSetRequest or _RetractionSetRequestFallback
EditRequest = EditRequest or _EditRequestFallback

# ============================= FastAPI =============================
app = FastAPI(title="Citation Backend (legacy gas + dynamic ABI)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================= Web3 / contract helpers ===================
ETH_RPC_URL = os.getenv("ETH_RPC_URL", "http://127.0.0.1:8545")
CONTRACT_ADDRESS_ENV = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
GAS_PRICE_GWEI = int(os.getenv("GAS_PRICE_GWEI", "1"))

# 允许通过 CONTRACT_ABI_PATH 自定义 ABI 路径；否则走默认 hardhat artifacts
CONTRACT_ABI_PATH = os.getenv("CONTRACT_ABI_PATH")
HARDHAT_ROOT = Path(__file__).resolve().parents[2] / "citationregistry-hardhat-kit"
ABI_PATH_DEFAULT = HARDHAT_ROOT / "artifacts" / "contracts" / "CitationRegistry.sol" / "CitationRegistry.json"
DEPLOYMENTS_JSON = HARDHAT_ROOT / "deployments" / "localhost.json"

w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))

def _load_contract_address() -> str:
    if CONTRACT_ADDRESS_ENV:
        return Web3.to_checksum_address(CONTRACT_ADDRESS_ENV)
    if DEPLOYMENTS_JSON.exists():
        obj = json.loads(DEPLOYMENTS_JSON.read_text(encoding="utf-8"))
        addr = obj.get("CitationRegistry")
        if addr:
            return Web3.to_checksum_address(addr)
    raise RuntimeError("CONTRACT_ADDRESS not set and deployments/localhost.json missing 'CitationRegistry'")

def _load_contract():
    addr = _load_contract_address()
    abi_path = Path(CONTRACT_ABI_PATH) if CONTRACT_ABI_PATH else ABI_PATH_DEFAULT
    if not abi_path.exists():
        raise RuntimeError(f"ABI not found at {abi_path} — set CONTRACT_ABI_PATH env or adjust path")
    abi = json.loads(abi_path.read_text(encoding="utf-8"))["abi"]
    c = w3.eth.contract(address=addr, abi=abi)
    c.abi = abi  # 方便后面函数探测使用
    return c

def _get_account():
    return Account.from_key(PRIVATE_KEY) if PRIVATE_KEY else None

def _force_legacy_gas(tx: dict) -> dict:
    """移除 EIP-1559 字段，改用 legacy gasPrice。"""
    tx.pop("maxFeePerGas", None)
    tx.pop("maxPriorityFeePerGas", None)
    tx["gasPrice"] = w3.to_wei(GAS_PRICE_GWEI, "gwei")
    return tx

def _send_tx(fn) -> str:
    """build_transaction + legacy gas + sign + send。返回 tx hash(hex)。"""
    acct = _get_account()
    if not acct:
        raise RuntimeError("no PRIVATE_KEY (dry-run cannot send tx)")
    tx = fn.build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": w3.eth.chain_id,
    })
    tx = _force_legacy_gas(tx)
    signed = acct.sign_transaction(tx)
    raw = getattr(signed, "rawTransaction", getattr(signed, "raw_transaction", None))
    if raw is None:
        raise RuntimeError("cannot find rawTransaction on signed tx")
    tx_hash = w3.eth.send_raw_transaction(raw)
    return tx_hash.hex()

# =================== Crypto / roles / signature ====================
def _keccak_text(t: str) -> bytes:
    return Web3.keccak(text=t)

REGISTRAR_ROLE = _keccak_text("REGISTRAR_ROLE")

def _to_dict(model_obj) -> dict:
    """兼容 pydantic v1/v2，把模型转成 dict。"""
    if model_obj is None:
        return {}
    for attr in ("dict", "model_dump"):
        if hasattr(model_obj, attr):
            try:
                return getattr(model_obj, attr)()
            except Exception:
                pass
    try:
        return dict(model_obj)
    except Exception:
        return {}

def _recover_eip191(auth: AuthEnvelope) -> str:
    if not auth or not getattr(auth, "message", None) or not getattr(auth, "signature", None):
        raise HTTPException(status_code=400, detail="auth.message and auth.signature required")
    sig_type = (getattr(auth, "sig_type", None) or "eip191").lower()
    if sig_type != "eip191":
        raise HTTPException(status_code=400, detail=f"unsupported sig_type: {sig_type}")
    msg = encode_defunct(text=auth.message)
    try:
        addr = Account.recover_message(msg, signature=auth.signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid signature: {e}")
    return Web3.to_checksum_address(addr)

def _assert_registrar_role(auth: AuthEnvelope) -> str:
    recovered = _recover_eip191(auth)
    c = _load_contract()
    # 显式使用函数签名，避免 ABI 重载干扰
    try:
        ok = c.get_function_by_signature("hasRole(bytes32,address)")(REGISTRAR_ROLE, recovered).call()
    except Exception:
        ok = c.functions.hasRole(REGISTRAR_ROLE, recovered).call()
    if not ok:
        raise HTTPException(status_code=403, detail="permission denied: REGISTRAR_ROLE required")
    return recovered

# ================= Canonicalization & hashing (domain sep) =========
def _canon_str(s: str, lower: bool = False) -> bytes:
    if s is None:
        s = ""
    s = unicodedata.normalize("NFKC", str(s).strip())
    if lower:
        s = s.lower()
    return s.encode("utf-8")

def _h00(b: bytes) -> bytes:
    return Web3.keccak(b"\x00" + b)

def _h01(a: bytes, b: bytes) -> bytes:
    return Web3.keccak(b"\x01" + a + b)

def _reduce_pairs(nodes: List[bytes]) -> bytes:
    """Merkle-style pairwise reduce；奇数时复制最后一个。"""
    if not nodes:
        return _h00(b"")
    lvl = list(nodes)
    while len(lvl) > 1:
        nxt = []
        for i in range(0, len(lvl), 2):
            left = lvl[i]
            right = lvl[i+1] if i+1 < len(lvl) else lvl[i]
            nxt.append(_h01(left, right))
        lvl = nxt
    return lvl[0]

def hash_hashedDoi(doi: str) -> bytes:
    # DOI: 小写 + NFKC + 叶前缀 0x00
    return _h00(_canon_str((doi or ""), lower=True))

def _authors_root(authors: List[str]) -> bytes:
    leaves = [_h00(_canon_str(a)) for a in (authors or [])]
    return _reduce_pairs(leaves)

def hash_hashedTAD(title: str, authors: List[str], date_iso: str) -> bytes:
    h_title = _h00(_canon_str(title))
    h_auth = _authors_root(authors)
    n_ta = _h01(h_title, h_auth)
    h_date = _h00(_canon_str(date_iso))
    return _h01(n_ta, h_date)

def metadata_root_from(md: Metadata) -> bytes:
    md_dict = _to_dict(md)
    title = md_dict.get("title") or ""
    authors = md_dict.get("authors") or []
    date_str = md_dict.get("date")
    if date_str is None:
        raise HTTPException(status_code=400, detail="metadata.date must be YYYY-MM-DD")
    norm_date = date.fromisoformat(str(date_str)).isoformat()

    doi = md_dict.get("doi") or ""

    h_title = _h00(_canon_str(title))
    h_auth = _authors_root(authors)
    n_ta = _h01(h_title, h_auth)

    h_doi = _h00(_canon_str(doi, lower=True))
    h_date = _h00(_canon_str(norm_date))
    n_dd = _h01(h_doi, h_date)

    return _h01(n_ta, n_dd)

def fulltext_root_from(text: Optional[str], chunk_size: int = 4096) -> bytes:
    if not text:
        return b"\x00" * 32
    b = text.encode("utf-8")
    leaves = []
    cs = max(1, int(chunk_size or 4096))
    for i in range(0, len(b), cs):
        chunk = b[i:i+cs]
        leaves.append(_h00(chunk))
    return _reduce_pairs(leaves)

def _to_hex32(x: bytes) -> str:
    return Web3.to_hex(x)

# ======================= ABI 动态探测（关键修复） ===================
def _find_register_method(c) -> str:
    """
    在 ABI 里查找接受四个 bytes32 参数的“注册”函数。
    先匹配常见名字；没有的话再按入参类型自动匹配。
    """
    preferred = ["register", "registerPaper", "registerDoc", "addPaper", "addDoc", "add", "submitPaper", "submit"]
    abi = getattr(c, "abi", [])
    by_name = {item.get("name"): item for item in abi if item.get("type") == "function"}

    for name in preferred:
        item = by_name.get(name)
        if item:
            inputs = item.get("inputs", [])
            if len(inputs) == 4 and all(i.get("type") == "bytes32" for i in inputs):
                return name

    for item in abi:
        if item.get("type") != "function":
            continue
        inputs = item.get("inputs", [])
        if len(inputs) == 4 and all(i.get("type") == "bytes32" for i in inputs):
            return item.get("name")

    raise RuntimeError("No register-like function (4 x bytes32) found in ABI; set CONTRACT_ABI_PATH correctly or check the contract.")

# ======================= DocId resolution helpers ==================
def _resolve_doc_id_by_metadata(c, md: Metadata) -> int:
    md_dict = _to_dict(md)
    doi = md_dict.get("doi")
    title = md_dict.get("title")
    authors = md_dict.get("authors") or []
    date_str = md_dict.get("date")

    if doi:
        did = c.functions.getDocIdByDoi(hash_hashedDoi(doi)).call()
        return int(did)

    if not (title and isinstance(authors, list) and date_str):
        raise HTTPException(status_code=400, detail="need doc_id or complete metadata (title/authors/date)")
    norm_date = date.fromisoformat(str(date_str)).isoformat()
    did = c.functions.getDocIdByTAD(hash_hashedTAD(title, authors, norm_date)).call()
    return int(did)

def _resolve_doc_id(c, doc_id_opt: Optional[int], md_opt: Optional[Metadata]) -> int:
    if doc_id_opt is not None:
        return int(doc_id_opt)
    if md_opt:
        did = _resolve_doc_id_by_metadata(c, md_opt)
        if did == 0 and (getattr(md_opt, "doi", None) or _to_dict(md_opt).get("doi") or "").strip():
            raise HTTPException(status_code=404, detail="paper not found by DOI")
        return int(did)
    raise HTTPException(status_code=400, detail="need doc_id or metadata")

# =============================== Routes ============================
@app.get("/")
def root():
    c = _load_contract()
    return {
        "ok": True,
        "chain_id": w3.eth.chain_id,
        "contract": c.address,
        "has_private_key": bool(PRIVATE_KEY),
        "gas_mode": f"legacy gasPrice {GAS_PRICE_GWEI} gwei"
    }

@app.post("/register")
def register(req: RegisterRequest):
    recovered = _assert_registrar_role(req.auth)

    md = req.metadata
    if md is None:
        raise HTTPException(status_code=400, detail="metadata required")

    md_dict = _to_dict(md)
    if md_dict.get("date") is None:
        raise HTTPException(status_code=400, detail="metadata.date must be YYYY-MM-DD")
    norm_date = date.fromisoformat(str(md_dict["date"])).isoformat()

    h_doi = hash_hashedDoi(md_dict.get("doi") or "")
    h_tad = hash_hashedTAD(md_dict.get("title") or "", md_dict.get("authors") or [], norm_date)
    md_root = metadata_root_from(md)
    ft_root = fulltext_root_from(getattr(req, "full_text", None) or md_dict.get("full_text") or "", getattr(req, "chunk_size", None) or 4096)

    c = _load_contract()

    if not PRIVATE_KEY:
        return {
            "ok": True,
            "message": "computed (no PRIVATE_KEY: dry-run)",
            "doc_id": None,
            "hashed_doi": _to_hex32(h_doi),
            "hashed_tad": _to_hex32(h_tad),
            "metadata_root": _to_hex32(md_root),
            "fulltext_root": _to_hex32(ft_root),
            "onchain_metadata_root": None,
            "onchain_fulltext_root": None,
            "details": {
                "checked_fields": ["doi", "title", "authors", "date"],
                "recovered_admin": recovered
            },
            "is_retracted": None
        }

    try:
        reg_name = _find_register_method(c)
        fn = getattr(c.functions, reg_name)(h_doi, h_tad, md_root, ft_root)
        tx_hash = _send_tx(fn)
    except Exception as e:
        return {
            "ok": False,
            "message": f"register tx failed: {e}",
            "doc_id": None,
            "hashed_doi": _to_hex32(h_doi),
            "hashed_tad": _to_hex32(h_tad),
            "metadata_root": _to_hex32(md_root),
            "fulltext_root": _to_hex32(ft_root),
            "onchain_metadata_root": None,
            "onchain_fulltext_root": None,
            "details": {
                "checked_fields": ["doi", "title", "authors", "date"],
                "recovered_admin": recovered
            },
            "is_retracted": None
        }

    doc_id = int(c.functions.getDocIdByDoi(h_doi).call() or 0) or int(c.functions.getDocIdByTAD(h_tad).call() or 0)
    on_md, on_ft, isr = c.functions.getPaper(doc_id).call() if doc_id else (None, None, None)
    return {
        "ok": True,
        "message": f"registered tx={tx_hash}",
        "doc_id": doc_id or None,
        "hashed_doi": _to_hex32(h_doi),
        "hashed_tad": _to_hex32(h_tad),
        "metadata_root": _to_hex32(md_root),
        "fulltext_root": _to_hex32(ft_root),
        "onchain_metadata_root": Web3.to_hex(on_md) if on_md is not None else None,
        "onchain_fulltext_root": Web3.to_hex(on_ft) if on_ft is not None else None,
        "details": {
            "checked_fields": ["doi", "title", "authors", "date"],
            "recovered_admin": recovered
        },
        "is_retracted": bool(isr) if isr is not None else None
    }

@app.post("/retraction/status")
def retraction_status(req: RetractionStatusRequest):
    c = _load_contract()
    doc_id = _resolve_doc_id(c, getattr(req, "doc_id", None), getattr(req, "metadata", None))
    if doc_id == 0:
        raise HTTPException(status_code=404, detail="paper not found")
    mr, fr, isr = c.functions.getPaper(doc_id).call()
    return {"doc_id": doc_id, "is_retracted": bool(isr)}

def _try_call_first(c, candidates: List[Tuple[str, Tuple]]) -> Tuple[str, str]:
    last_err = None
    names_in_abi = {f["name"] for f in getattr(c, "abi", []) if f.get("type") == "function"}
    for name, args in candidates:
        if name not in names_in_abi:
            last_err = f"{name} not in ABI"
            continue
        try:
            fn = getattr(c.functions, name)(*args)
            tx_hash = _send_tx(fn)
            return name, tx_hash
        except Exception as e:
            last_err = e
    raise HTTPException(status_code=500, detail=f"all retraction method calls failed: {last_err!r}")

@app.post("/retraction/set")
def retraction_set(req: RetractionSetRequest):
    recovered = _assert_registrar_role(req.auth)
    c = _load_contract()
    doc_id = _resolve_doc_id(c, getattr(req, "doc_id", None), getattr(req, "metadata", None))
    if doc_id == 0:
        raise HTTPException(status_code=404, detail="paper not found")

    if bool(getattr(req, "retract", False)):
        calls = [
            ("setRetractedStatus", (doc_id, True)),
            ("setRetracted", (doc_id, True)),
            ("retractPaper", (doc_id,))
        ]
    else:
        calls = [
            ("setRetractedStatus", (doc_id, False)),
            ("setRetracted", (doc_id, False)),
            ("unretractPaper", (doc_id,))
        ]
    method, tx_hash = _try_call_first(c, calls)
    return {"doc_id": doc_id, "retract": bool(getattr(req, "retract", False)), "tx": tx_hash, "method": method, "recovered": recovered}

@app.post("/papers/edit")
def papers_edit(req: EditRequest):
    recovered = _assert_registrar_role(req.auth)
    c = _load_contract()

    old_doc_id = _resolve_doc_id(c, getattr(req, "old_doc_id", None), getattr(req, "old_metadata", None))
    if old_doc_id == 0:
        raise HTTPException(status_code=404, detail="old paper not found")

    # 若旧文尚未撤稿，则先撤；若已撤则跳过（避免重复撤导致 revert）
    _, _, isr = c.functions.getPaper(old_doc_id).call()
    tx_retract: Optional[str] = None
    if not isr:
        method, tx_hash = _try_call_first(c, [
            ("setRetractedStatus", (old_doc_id, True)),
            ("setRetracted", (old_doc_id, True)),
            ("retractPaper", (old_doc_id,))
        ])
        tx_retract = tx_hash
    else:
        tx_retract = "skipped_already_retracted"

    new_md = getattr(req, "new_metadata", None)
    if new_md is None:
        raise HTTPException(status_code=400, detail="new_metadata required")
    md_dict = _to_dict(new_md)
    norm_date = date.fromisoformat(str(md_dict.get("date"))).isoformat()

    new_h_doi = hash_hashedDoi(md_dict.get("doi") or "")
    new_h_tad = hash_hashedTAD(md_dict.get("title") or "", md_dict.get("authors") or [], norm_date)
    new_md_root = metadata_root_from(new_md)
    new_ft_root = fulltext_root_from(getattr(req, "new_full_text", None) or "", getattr(req, "chunk_size", None) or 4096)

    try:
        reg_name = _find_register_method(c)
        fn = getattr(c.functions, reg_name)(new_h_doi, new_h_tad, new_md_root, new_ft_root)
        tx_add = _send_tx(fn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"add new failed: {e}")

    return {
        "ok": True,
        "tx_retract": tx_retract,
        "tx_add": tx_add,
        "new_hashed_doi": _to_hex32(new_h_doi),
        "new_hashed_tad": _to_hex32(new_h_tad),
        "new_metadata_root": _to_hex32(new_md_root),
        "new_fulltext_root": _to_hex32(new_ft_root),
        "recovered_admin": recovered
    }
    
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



@app.get("/paper/status")
def paper_status(doc_id: Optional[int] = None, doi: Optional[str] = None, title: Optional[str] = None, authors: Optional[str] = None, date: Optional[str] = None):
    """
    Convenience GET endpoint to query paper status directly by query params.
    You can pass ?doc_id= or ?doi= or (?title=&?authors=&?date=) where
    authors is comma-separated.
    """
    c = _load_contract()
    target_doc_id = None
    if doc_id is not None:
        target_doc_id = int(doc_id)
    elif doi and doi.strip():
        try:
            did = c.functions.getDocIdByDoi(hash_hashedDoi(doi)).call()
            target_doc_id = int(did)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"getDocIdByDoi failed: {e}")
    elif title and authors and date:
        try:
            authors_list = [a.strip() for a in authors.split(",") if a.strip()]
            norm_date = date.strip()
            did = c.functions.getDocIdByTAD(hash_hashedTAD(title, authors_list, norm_date)).call()
            target_doc_id = int(did)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"getDocIdByTAD failed: {e}")
    else:
        raise HTTPException(status_code=400, detail="need doc_id or doi or title+authors+date")

    if not target_doc_id:
        raise HTTPException(status_code=404, detail="paper not found")
    try:
        mr, fr, isr = c.functions.getPaper(target_doc_id).call()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"getPaper failed: {e}")
    return {"doc_id": target_doc_id, "is_retracted": bool(isr)}
