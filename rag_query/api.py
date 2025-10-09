import os
import re
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
MODEL_PATH = os.path.expanduser(os.environ.get("LOCAL_LLM_PATH", "../model/mistral-7b"))  # 改成你的本地路径

# -----------------------
# App init
# -----------------------
app = FastAPI(title="RAG API", version="1.0")

DOCS = load_documents(PAPER_JSON)                      # 你的 data_loader 返回 List[Document]
VS = build_vectorstore(DOCS)                           # 向量库（FAISS）
RETRIEVER = get_retriever(VS, k=8)                     # 检索器（建议在 embedder 里用 MMR、fetch_k）
rag_chain, llm = build_rag_chain(model_path=MODEL_PATH)  # 链：只负责提示+LLM，不做检索

# -----------------------
# Utils
# -----------------------
# 放宽的引用正则：允许 -, _, ., :（DOI 常见），如需再放宽可加 '/'
CITE_RE = re.compile(r"\[#\s*([A-Za-z0-9._:\-]+)\s*\]")

def _strip_prompt_echo(text: str) -> str:
    t = text or ""
    key = "SOURCES:"
    idx = t.find(key)
    if idx == -1:
        return t
    post = t[idx + len(key):]
    sep = post.find("\n\n")
    if sep != -1:
        return post[sep+2:].lstrip()
    return t

def _extract_ids(text: str) -> List[str]:
    return sorted(set(CITE_RE.findall(text or "")))

def _drop_placeholders(ids: List[str]) -> List[str]:
    """过滤模型误打的占位符（如 'paper_id'）"""
    return [i for i in ids if str(i).lower().strip() not in {"paper_id", "id"}]

def _collect_allowed_ids(hits) -> List[str]:
    """从检索结果提取白名单 id 列表（去重保序）"""
    seen, out = set(), []
    for d in hits:
        md = getattr(d, "metadata", {}) or {}
        pid = md.get("id") or md.get("doi") or md.get("paper_id")
        if not pid:
            continue
        pid = str(pid)
        if pid not in seen:
            seen.add(pid)
            out.append(pid)
    return out

def _format_docs(docs, max_chars: int = 900) -> str:
    """把检索到的文档转成可读 SOURCES 文本"""
    lines = []
    for d in docs:
        md = getattr(d, "metadata", {}) or {}
        pid   = md.get("id") or md.get("paper_id") or md.get("doi") or "UNKNOWN_ID"
        title = md.get("title", "") or ""
        year  = md.get("year", "") or ""
        doi   = md.get("doi", "") or ""
        excerpt = (getattr(d, "page_content", "") or "").strip()[:max_chars]
        lines.append(f"- [#{pid}] {title} ({year}) DOI:{doi}\n{excerpt}")
    return "\n".join(lines)

def _revise_instruction(allowed: List[str]) -> str:
    return (
        "Re-write the entire answer.\n"
        f"Use ONLY these ids: {allowed}.\n"
        "Place [#paper_id] immediately after EACH factual sentence.\n"
        "Do NOT invent any ids (never write placeholders like [#paper_id]). "
        "Delete any claim you cannot support with the allowed ids."
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

    # 1) 同一次检索 → 产出 allowed_ids + sources（文本）
    k = int(getattr(q, "top_k", 6) or 6)
    hits = RETRIEVER.invoke(q.prompt)[:k]
    top_hit = hits[0:1]
    allowed_ids = _collect_allowed_ids(top_hit)
    sources = _format_docs(top_hit)
    max_toks = int(getattr(q, "max_tokens", 300) or 300)

    # 2) 首次生成
    out1 = rag_chain.invoke({
        "question": q.prompt,
        "allowed_ids": allowed_ids,
        "sources": sources,
        "max_tokens": max_toks,
    })
    text1 = str(out1)
    text1_body = _strip_prompt_echo(text1)
    used1_raw = _extract_ids(text1_body)
    used1 = _drop_placeholders(used1_raw)
    out_of_white1 = [x for x in used1 if x not in allowed_ids]

    if used1 and not out_of_white1:
        return {
            "response": text1,
            "citations_used": used1,
            "allowed_ids": allowed_ids,
            "auto_revised": False
        }

    # 3) 强制重写一次（无引用或越界引用）
    forced_q = q.prompt + "\n\n" + _revise_instruction(allowed_ids)
    out2 = rag_chain.invoke({
        "question": forced_q,
        "allowed_ids": allowed_ids,
        "sources": sources,
        "max_tokens": max_toks,
    })
    text2 = str(out2)
    text2_body = _strip_prompt_echo(text2)
    used2_raw = _extract_ids(text2_body)
    used2 = _drop_placeholders(used2_raw)
    out_of_white2 = [x for x in used2 if x not in allowed_ids]

    if used2 and not out_of_white2:
        return {
            "response": text2,
            "citations_used": used2,
            "allowed_ids": allowed_ids,
            "auto_revised": True
        }

    # 4) 仍失败 → 兜底 + 诊断信息便于排查
    return {
        "response": "INSUFFICIENT_EVIDENCE",
        "citations_used": used2,
        "allowed_ids": allowed_ids,
        "auto_revised": True,
        "debug": {
            "sources_preview": sources[:1000],
            "gen1_preview": text1[:1000],
            "gen1_used_raw": used1_raw,
            "gen1_used": used1,
            "gen1_out_of_white": out_of_white1,
            "gen2_preview": text2[:1000],
            "gen2_used_raw": used2_raw,
            "gen2_used": used2,
            "gen2_out_of_white": out_of_white2
        }
    }