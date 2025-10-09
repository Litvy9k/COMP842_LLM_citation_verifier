from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from local_llm import LocalCausalLM

def build_rag_chain(model_path: str):

    SYSTEM = (
        "You are a helpful academic assistant.\n"
        "Use ONLY the provided SOURCES to answer.\n"
        "Write in clear, natural academic English.\n"
        "Do NOT use citation markers like [#paper_id] and do NOT include a References section.\n"
        "Mention exactly ONE paper (the most relevant one) by its title, year, and author(s) in plain text.\n"
        "If the question cannot be answered from the SOURCES, reply exactly: INSUFFICIENT_EVIDENCE.\n"
        "Be concise and factual."
    )

    USER = (
        "Question: {question}\n\n"
        "SOURCES:\n{sources}\n\n"
        "Write 1 concise paragraph summarizing the SINGLE most relevant paper from SOURCES. "
        "Include its title, year, and author(s) naturally in the text. "
        "Do NOT mention other sources. Do NOT add a references list."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM),
        ("user", USER),
    ])

    llm = LocalCausalLM(model_path=model_path)

    def _call(d: Dict[str, Any]) -> str:
        cpv = prompt.invoke(d)
        mt = d.get("max_tokens", llm.max_tokens)
        if isinstance(mt, dict):
            mt = mt.get("max_tokens", llm.max_tokens)
        try:
            mt = int(mt)
        except Exception:
            mt = llm.max_tokens
        return llm.invoke(cpv, max_tokens=mt)

    chain = RunnableLambda(_call) | StrOutputParser()
    return chain, llm