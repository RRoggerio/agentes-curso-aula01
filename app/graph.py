# app/graph.py
# Grafo do agente (Aula 4) + fluxo de human-in-the-loop (Aula 5).
#
# Dois grafos convivem:
#  - graph: o agente conversacional com ferramentas e memória (Aulas 2-4).
#  - approval_graph: um fluxo com aprovação humana (propor -> aprovação -> executar),
#    que demonstra o human-in-the-loop com interrupt() e Command(resume=...).

import os
from typing import Annotated, Optional
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt

from app.agent import TOOLS, SYSTEM_PROMPT, build_model


# --- Estado: mensagens (Aulas 2-4) + campos de aprovação (Aula 5) ---
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    pending_action: Optional[str]   # a ação crítica proposta, aguardando decisão
    approved: Optional[bool]        # a decisão humana, preenchida na retomada


model = build_model()


def model_node(state: AgentState) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
    return {"messages": [model.invoke(messages)]}


tool_node = ToolNode(TOOLS)


def build_checkpointer():
    """Em produção, persiste no PostgreSQL; em dev, guarda em memória."""
    db_url = os.getenv("DATABASE_URL")
    if db_url and os.getenv("USE_PG_MEMORY") == "1":
        from langgraph.checkpoint.postgres import PostgresSaver
        return PostgresSaver.from_conn_string(db_url)
    return InMemorySaver()


# Um único checkpointer sustenta memória (graph) E pausa/retomada (approval_graph).
_checkpointer = build_checkpointer()


# --- Grafo do agente conversacional (Aulas 2-4) ---
def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("model", model_node)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", tools_condition)
    builder.add_edge("tools", "model")
    return builder.compile(checkpointer=_checkpointer)


graph = build_graph()


# ===================== HUMAN-IN-THE-LOOP (Aula 5) =====================

def propor_acao_node(state: AgentState) -> dict:
    """Aqui o agente decide a ação crítica. No exemplo, fixamos uma; no seu
    projeto, derive de uma ferramenta ou da decisão do modelo."""
    acao = "Registrar uma transferência de R$ 500 para a conta destino."
    return {
        "pending_action": acao,
        "messages": [{"role": "assistant", "content": f"Proponho: {acao}"}],
    }


def aprovacao_humana_node(state: AgentState) -> dict:
    """Pausa o grafo e espera a decisão humana sobre a ação proposta."""
    # interrupt() congela o grafo e devolve este payload ao chamador.
    decisao = interrupt({
        "acao_proposta": state["pending_action"],
        "pergunta": "Você aprova esta ação? Responda 'aprovar' ou 'rejeitar'.",
    })
    # Quando retomado, 'decisao' recebe o valor passado em Command(resume=...).
    return {"approved": decisao == "aprovar"}


def executar_acao_node(state: AgentState) -> dict:
    """Executa a ação somente se aprovada; caso contrário, cancela."""
    if state.get("approved"):
        # Aqui entraria a chamada real (API, banco). No exemplo, confirmamos.
        msg = f"Ação executada: {state['pending_action']}"
    else:
        msg = "Ação cancelada pela revisão humana."
    return {"messages": [{"role": "assistant", "content": msg}], "pending_action": None}


def build_approval_graph():
    """Fluxo com aprovação humana: propor -> aprovação (pausa) -> executar."""
    builder = StateGraph(AgentState)
    builder.add_node("propor", propor_acao_node)
    builder.add_node("aprovacao", aprovacao_humana_node)
    builder.add_node("executar", executar_acao_node)
    builder.add_edge(START, "propor")
    builder.add_edge("propor", "aprovacao")
    builder.add_edge("aprovacao", "executar")
    builder.add_edge("executar", END)
    # O MESMO checkpointer sustenta a pausa/retomada.
    return builder.compile(checkpointer=_checkpointer)


approval_graph = build_approval_graph()
