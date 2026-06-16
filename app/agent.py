# app/agent.py
# Ferramentas e modelo do agente. O grafo (graph.py) consome o que está aqui.

import os
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI
import unicodedata

load_dotenv()


# --- Ferramenta 1: calculadora (da Aula 1) ---
@tool
def calculator(expression: str) -> str:
    """Avalia uma expressão aritmética simples (ex.: '3 * (4 + 2)').
    Use para cálculos exatos em vez de estimar."""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as exc:
        return f"Erro ao calcular: {exc}"


# --- Ferramenta 2: base de conhecimento SIMULADA ---
# Placeholder em memória. Na Aula 3 isto vira RAG real com PostgreSQL + pgvector.
KNOWLEDGE_BASE = {
    "horario de atendimento": "O atendimento funciona de segunda a sexta, das 9h às 18h.",
    "politica de reembolso": "Reembolsos podem ser solicitados em até 30 dias após a compra.",
    "prazo de entrega": "O prazo médio de entrega é de 5 a 7 dias úteis.",
}

def _normalizar(texto: str) -> str:
    # remove acentos e baixa a caixa, para comparar de forma robusta
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))

@tool
def knowledge_lookup(topic: str) -> str:
    """Consulta a base de conhecimento interna sobre políticas e informações
    da empresa (horário, reembolso, prazo de entrega). Use quando a pergunta
    for sobre regras ou informações institucionais."""
    topic_norm = _normalizar(topic)
    for key, value in KNOWLEDGE_BASE.items():
        key_norm = _normalizar(key)
        if key_norm in topic_norm or topic_norm in key_norm:
            return value
    return "Não encontrei essa informação na base de conhecimento."


# --- Conjunto de ferramentas e modelo ---
TOOLS = [calculator, knowledge_lookup]

SYSTEM_PROMPT = (
    "Você é um assistente objetivo e confiável. "
    "Use 'calculator' para cálculos exatos e 'knowledge_lookup' para perguntas "
    "sobre políticas e informações da empresa. Responda em português, de forma concisa."
)

def build_model():
    """Cria o modelo já com as ferramentas vinculadas (tool calling)."""
    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    # bind_tools informa ao modelo quais ferramentas ele pode chamar.
    return model.bind_tools(TOOLS)