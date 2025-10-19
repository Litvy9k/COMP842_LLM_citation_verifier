from typing import Any, List
from datetime import date
import json, hashlib

def canonical_json_bytes(obj: Any) -> bytes:
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    return s.encode('utf-8')

def sha256_b32(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def normalize_doi(doi: str) -> str:
    if not doi:
        return ""
    v = doi.strip()
    prefixes = ["doi:", "https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/"]
    for p in prefixes:
        if v.lower().startswith(p):
            v = v[len(p):]
            break
    return v

def hash_hashedDoi(doi: str) -> bytes:
    return sha256_b32(canonical_json_bytes(normalize_doi(doi)))

def _normalize_date(d: date | str) -> str:
    if isinstance(d, date):
        return d.isoformat()
    if isinstance(d, str):
        try:
            return date.fromisoformat(d).isoformat()
        except Exception:
            raise ValueError("date must be ISO format YYYY-MM-DD")
    raise ValueError("date must be a date or ISO string")

def hash_hashedTAD(title: str, authors: List[str], date_value: date | str) -> bytes:
    title_norm = (title or "").strip()
    authors_norm = [str(a).strip() for a in (authors or [])]
    payload = {"title": title_norm, "authors": authors_norm, "date": _normalize_date(date_value)}
    return sha256_b32(canonical_json_bytes(payload))
