from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from local_llm import LocalCausalLM


def build_rag_chain(model_path: str):
    """
    精简版链：不做检索，只吃外部传入的：
      - question: str
      - sources: str  （已格式化好的 SOURCES 文本）
      - allowed_ids: List[str]
      - max_tokens: int
    """

    SYSTEM = (
        "You are a citation-faithful academic assistant.\n"
        "- Use ONLY the SOURCES.\n"
        "- Allowed citation ids: {allowed_ids}\n"
        "- Every factual sentence must end with [#paper_id].\n"
        "- Never invent ids. The literal token [#paper_id] is FORBIDDEN unless replaced by a real id from Allowed ids.\n"
        "- If evidence is missing in SOURCES, reply exactly: INSUFFICIENT_EVIDENCE.\n"
        "- Be concise."
    )

    USER = (
        "Question: {question}\n\n"
        "SOURCES:\n{sources}\n\n"
        "Write 1–3 concise paragraphs.\n"
        "Place [#paper_id] immediately after each factual sentence.\n"
        "End with a short 'References' section mapping [#paper_id] -> Title (Year), DOI."
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