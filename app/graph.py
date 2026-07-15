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
    product: Optional[str]          # contexto do produto (Aula 1), layerado no prompt


model = build_model()


def model_node(state: AgentState) -> dict:
    # O contexto do produto (Aula 1) é LAYERADO sobre o system prompt — nunca o
    # substitui, senão o agente perde as instruções das tools e das skills e o
    # RAG deixa de ser usado. Ele entra DEPOIS, como enquadramento do domínio.
    system = SYSTEM_PROMPT
    produto = state.get("product")
    if produto:
        system = (
            SYSTEM_PROMPT
            + "\n\n--- Contexto do produto (definido pelo usuário) ---\n"
            + produto
        )
    messages = [{"role": "system", "content": system}] + state["messages"]
    return {"messages": [model.invoke(messages)]}


tool_node = ToolNode(TOOLS)


def build_checkpointer():
    """Em produção, persiste no PostgreSQL; em dev, guarda em memória."""
    db_url = os.getenv("DATABASE_URL")
    if db_url and os.getenv("USE_PG_MEMORY") == "1":
        from psycopg import Connection
        from psycopg.rows import dict_row
        from langgraph.checkpoint.postgres import PostgresSaver

        # O RAG (SQLAlchemy) usa o dialeto 'postgresql+psycopg://'; o psycopg
        # puro do checkpointer NÃO aceita esse esquema — normalizamos aqui.
        conn_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
        if conn_url.startswith("postgres://"):
            conn_url = conn_url.replace("postgres://", "postgresql://", 1)

        # PostgresSaver.from_conn_string() devolve um CONTEXT MANAGER (fecha a
        # conexão ao sair do 'with'). Para manter o saver vivo pela vida do
        # serviço, abrimos a conexão explicitamente e a entregamos ao saver.
        conn = Connection.connect(
            conn_url, autocommit=True, prepare_threshold=0, row_factory=dict_row
        )
        saver = PostgresSaver(conn)
        saver.setup()  # cria as tabelas do checkpointer na primeira execução
        return saver
    return InMemorySaver()


# UM único checkpointer sustenta memória (graph), pausa/retomada
# (approval_graph) E o time multiagente (mas.py importa este mesmo objeto).
_checkpointer = build_checkpointer()
checkpointer = _checkpointer  # nome público para os demais módulos


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
