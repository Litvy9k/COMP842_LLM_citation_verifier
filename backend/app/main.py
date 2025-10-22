# app/main.py
import os
import json
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

# -------------------------------------------------
# 尝试从 app.models 导入（六字段 metadata）
# -------------------------------------------------
try:
    from app.models import (
        AuthEnvelope, Metadata,
        RegisterRequest, RetractionStatusRequest, RetractionSetRequest,
        EditRequest, CompleteValidateRequest, ValidateResponse
    )
except Exception:
    # ---------- Fallback（仅导入失败时使用） ----------
    class _AuthEnvelopeFallback(BaseModel):
        message: str
        signature: str
        sig_type: Optional[str] = "eip191"

    class _MetadataFallback(BaseModel):
        doi: Optional[str] = None
        title: Optional[str] = None
        author: Optional[List[str]] = None
        date: Optional[str] = None
        journal: Optional[str] = None
        abstract: Optional[str] = None

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

    class _CompleteValidateRequestFallback(BaseModel):
        doc_id: Optional[int] = None
        metadata: Optional[_MetadataFallback] = None
        full_text: Optional[str] = None
        chunk_size: Optional[int] = 4096
        include_retraction: bool = True

    class _ValidateResponseFallback(BaseModel):
        ok: bool
        doc_id: Optional[int] = None
        hashed_doi: Optional[str] = None
        hashed_tad: Optional[str] = None
        metadata_root: Optional[str] = None
        fulltext_root: Optional[str] = None
        onchain_metadata_root: Optional[str] = None
        onchain_fulltext_root: Optional[str] = None
        matches: Optional[Dict[str, bool]] = None
        details: Optional[Dict[str, Any]] = None
        is_retracted: Optional[bool] = None

    AuthEnvelope = _AuthEnvelopeFallback
    Metadata = _MetadataFallback
    RegisterRequest = _RegisterRequestFallback
    RetractionStatusRequest = _RetractionStatusRequestFallback
    RetractionSetRequest = _RetractionSetRequestFallback
    EditRequest = _EditRequestFallback
    CompleteValidateRequest = _CompleteValidateRequestFallback
    ValidateResponse = _ValidateResponseFallback

# -------------------------------------------------
# canonical / merkle helper
# -------------------------------------------------
try:
    from app.canonical import canonical_json_bytes, normalize_doi, hash_hashedTAD
except Exception:
    import hashlib
    import json as _json
    from datetime import date as _date
    def canonical_json_bytes(obj: Any) -> bytes:
        return _json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')
    def _normalize_date(d: Any) -> str:
        if isinstance(d, _date):
            return d.isoformat()
        if isinstance(d, str):
            return _date.fromisoformat(d).isoformat()
        raise ValueError("date must be str or date")
    def hash_hashedTAD(title: str, authors: List[str], date_value: Any) -> bytes:
        payload = {"title": (title or "").strip(), "authors": [str(a).strip() for a in (authors or [])], "date": _normalize_date(date_value)}
        return hashlib.sha256(canonical_json_bytes(payload)).digest()
    def normalize_doi(doi: str) -> str:
        v = (doi or "").strip().lower()
        v = unicodedata.normalize("NFKC", v)
        v = v.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "").strip()
        return v

from app.merkle_sha256 import build_merkle

# -------------------------------------------------
# 配置 & Web3
# -------------------------------------------------
APP_NAME = "Citation Backend (six-field metadata)"
ETH_RPC_URL = os.getenv("ETH_RPC_URL", "http://127.0.0.1:8545")
CONTRACT_ADDRESS_ENV = os.getenv("CONTRACT_ADDRESS", "").strip()
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "").strip()
GAS_PRICE_GWEI = int(os.getenv("GAS_PRICE_GWEI", "1"))
REGISTER_FN_OVERRIDE = os.getenv("REGISTER_FN_OVERRIDE")  # 可选：注册函数名覆盖

CONTRACT_ABI_PATH = os.getenv("CONTRACT_ABI_PATH")  # 可选
HARDHAT_ROOT = Path(__file__).resolve().parents[2] / "citationregistry-hardhat-kit"
ABI_PATH_DEFAULT = HARDHAT_ROOT / "artifacts" / "contracts" / "CitationRegistry.sol" / "CitationRegistry.json"
DEPLOYMENTS_JSON = HARDHAT_ROOT / "deployments" / "localhost.json"

w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))

# -------------------------------------------------
# ABI & 地址
# -------------------------------------------------
def _auto_find_abi() -> Path:
    if CONTRACT_ABI_PATH:
        p = Path(CONTRACT_ABI_PATH)
        if p.exists(): return p
    if ABI_PATH_DEFAULT.exists():
        return ABI_PATH_DEFAULT
    try:
        for c in HARDHAT_ROOT.rglob("CitationRegistry.json"):
            return c
    except Exception:
        pass
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        art = parent / "artifacts"
        if art.exists():
            try:
                for c in art.rglob("CitationRegistry.json"):
                    return c
            except Exception:
                pass
    raise RuntimeError("ABI not found. Run 'npx hardhat compile' to generate artifacts.")

def _load_contract_address() -> str:
    if CONTRACT_ADDRESS_ENV:
        return Web3.to_checksum_address(CONTRACT_ADDRESS_ENV)
    if DEPLOYMENTS_JSON.exists():
        j = json.loads(DEPLOYMENTS_JSON.read_text(encoding="utf-8-sig"))
        adr = j.get("CitationRegistry")
        if adr:
            return Web3.to_checksum_address(adr)
    raise RuntimeError("Contract address not found. Set CONTRACT_ADDRESS or ensure deployments/localhost.json exists.")

def _load_contract():
    addr = _load_contract_address()
    abi_path = _auto_find_abi()
    abi = json.loads(abi_path.read_text(encoding="utf-8-sig"))["abi"]
    c = w3.eth.contract(address=addr, abi=abi)
    c.abi = abi
    return c

# -------------------------------------------------
# 签名/交易工具（兼容 web3.py v5/v6）
# -------------------------------------------------
def _get_account():
    return Account.from_key(PRIVATE_KEY) if PRIVATE_KEY else None

def _force_legacy_gas(tx: Dict[str, Any]) -> Dict[str, Any]:
    tx.pop("maxFeePerGas", None)
    tx.pop("maxPriorityFeePerGas", None)
    tx["gasPrice"] = w3.to_wei(GAS_PRICE_GWEI, "gwei")
    return tx

def _send_tx(fn) -> str:
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
    raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
    if raw is None:
        try:
            raw = bytes(signed)
        except Exception:
            raise RuntimeError("Could not resolve raw transaction payload from signed tx (web3 v5/v6 compatibility).")
    tx_hash = w3.eth.send_raw_transaction(raw)
    return tx_hash.hex() if hasattr(tx_hash, "hex") else Web3.to_hex(tx_hash)

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

# -------------------------------------------------
# 字段归一 & 哈希
# -------------------------------------------------
def _canon_str(s: str, lower: bool = False) -> str:
    if s is None: s = ""
    s = unicodedata.normalize("NFKC", s).strip()
    return s.lower() if lower else s

def hash_hashedDoi(doi: str) -> bytes:
    v = _canon_str(doi, lower=True)
    v = v.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "").strip()
    return Web3.keccak(text=v)

def _to_dict(x: Any) -> dict:
    if x is None:
        return {}
    if hasattr(x, "model_dump"):
        d = x.model_dump()
    elif hasattr(x, "dict"):
        d = x.dict()
    elif isinstance(x, dict):
        d = dict(x)
    else:
        d = {k: getattr(x, k) for k in dir(x) if not k.startswith("_")}
    # authors ↔ author 双向同步（向后兼容）
    if "author" not in d and "authors" in d:
        d["author"] = d.get("authors") or []
    if "authors" not in d and "author" in d:
        d["authors"] = d.get("author") or []
    return d

# -------------------------------------------------
# merkle roots
# -------------------------------------------------
def make_metadata_leaves(md: Any) -> List[bytes]:
    d = _to_dict(md)
    required = ["doi", "title", "author", "date", "journal", "abstract"]
    for k in required:
        if d.get(k) in (None, "", []):
            raise HTTPException(status_code=400, detail=f"metadata.{k} required")
    seq = [
        ("doi", d["doi"]),
        ("title", d["title"]),
        ("author", d["author"]),
        ("date", d["date"]),
        ("journal", d["journal"]),
        ("abstract", d["abstract"]),
    ]
    return [canonical_json_bytes({k: v}) for k, v in seq]

def metadata_root_from(md: Any) -> bytes:
    root, _ = build_merkle(make_metadata_leaves(md))
    return root

def make_fulltext_leaves(full_text: Optional[str], chunk_size: int) -> List[bytes]:
    if not full_text:
        return []
    text = full_text.encode("utf-8")
    leaves = []
    for i in range(0, len(text), chunk_size):
        leaves.append(text[i:i+chunk_size])
    return leaves

def fulltext_root_from(full_text: Optional[str], chunk_size: int) -> bytes:
    leaves = make_fulltext_leaves(full_text, chunk_size)
    root, _ = build_merkle(leaves)
    return root

# -------------------------------------------------
# ABI 函数辅助 & 注册函数选择
# -------------------------------------------------
def _abi_functions(c):
    return [f for f in getattr(c, "abi", []) if f.get("type") == "function"]

def _find_register_method(c) -> str:
    # a) 显式覆盖
    if REGISTER_FN_OVERRIDE:
        return REGISTER_FN_OVERRIDE
    fns = _abi_functions(c)
    names = {f.get("name") for f in fns if f.get("type") == "function"}
    # b) 常见精确名
    for name in ("register", "addPaper", "add_record", "registerPaper", "registerDoc", "addDocument"):
        if name in names:
            return name
    # c) 形状识别：非 view、4 入参、>=3个 bytes32
    candidates = []
    for f in fns:
        if f.get("stateMutability") == "view":
            continue
        inputs = f.get("inputs") or []
        if len(inputs) == 4:
            types = [i.get("type","") for i in inputs]
            b32_count = sum(1 for t in types if t.startswith("bytes32"))
            if b32_count >= 3:
                candidates.append(f.get("name"))
    if candidates:
        return candidates[0]
    # d) 名称模糊
    for f in fns:
        nm = (f.get("name") or "").lower()
        if any(k in nm for k in ("register","add","create","submit","publish","store","save")):
            inputs = f.get("inputs") or []
            if 3 <= len(inputs) <= 5:
                return f.get("name")
    raise HTTPException(status_code=500, detail=f"no register-like function in ABI; available={sorted(names)}")

# ---------- 撤稿函数：按 ABI 形状自适配 ----------
def _abi_input_count(c, name: str) -> Optional[int]:
    for f in getattr(c, "abi", []):
        if f.get("type") == "function" and f.get("name") == name:
            return len(f.get("inputs") or [])
    return None

def _send_tx_by_shape(c, name: str, doc_id: int, retract_flag: bool) -> str:
    argc = _abi_input_count(c, name)
    if argc is None:
        raise HTTPException(status_code=500, detail=f"{name} not in ABI")
    if argc == 0:
        fn = getattr(c.functions, name)()
    elif argc == 1:
        # 例如 retractPaper(uint256)
        fn = getattr(c.functions, name)(int(doc_id))
    else:
        # 例如 setRetracted(uint256,bool) / setRetraction(uint256,bool)
        fn = getattr(c.functions, name)(int(doc_id), bool(retract_flag))
    return _send_tx(fn)

# -------------------------------------------------
# FastAPI
# -------------------------------------------------
app = FastAPI(title=APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 调试：看 ABI 函数
@app.get("/__debug/abi-functions")
def debug_abi_functions():
    try:
        c = _load_contract()
        return {"ok": True, "functions": [f for f in c.abi if f.get("type") == "function"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/")
def root():
    try:
        c = _load_contract()
        info = {
            "ok": True,
            "chain_id": w3.eth.chain_id,
            "contract": c.address,
            "has_private_key": bool(PRIVATE_KEY),
            "gas_mode": f"legacy gasPrice {GAS_PRICE_GWEI} gwei"
        }
        return info
    except Exception as e:
        return {"ok": False, "error": str(e)}

# 角色校验
def _assert_registrar_role(auth: AuthEnvelope) -> str:
    recovered = _recover_eip191(auth)
    c = _load_contract()
    try:
        ok = c.get_function_by_signature("hasRole(bytes32,address)")(Web3.keccak(text="REGISTRAR_ROLE"), recovered).call()
    except Exception:
        try:
            role = c.functions.REGISTRAR_ROLE().call()
        except Exception:
            role = Web3.keccak(text="REGISTRAR_ROLE")
        ok = c.functions.hasRole(role, recovered).call()
    if not ok:
        raise HTTPException(status_code=403, detail="permission denied: REGISTRAR_ROLE required")
    return recovered

# -------------------------------------------------
# 路由
# -------------------------------------------------
@app.post("/register")
def register(req: RegisterRequest):
    recovered = _assert_registrar_role(req.auth)
    md = _to_dict(req.metadata)
    doi = md["doi"]; title = md["title"]; authors = md["author"]; date_str = md["date"]

    hashed_doi = hash_hashedDoi(doi)
    hashed_tad = hash_hashedTAD(title, authors, date.fromisoformat(date_str).isoformat())
    md_root = metadata_root_from(md)
    ft_root = fulltext_root_from(req.full_text or "", req.chunk_size or 4096)

    c = _load_contract()

    if not PRIVATE_KEY:
        return {
            "ok": True, "message": "computed (no PRIVATE_KEY: dry-run)",
            "doc_id": None,
            "hashed_doi": Web3.to_hex(hashed_doi),
            "hashed_tad": Web3.to_hex(hashed_tad),
            "metadata_root": Web3.to_hex(md_root),
            "fulltext_root": Web3.to_hex(ft_root),
            "onchain_metadata_root": None,
            "onchain_fulltext_root": None,
            "recovered_admin": recovered
        }

    method = _find_register_method(c)
    tx = _send_tx(getattr(c.functions, method)(hashed_doi, hashed_tad, md_root, ft_root))

    # 可选：等交易出块后回查 doc_id（避免你说“没有 doc_id”）
    try:
        w3.eth.wait_for_transaction_receipt(tx)
        doc_id = int(c.functions.getDocIdByDoi(hashed_doi).call())
    except Exception:
        doc_id = None

    return {
        "ok": True,
        "tx": tx,
        "hashed_doi": Web3.to_hex(hashed_doi),
        "hashed_tad": Web3.to_hex(hashed_tad),
        "metadata_root": Web3.to_hex(md_root),
        "fulltext_root": Web3.to_hex(ft_root),
        "recovered_admin": recovered,
        "doc_id": doc_id
    }

@app.post("/retraction/status")
def retraction_status(req: RetractionStatusRequest):
    c = _load_contract()
    did = _resolve_doc_id(c, getattr(req, "doc_id", None), getattr(req, "metadata", None))
    if not did:
        raise HTTPException(status_code=404, detail="paper not found")
    mr, fr, isr = c.functions.getPaper(did).call()
    return {"doc_id": int(did), "is_retracted": bool(isr)}

def _try_call_first(c, candidates: List[Tuple[str, Tuple]]) -> Tuple[str, str]:
    names_in_abi = {f["name"] for f in getattr(c, "abi", []) if f.get("type") == "function"}
    last_err = None
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
    raise HTTPException(status_code=500, detail=f"all candidate calls failed: {last_err!r}")

@app.post("/retraction/set")
def retraction_set(req: RetractionSetRequest):
    recovered = _assert_registrar_role(req.auth)
    c = _load_contract()
    did = _resolve_doc_id(c, getattr(req, "doc_id", None), getattr(req, "metadata", None))
    if not did:
        raise HTTPException(status_code=404, detail="paper not found")

    # 优先尝试常见函数名，按 ABI 的入参个数自动决定是否带 bool
    names_in_abi = {f["name"] for f in getattr(c, "abi", []) if f.get("type") == "function"}
    last_err = None
    for cand in ("setRetraction", "setRetracted", "retractPaper", "retract", "setPaperRetracted"):
        if cand in names_in_abi:
            try:
                tx_hash = _send_tx_by_shape(c, cand, int(did), bool(req.retract))
                return {"ok": True, "fn": cand, "tx": tx_hash, "doc_id": int(did), "recovered_admin": recovered}
            except Exception as e:
                last_err = e
                continue
    raise HTTPException(status_code=500, detail=f"no matching retraction function worked; last_err={last_err!r}")

def _resolve_doc_id(c, doc_id: Optional[int], metadata: Optional[Any]) -> int:
    if doc_id:
        return int(doc_id)
    if metadata:
        d = _to_dict(metadata)
        if d.get("doi"):
            return int(c.functions.getDocIdByDoi(hash_hashedDoi(d["doi"])).call())
        if d.get("title") and d.get("author") and d.get("date"):
            h = hash_hashedTAD(d["title"], d["author"], date.fromisoformat(d["date"]).isoformat())
            names = {f["name"] for f in getattr(c, "abi", []) if f.get("type") == "function"}
            if "getDocIdByTAD" in names:
                did = c.functions.getDocIdByTAD(h).call()
            elif "getDocIdByTad" in names:
                did = c.functions.getDocIdByTad(h).call()
            else:
                raise HTTPException(status_code=500, detail="no getDocIdByTAD/Tad in ABI")
            return int(did)
    return 0

@app.post("/papers/edit")
def papers_edit(req: EditRequest):
    recovered = _assert_registrar_role(req.auth)
    c = _load_contract()
    old_id = _resolve_doc_id(c, getattr(req, "old_doc_id", None), getattr(req, "old_metadata", None))
    if not old_id:
        raise HTTPException(status_code=404, detail="old paper not found")

    # 旧文撤回（自适配一参/二参）
    names_in_abi = {f["name"] for f in getattr(c, "abi", []) if f.get("type") == "function"}
    last_err = None
    for cand in ("setRetraction", "setRetracted", "retractPaper", "retract", "setPaperRetracted"):
        if cand in names_in_abi:
            try:
                _ = _send_tx_by_shape(c, cand, int(old_id), True)
                break
            except Exception as e:
                last_err = e
                continue
    if last_err and old_id:
        raise HTTPException(status_code=500, detail=f"retract old failed: {last_err!r}")

    # 新文注册
    new_md = _to_dict(req.new_metadata)
    doi = new_md["doi"]; title = new_md["title"]; authors = new_md["author"]; date_str = new_md["date"]
    md_root = metadata_root_from(new_md)
    ft_root = fulltext_root_from(getattr(req, "new_full_text", None) or "", getattr(req, "chunk_size", None) or 4096)
    h_doi = hash_hashedDoi(doi)
    h_tad = hash_hashedTAD(title, authors, date.fromisoformat(date_str).isoformat())
    reg_name = _find_register_method(c)
    tx2 = _send_tx(getattr(c.functions, reg_name)(h_doi, h_tad, md_root, ft_root))

    return {
        "ok": True,
        "register_tx": tx2,
        "new_hashed_doi": Web3.to_hex(h_doi),
        "new_hashed_tad": Web3.to_hex(h_tad),
        "new_metadata_root": Web3.to_hex(md_root),
        "new_fulltext_root": Web3.to_hex(ft_root),
        "recovered_admin": recovered
    }

@app.post("/validate/complete-metadata", response_model=ValidateResponse)
def validate_complete(req: CompleteValidateRequest):
    md = _to_dict(req.metadata or {})
    doi = md.get("doi"); title = md.get("title"); authors = md.get("author"); date_str = md.get("date")
    if not (doi and title and isinstance(authors, list) and date_str):
        raise HTTPException(status_code=400, detail="metadata must include doi,title,author(list),date")
    h_doi = hash_hashedDoi(doi)
    h_tad = hash_hashedTAD(title, authors, date.fromisoformat(date_str).isoformat())
    md_root = metadata_root_from(md)
    ft_root = fulltext_root_from(getattr(req, "full_text", None) or "", getattr(req, "chunk_size", None) or 4096)

    c = _load_contract()
    did = _resolve_doc_id(c, getattr(req, "doc_id", None), md)
    if not did:
        raise HTTPException(status_code=404, detail="paper not found")
    on_md, on_ft, isr = c.functions.getPaper(int(did)).call()

    matches = {
        "metadata_root": Web3.to_hex(md_root) == Web3.to_hex(on_md),
        "fulltext_root": Web3.to_hex(ft_root) == Web3.to_hex(on_ft),
    }
    return ValidateResponse(
        ok=True, doc_id=int(did),
        hashed_doi=Web3.to_hex(h_doi),
        hashed_tad=Web3.to_hex(h_tad),
        metadata_root=Web3.to_hex(md_root),
        fulltext_root=Web3.to_hex(ft_root),
        onchain_metadata_root=Web3.to_hex(on_md),
        onchain_fulltext_root=Web3.to_hex(on_ft),
        matches=matches,
        details={"checked_fields": ["doi", "title", "author", "date", "journal", "abstract"]},
        is_retracted=bool(isr) if getattr(req, "include_retraction", True) else None
    )

@app.get("/paper/status")
def paper_status(doc_id: Optional[int] = None, doi: Optional[str] = None, title: Optional[str] = None, authors: Optional[str] = None, date: Optional[str] = None):
    c = _load_contract()
    target_doc_id = None
    if doc_id is not None:
        target_doc_id = int(doc_id)
    elif doi and doi.strip():
        did = c.functions.getDocIdByDoi(hash_hashedDoi(doi)).call()
        target_doc_id = int(did)
    elif title and authors and date:
        author_list = [a.strip() for a in authors.split(",") if a.strip()]
        h = hash_hashedTAD(title, author_list, date)
        names = {f["name"] for f in getattr(c, "abi", []) if f.get("type") == "function"}
        if "getDocIdByTAD" in names:
            target_doc_id = int(c.functions.getDocIdByTAD(h).call())
        elif "getDocIdByTad" in names:
            target_doc_id = int(c.functions.getDocIdByTad(h).call())
        else:
            raise HTTPException(status_code=500, detail="no getDocIdByTAD/Tad in ABI")

    if not target_doc_id:
        raise HTTPException(status_code=404, detail="paper not found")
    on_md, on_ft, isr = c.functions.getPaper(target_doc_id).call()
    return {"doc_id": target_doc_id, "is_retracted": bool(isr)}
