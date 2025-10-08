from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from local_llm import LocalCausalLM

def build_rag_chain(retriever, model_path):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful academic assistant. Use the provided paper content to answer the question. Cite relevant paper titles and years. Answer concisely and stop when done."),
        # ("human", "{question}\n\nRelevant paper content:\n{context}")
        ("human", "{question}")
    ])

    llm = LocalCausalLM(model_path=model_path)

    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain, llm