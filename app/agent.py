# app/agent.py
# Ferramentas e modelo. A base simulada deu lugar ao RAG real.

import os
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_core.tools.retriever import create_retriever_tool
from langchain_openai import ChatOpenAI

from app.rag import get_vector_store

load_dotenv()


# --- Ferramenta 1: calculadora (mantida) ---
@tool
def calculator(expression: str) -> str:
    """Avalia uma expressão aritmética simples (ex.: '3 * (4 + 2)').
    Use para cálculos exatos em vez de estimar."""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as exc:
        return f"Erro ao calcular: {exc}"


# --- Ferramenta 2: recuperação REAL (RAG) no lugar da base simulada ---
# O retriever busca os trechos mais similares à pergunta no pgvector.
_retriever = get_vector_store().as_retriever(search_kwargs={"k": 4})

knowledge_search = create_retriever_tool(
    _retriever,
    name="knowledge_search",
    description=(
        "Busca informações sobre políticas e conhecimento do domínio na base "
        "de conhecimento da empresa. Use para qualquer pergunta sobre regras, "
        "procedimentos ou informações institucionais."
    ),
)


# --- Conjunto de ferramentas e modelo ---
TOOLS = [calculator, knowledge_search]

SYSTEM_PROMPT = (
    "Você é um assistente objetivo e confiável. "
    "Use 'calculator' para cálculos exatos e 'knowledge_search' para perguntas "
    "sobre políticas e informações da empresa. Responda SEMPRE com base nos "
    "trechos recuperados; se não encontrar, diga que não sabe. Responda em português."
)


def build_model():
    """Cria o modelo já com as ferramentas vinculadas (tool calling)."""
    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    return model.bind_tools(TOOLS)
