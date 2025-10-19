import os
import torch
import random
from nlp_normalizer import normalize_query_nlp
# from typing import List, Dict, Any
from transformers import AutoTokenizer, AutoModelForCausalLM

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
RETRIEVER = get_retriever(VS, DOCS, k=8, fetch_k=50, mmr_lambda=0.5, bm25_k=16, weights=(0.6, 0.4))
rag_chain, llm = build_rag_chain(model_path=MODEL_PATH) 
# tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
# model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, device_map="auto", dtype=torch.float16)

# -----------------------
# Utils
# -----------------------
# def is_research_query(text: str) -> bool:
#     keywords = [
#         "paper", "papers", "publication", "preprint", "arxiv", "doi", "journal",
#         "cite", "citation", "reference", "references", "bibliography", "literature",
#         "survey", "systematic review", "meta-analysis",
#         "compare papers", "related work", "state of the art",
#         "find me a paper", "find papers", "looking for papers",
#     ]
#     text_low = text.lower()
#     return any(kw in text_low for kw in keywords)

def retrieve_query(x) -> str:
    if hasattr(x, "prompt"):
        x = getattr(x, "prompt")
    return x

def choose_weighted_hit(hits, scheme: str = "exp", decay: float = 0.65):
    if not hits:
        return None
    n = len(hits)

    if scheme == "exp":
        weights = [decay ** i for i in range(n)]
    elif scheme == "linear":
        weights = [n - i for i in range(n)]
    elif scheme == "harmonic":
        weights = [1.0 / (i + 1) for i in range(n)]
    else:
        weights = [1.0] * n

    return random.choices(hits, weights=weights, k=1)[0]

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
    query_text = retrieve_query(q)
    hits = RETRIEVER.invoke(query_text)[:k]
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

    query_text = retrieve_query(q)
    # if not is_research_query(query_text):
    #     messages = [
    #         {"role": "system", "content": "You are a helpful assistant. Answer concisely and stop when done."},
    #         {"role": "user", "content": query_text}
    #     ]
    #     prompt_text = tokenizer.apply_chat_template(
    #         messages,
    #         tokenize=False,
    #         add_generation_prompt=True
    #     )

    #     inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
        
    #     max_toks = int(getattr(q, "max_tokens", 300) or 300)
    #     outputs = model.generate(
    #         **inputs,
    #         max_new_tokens=max_toks,
    #         temperature=0.3,
    #         top_p=0.9,
    #         do_sample=True,
    #         eos_token_id=tokenizer.eos_token_id,
    #     )

    #     response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    #     if "assistant" in response.lower():
    #         response = response.split("assistant")[-1].strip()

    #     return {"response": response}
    # else:
    query_text = normalize_query_nlp(query_text)
    hits_all = RETRIEVER.invoke(query_text)[: int(getattr(q, "top_k", 6) or 6)]
    if not hits_all:
        return {"response": "INSUFFICIENT_EVIDENCE", "auto_revised": False}


    hit = choose_weighted_hit(hits_all, scheme="exp", decay=0.65)

    hits = [hit]
    meta = getattr(hit, "metadata", {}) or {}

    top_title = meta.get("title", "")
    sources = _format_docs(hits)
    max_toks = int(getattr(q, "max_tokens", 300) or 300)

    out1 = rag_chain.invoke({
        "question": q.prompt,
        "sources": sources,
        "max_tokens": max_toks,
    })
    text1 = str(out1).strip()

    if top_title and (top_title.lower() in text1.lower()):
        return {
            "response": text1,
            "auto_revised": False,
            "paper_metadata": meta,
        }

    forced_q = q.prompt + "\n\n" + _revise_instruction_natural(top_title)
    out2 = rag_chain.invoke({
        "question": forced_q,
        "sources": sources,
        "max_tokens": max_toks,
    })
    text2 = str(out2).strip()

    if top_title and (top_title.lower() in text2.lower()):
        return {
            "response": text2,
            "auto_revised": True,
            "paper_metadata": meta,
        }

    return {
        "response": "INSUFFICIENT_EVIDENCE",
        "auto_revised": True,
        "paper_metadata": meta,
    }