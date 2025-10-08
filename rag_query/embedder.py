from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

def build_vectorstore(docs, model_name="../model/all-MiniLM-L6-v2"):
    embedding_model = HuggingFaceEmbeddings(model_name=model_name)
    vectorstore = FAISS.from_documents(docs, embedding_model)
    return vectorstore

def get_retriever(vectorstore, k=4):
    return vectorstore.as_retriever(search_kwargs={"k": k})