# app/graph.py
# Grafo do agente, agora COM memória (checkpointer).

import os
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver

from app.agent import TOOLS, SYSTEM_PROMPT, build_model


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


model = build_model()


def model_node(state: AgentState) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
    return {"messages": [model.invoke(messages)]}


tool_node = ToolNode(TOOLS)


def build_checkpointer():
    """Em produção, persiste no PostgreSQL; em dev, guarda em memória."""
    db_url = os.getenv("DATABASE_URL")
    if db_url and os.getenv("USE_PG_MEMORY") == "1":
        # Persistência real no Postgres (requer setup() na 1ª vez).
        from langgraph.checkpoint.postgres import PostgresSaver
        cp = PostgresSaver.from_conn_string(db_url)
        return cp
    # Padrão de desenvolvimento: memória do processo.
    return InMemorySaver()


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("model", model_node)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", tools_condition)
    builder.add_edge("tools", "model")
    # A memória entra aqui: compile com o checkpointer.
    return builder.compile(checkpointer=build_checkpointer())


graph = build_graph()
