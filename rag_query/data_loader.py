import json
import re
import hashlib
from typing import List
from langchain_core.documents import Document

def _norm(s: str) -> str:
    return (s or "").strip()

def _make_id(paper: dict) -> str:
    doi = _norm(paper.get("doi", ""))
    if doi:
        safe = re.sub(r"[^A-Za-z0-9_\-]", "-", doi)
        return f"doi-{safe}".lower()
    title = _norm(paper.get("title", ""))
    date = _norm(paper.get("date") or "")
    base = f"{title}|{date}"
    hid = hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]
    return f"tY-{hid}"

def _join_author(auth):
    if isinstance(auth, list):
        return ", ".join([_norm(a) for a in auth if _norm(a)])
    return _norm(auth)

def _join_keywords(kw):
    if isinstance(kw, list):
        return ", ".join([_norm(k) for k in kw if _norm(k)])
    return _norm(kw)

def _build_page_content(p: dict) -> str:
    title = _norm(p.get("title"))
    date  = _norm(p.get("date"))
    doi   = _norm(p.get("doi"))
    jnl   = _norm(p.get("journal"))
    auths = _join_author(p.get("author"))
    ab    = _norm(p.get("abstract"))

    return (
        f"TITLE: {title}\n"
        f"author: {auths}\n"
        f"DATE: {date}\n"
        f"DOI: {doi}\n"
        f"JOURNAL: {jnl}\n"
        f"ABSTRACT: {ab}"
    ).strip()

def load_documents(json_path: str) -> List[Document]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs: List[Document] = []
    for paper in data:
        pid = _make_id(paper)
        page_content = _build_page_content(paper)

        metadata = {
            "id": pid,
            "title": _norm(paper.get("title")),
            "date": _norm(paper.get("date")),
            "doi": _norm(paper.get("doi")),
            "author": _join_author(paper.get("author")),
            "journal": _norm(paper.get("journal")),
            "abstract": _norm(paper.get("abstract")),
        }

        docs.append(Document(page_content=page_content, metadata=metadata))

    return docs