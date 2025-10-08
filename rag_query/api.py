from fastapi import FastAPI
from pydantic import BaseModel
from data_loader import load_documents
from embedder import build_vectorstore, get_retriever
from rag_chain import build_rag_chain

app = FastAPI()

docs = load_documents("papers.json")
vectorstore = build_vectorstore(docs)
retriever = get_retriever(vectorstore)
rag_chain = build_rag_chain(retriever, model_path="~/git_workspace/COMP842_LLM_citation_verifier/model/mistral-7b")

class Query(BaseModel):
    question: str
    max_tokens: int = 100

@app.post("/rag")
async def rag_answer(query: Query):
    rag_chain.llm.max_tokens = query.max_tokens
    result = rag_chain.invoke(query.question)
    return {"response": result}