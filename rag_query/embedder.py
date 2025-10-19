from __future__ import annotations
from typing import List, Optional
import os

from langchain_community.vectorstores import FAISS

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever  


def build_vectorstore(
    docs,
    model_path: str = os.path.expanduser("../model/bge-small-en-v1.5"),
    normalize: bool = True,
):
    embedding_model = HuggingFaceEmbeddings(
        model_name=model_path,
        encode_kwargs={"normalize_embeddings": normalize},
    )
    vectorstore = FAISS.from_documents(docs, embedding_model)
    return vectorstore


def get_retriever(
    vectorstore,
    docs,
    k: int = 8,
    fetch_k: int = 50,
    mmr_lambda: float = 0.5,
    bm25_k: Optional[int] = None,
    weights=(0.6, 0.4),
):
    if bm25_k is None:
        bm25_k = max(k * 2, 8)

    bm25 = BM25Retriever.from_documents(docs)
    bm25.k = bm25_k

    dense = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": fetch_k,
            "lambda_mult": mmr_lambda,
        },
    )

    hybrid = EnsembleRetriever(
        retrievers=[bm25, dense],
        weights=list(weights),
    )
    return hybrid