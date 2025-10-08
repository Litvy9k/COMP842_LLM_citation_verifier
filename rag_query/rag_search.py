from langchain_core.documents import Document
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
import json

with open("chatbot-ui/paper.json", "r") as f:
    data = json.load(f)

docs = [
    Document(
        page_content=paper["title"] + "\n" + paper["abstract"],
        metadata={"doi": paper["doi"], "title": paper["title"], "date": paper["date"], "authors": paper["authors"], "journal": paper["journal"], "abstract": paper["abstract"]},
    )
    for paper in data
]