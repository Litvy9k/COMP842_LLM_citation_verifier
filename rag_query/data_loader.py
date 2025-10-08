import json
from langchain_core.documents import Document

def load_documents(json_path: str) -> list[Document]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = [
        Document(
            page_content=paper["title"] + "\n" + paper["abstract"],
            metadata={"title": paper["title"], 
                      "date": paper.get("date"),
                      "authors": paper.get("authors"), 
                      "journal": paper.get("journal"), 
                      "abstract": paper.get("abstract"),
                      "doi": paper.get("doi")},
        )
        for paper in data
    ]
    return docs