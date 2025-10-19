import spacy

nlp = spacy.load("en_core_web_sm")

STOP_PHRASES = [
    "find me", "show me", "tell me", "i want", "give me",
    "a paper about", "papers about", "papers on", "related to",
    "that discuss", "which discuss", "that talk about", "which talk about",
]

STOPWORDS = {
    "paper", "papers", "study", "studies", "research", "article", "articles",
    "about", "on", "of", "for", "related", "to", "please", "find", "show",
    "me", "give", "that", "which", "discuss", "talk", "describe"
}

def normalize_query_nlp(q: str) -> str:
    q = q.strip().lower()

    for phrase in STOP_PHRASES:
        if q.startswith(phrase):
            q = q.replace(phrase, "").strip()

    doc = nlp(q)

    key_terms = []
    for chunk in doc.noun_chunks:
        words = [t.lemma_ for t in chunk if t.text not in STOPWORDS]
        if words:
            key_terms.append(" ".join(words))

    if not key_terms:
        key_terms = [t.lemma_ for t in doc if not t.is_stop and t.pos_ in {"NOUN", "PROPN", "ADJ"}]

    normalized = " ".join(dict.fromkeys(key_terms))
    return normalized or q