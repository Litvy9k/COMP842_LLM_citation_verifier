from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any
from .models import RegisterRequest, ValidateResponse, CompleteValidateRequest, PartialValidateRequest
from .canonical import canonical_json_bytes, normalize_doi, hash_hashedDoi, hash_hashedTAH
from .merkle_sha256 import build_merkle
from .blockchain import RegistryClient
from .storage import save_cache, load_cache
from .config import LOCAL_STORE_LEAVES

app = FastAPI(title="CitationRegistry Backend (SHA-256 & canonical JSON)")

def make_metadata_leaves(md: Dict[str, Any]) -> List[bytes]:
    leaves: List[bytes] = []
    for k in sorted(md.keys()):
        leaves.append(canonical_json_bytes({k: md[k]}))
    return leaves

def make_fulltext_leaves(full_text: str | None, chunk: int) -> List[bytes]:
    if not full_text:
        return []
    s = full_text
    return [s[i:i+chunk].encode("utf-8") for i in range(0, len(s), chunk)]

@app.post("/register", response_model=ValidateResponse)
def register(req: RegisterRequest):
    md = dict(req.metadata or {})
    doi = md.get("doi")
    title = md.get("title")
    authors = md.get("authors") or []
    year = md.get("year")

    if not doi or not title or not isinstance(authors, list) or year is None:
        raise HTTPException(status_code=400, detail="metadata must include doi, title, authors(list), year(int)")

    hashed_doi = hash_hashedDoi(doi)
    hashed_tah = hash_hashedTAH(title, authors, int(year))

    meta_leaves = make_metadata_leaves(md)
    full_leaves = make_fulltext_leaves(req.full_text, req.chunk_size)

    metadata_root, _ = build_merkle(meta_leaves)
    fulltext_root, _ = build_merkle(full_leaves)

    client = RegistryClient()
    tx_hash = client.register(hashed_doi, hashed_tah, metadata_root, fulltext_root)
    doc_id = client.get_doc_id_by_doi(hashed_doi)

    if LOCAL_STORE_LEAVES:
        save_cache(hashed_doi.hex(), {
            "metadata": md,
            "full_text_present": bool(req.full_text),
            "chunk_size": req.chunk_size
        })

    return ValidateResponse(
        ok=True, message="registered",
        doc_id=doc_id,
        hashed_doi=hashed_doi.hex(),
        hashed_tah=hashed_tah.hex(),
        metadata_root=metadata_root.hex(),
        fulltext_root=fulltext_root.hex(),
        details={"tx_hash": tx_hash}
    )

@app.post("/validate/complete-metadata", response_model=ValidateResponse)
def validate_complete(req: CompleteValidateRequest):
    md = dict(req.metadata or {})
    doi = md.get("doi")
    title = md.get("title")
    authors = md.get("authors") or []
    year = md.get("year")

    if not doi or not title or not isinstance(authors, list) or year is None:
        raise HTTPException(status_code=400, detail="metadata must include doi, title, authors(list), year(int)")

    hashed_doi = hash_hashedDoi(doi)
    hashed_tah = hash_hashedTAH(title, authors, int(year))

    meta_leaves = make_metadata_leaves(md)
    full_leaves = make_fulltext_leaves(req.full_text, req.chunk_size)
    metadata_root, _ = build_merkle(meta_leaves)
    fulltext_root, _ = build_merkle(full_leaves)

    client = RegistryClient()
    doc_id = client.get_doc_id_by_doi(hashed_doi)
    if doc_id == 0:
        # optional fallback: try TAH path
        doc_id = client.get_doc_id_by_tah(hashed_tah)
        if doc_id == 0:
            return ValidateResponse(ok=False, message="not registered (by DOI nor TAH)",
                                    hashed_doi=hashed_doi.hex(), hashed_tah=hashed_tah.hex())

    onchain_meta_root, onchain_full_root = client.get_paper(doc_id)
    ok = (onchain_meta_root == metadata_root) and (onchain_full_root == fulltext_root)

    return ValidateResponse(
        ok=ok, message="match" if ok else "mismatch",
        doc_id=doc_id,
        hashed_doi=hashed_doi.hex(),
        hashed_tah=hashed_tah.hex(),
        metadata_root=metadata_root.hex(),
        fulltext_root=fulltext_root.hex(),
        onchain_metadata_root=onchain_meta_root.hex() if isinstance(onchain_meta_root,(bytes,bytearray)) else str(onchain_meta_root),
        onchain_fulltext_root=onchain_full_root.hex() if isinstance(onchain_full_root,(bytes,bytearray)) else str(onchain_full_root),
    )

@app.post("/validate/partial-metadata", response_model=ValidateResponse)
def validate_partial(req: PartialValidateRequest):
    md = dict(req.metadata or {})
    doi = md.get("doi")
    if not doi:
        raise HTTPException(status_code=400, detail="metadata.doi is required")

    hashed_doi = hash_hashedDoi(doi)
    client = RegistryClient()
    doc_id = client.get_doc_id_by_doi(hashed_doi)
    if doc_id == 0:
        return ValidateResponse(ok=False, message="not registered (by DOI)", hashed_doi=hashed_doi.hex())

    cache = load_cache(hashed_doi.hex())
    if not cache or "metadata" not in cache:
        return ValidateResponse(ok=False, message="no local cache for partial validation (demo)", doc_id=doc_id)

    cached = cache["metadata"]
    for k, v in md.items():
        if k != "doi":
            cached[k] = v

    meta_leaves = make_metadata_leaves(cached)
    metadata_root, _ = build_merkle(meta_leaves)
    onchain_meta_root, onchain_full_root = client.get_paper(doc_id)

    ok = (onchain_meta_root == metadata_root)
    return ValidateResponse(
        ok=ok, message="match" if ok else "mismatch",
        doc_id=doc_id,
        hashed_doi=hashed_doi.hex(),
        metadata_root=metadata_root.hex(),
        onchain_metadata_root=onchain_meta_root.hex() if isinstance(onchain_meta_root,(bytes,bytearray)) else str(onchain_meta_root),
        onchain_fulltext_root=onchain_full_root.hex() if isinstance(onchain_full_root,(bytes,bytearray)) else str(onchain_full_root),
        details={"checked_fields": req.fields_to_check}
    )
