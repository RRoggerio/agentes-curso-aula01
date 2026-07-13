# app/agent.py
# Ferramentas e modelo. A base simulada deu lugar ao RAG real.

import os
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from app.rag import get_vector_store
from app.tools_externas import lookup_cep

from app.mcp_client import carregar_tools_mcp

from app.skills_loader import descobrir_skills, resumo_para_prompt

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
# O retriever é criado sob demanda (lazy): assim o serviço sobe no Render
# sem precisar conectar ao banco no momento do import/deploy.
_retriever = None


def _get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = get_vector_store().as_retriever(search_kwargs={"k": 4})
    return _retriever


@tool
def knowledge_search(query: str) -> str:
    """Busca informações sobre políticas e conhecimento do domínio na base
    de conhecimento da empresa. Use para qualquer pergunta sobre regras,
    procedimentos ou informações institucionais."""
    try:
        docs = _get_retriever().invoke(query)
    except Exception as exc:
        return f"Erro ao consultar a base de conhecimento: {exc}"
    if not docs:
        return "Nenhuma informação encontrada na base de conhecimento."
    return "\n\n".join(doc.page_content for doc in docs)


# --- Conjunto de ferramentas e modelo ---
TOOLS = [calculator, knowledge_search, lookup_cep]

SYSTEM_PROMPT = (
    "Você é um assistente objetivo e confiável. "
    "Use 'calculator' para cálculos exatos, 'knowledge_search' para perguntas "
    "sobre políticas e informações institucionais da empresa, e 'lookup_cep' "
    "para consultar endereços a partir de um CEP. "
    "Sempre que existir uma ferramenta adequada à pergunta, use-a e responda "
    "com base no resultado dela; se uma ferramenta falhar, explique. "
    # Restrição de 'fora de escopo', agora sem suprimir tools legítimas:
    "Só afirme que NÃO TEM a informação quando NENHUMA ferramenta disponível "
    "puder respondê-la — nunca invente. Responda em português, de forma concisa."
)


def build_model():
    """Cria o modelo já com as ferramentas vinculadas (tool calling)."""
    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    return model.bind_tools(TOOLS)


# Ferramentas que NÓS escrevemos (Aulas 1-4).
TOOLS = [calculator, knowledge_search, lookup_cep]

# Ferramentas que VÊM de servidores MCP (Aula 9), sem adaptador sob medida.
_mcp_tools = carregar_tools_mcp()
TOOLS = TOOLS + _mcp_tools

# As tools MCP são dinâmicas (cada grupo expõe a sua). Descrevê-las no prompt
# faz o modelo saber QUANDO usá-las; sem isso ele tende a cair no
# knowledge_search e responder "não temos" para dados operacionais (ex.: estoque).
if _mcp_tools:
    _desc_mcp = "\n".join(f"- '{t.name}': {t.description}" for t in _mcp_tools)
    SYSTEM_PROMPT = SYSTEM_PROMPT + (
        "\n\nVocê também tem ferramentas de sistemas integrados da empresa "
        "(via MCP). Prefira-as à base de conhecimento para os dados operacionais "
        "que elas atendem (como estoque):\n" + _desc_mcp
    )
    print(f"[MCP] {len(_mcp_tools)} tool(s) carregada(s): {[t.name for t in _mcp_tools]}")
else:
    print("[MCP] nenhuma tool carregada — verifique o servidor MCP e o requirements.txt.")

# NÍVEL 1: no boot, só os metadados das skills vão ao prompt (poucos tokens).
SKILLS = descobrir_skills("skills")
SYSTEM_PROMPT = SYSTEM_PROMPT + "\n\n" + resumo_para_prompt(SKILLS)
# NÍVEL 2: carregar_skill(SKILLS, nome) traz as instruções completas só
# quando a tarefa exige — mantendo o contexto enxuto.
