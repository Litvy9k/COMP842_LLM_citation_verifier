import os
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from data_loader import load_documents
from embedder import build_vectorstore, get_retriever
from rag_chain import build_rag_chain

# -----------------------
# Config
# -----------------------
PAPER_JSON = os.environ.get("PAPER_JSON", "paper.json")
MODEL_PATH = os.path.expanduser(os.environ.get("LOCAL_LLM_PATH", "../model/mistral-7b"))

# -----------------------
# App init
# -----------------------
app = FastAPI(title="RAG API", version="1.0")

DOCS = load_documents(PAPER_JSON)
VS = build_vectorstore(DOCS)
RETRIEVER = get_retriever(VS, k=8)
rag_chain, llm = build_rag_chain(model_path=MODEL_PATH) 

# -----------------------
# Utils
# -----------------------
def _collect_titles(hits) -> List[str]:
    out = []
    for d in hits:
        md = getattr(d, "metadata", {}) or {}
        t = (md.get("title") or "").strip()
        if t:
            out.append(t)
    return out

def _format_docs(docs, max_chars: int = 900) -> str:
    lines = []
    for d in docs:
        md = getattr(d, "metadata", {}) or {}
        title = md.get("title", "") or ""
        year  = md.get("year", "") or ""
        authors = md.get("authors", "") or ""
        doi   = md.get("doi", "") or ""
        excerpt = (getattr(d, "page_content", "") or "").strip()[:max_chars]
        lines.append(f"- TITLE: {title}\n  AUTHORS: {authors}\n  YEAR: {year}\n  DOI: {doi}\n  EXCERPT: {excerpt}")
    return "\n\n".join(lines)

def _revise_instruction_natural(single_title: str) -> str:
    return (
        "Re-write as a single concise paragraph.\n"
        f"Explicitly mention the paper titled “{single_title}” and include its year and author(s) in plain text.\n"
        "Do NOT mention any other papers. Do NOT add a references list. Do NOT use citation markers."
    )

# -----------------------
# Schemas
# -----------------------
class Query(BaseModel):
    prompt: str
    max_tokens: int = 300
    top_k: int = 6

# -----------------------
# Routes
# -----------------------
@app.get("/health")
async def health():
    return {"ok": True, "docs": len(DOCS)}

@app.get("/debug/retrieve")
async def debug_retrieve(q: str, k: int = 6):
    hits = RETRIEVER.invoke(q)[:k]
    results = []
    for i, d in enumerate(hits, 1):
        md = getattr(d, "metadata", {}) or {}
        results.append({
            "rank": i,
            "id": md.get("id") or md.get("doi") or md.get("paper_id"),
            "title": md.get("title"),
            "year": md.get("year"),
            "doi": md.get("doi"),
            "snippet": (getattr(d, "page_content", "") or "")[:220],
        })
    return {"query": q, "top_k": k, "results": results}

@app.post("/rag")
async def rag_answer(q: Query):
    if not q.prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    hits_all = RETRIEVER.invoke(q.prompt)[: int(getattr(q, "top_k", 6) or 6)]
    if not hits_all:
        return {"response": "INSUFFICIENT_EVIDENCE", "auto_revised": False}

    hits = hits_all[:1]
    titles = _collect_titles(hits)
    top_title = titles[0] if titles else ""

    sources = _format_docs(hits)
    max_toks = int(getattr(q, "max_tokens", 300) or 300)

    out1 = rag_chain.invoke({
        "question": q.prompt,
        "sources": sources,
        "max_tokens": max_toks,
    })
    text1 = str(out1).strip()

    if top_title and (top_title.lower() in text1.lower()):
        return {"response": text1, "auto_revised": False}

    forced_q = q.prompt + "\n\n" + _revise_instruction_natural(top_title)
    out2 = rag_chain.invoke({
        "question": forced_q,
        "sources": sources,
        "max_tokens": max_toks,
    })
    text2 = str(out2).strip()

    if top_title and (top_title.lower() in text2.lower()):
        return {"response": text2, "auto_revised": True}

    return {"response": "INSUFFICIENT_EVIDENCE", "auto_revised": True}