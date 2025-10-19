import arxiv
import json

# Neural nerwork, semiconductor, supervised leaning, blockchain, language model

with open("chatbot-ui/arxiv_ids.txt", "r", encoding="utf-8") as f:
    arxiv_ids = [line.strip() for line in f if line.strip()]
print(arxiv_ids)

def fetch_arxiv_metadata(arxiv_id):
    paper = next(arxiv.Search(arxiv_id).results())
    doi = paper.doi or f'arXiv:{arxiv_id}'
    title = paper.title
    authors = ', '.join([author.name for author in paper.authors])
    dete = paper.published.strftime('%Y-%m-%d')
    abstract = paper.summary.replace('\n', ' ')
    journal_ref = paper.journal_ref or 'N/A'
    return {
        'doi': doi,
        'title': title,
        'authors': authors,
        'date': dete,
        'abstract': abstract,
        'journal': journal_ref
    }
    
data = []
for item in arxiv_ids:
    metadata = fetch_arxiv_metadata(item)
    data.append(metadata)

with open("chatbot-ui/paper.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)