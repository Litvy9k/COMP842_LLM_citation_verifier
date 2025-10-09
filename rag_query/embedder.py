from typing import List
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

def build_vectorstore(docs, model_name="../model/bge-small-en-v1.5"):
    embedding_model = HuggingFaceEmbeddings(
        model_name=model_name,
        encode_kwargs={"normalize_embeddings": True},
    )
    vectorstore = FAISS.from_documents(documents=docs, embedding=embedding_model)
    return vectorstore

def get_retriever(
    vectorstore,
    k: int = 6,
    use_mmr: bool = True,
    fetch_k: int = 24,
):
    if use_mmr:
        return vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": fetch_k, "lambda_mult": 0.5},
        )
    else:
        return vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k},
        )