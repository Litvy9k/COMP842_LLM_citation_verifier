from typing import Any, Dict, List
import json, hashlib

def canonical_json_bytes(obj: Any) -> bytes:
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    return s.encode('utf-8')

def sha256_b32(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def normalize_doi(doi: str) -> str:
    if not doi: return ""
    v = doi.strip()
    for p in ("doi:", "https://doi.org/", "http://doi.org/"):
        if v.lower().startswith(p):
            v = v[len(p):]
    return v

def hash_hashedDoi(doi: str) -> bytes:
    return sha256_b32(canonical_json_bytes(normalize_doi(doi)))

def hash_hashedTAH(title: str, authors: List[str], year: int) -> bytes:
    payload = {"title": title, "authors": authors, "year": year}
    return sha256_b32(canonical_json_bytes(payload))
