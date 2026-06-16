# app/graph.py
# Orquestração explícita do agente como um StateGraph do LangGraph.

from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent import TOOLS, SYSTEM_PROMPT, build_model


# --- 1. O ESTADO ---------------------------------------------------------
# O que trafega entre os nós. 'add_messages' é um reducer: novas mensagens
# são ACRESCENTADAS à lista (em vez de sobrescrevê-la).
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# Modelo com ferramentas vinculadas (criado uma vez).
model = build_model()


# --- 2. OS NÓS -----------------------------------------------------------
def model_node(state: AgentState) -> dict:
    """Nó do modelo: injeta o system prompt e chama o LLM com o histórico."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
    response = model.invoke(messages)
    # Retorna a resposta; o reducer add_messages a acrescenta ao estado.
    return {"messages": [response]}


# Nó de ferramentas pronto: executa qualquer ferramenta que o modelo pediu.
tool_node = ToolNode(TOOLS)


# --- 3. O GRAFO ----------------------------------------------------------
def build_graph():
    """Monta e compila o grafo do agente."""
    builder = StateGraph(AgentState)

    # Registra os nós
    builder.add_node("model", model_node)
    builder.add_node("tools", tool_node)

    # Arestas: começa no model
    builder.add_edge(START, "model")

    # Aresta CONDICIONAL: se o model pediu ferramenta -> 'tools'; senão -> END.
    # tools_condition já implementa essa decisão padrão.
    builder.add_conditional_edges("model", tools_condition)

    # Depois de executar a ferramenta, volta ao model para continuar o raciocínio.
    builder.add_edge("tools", "model")

    return builder.compile()


# Instância única do grafo, reutilizada pela API.
graph = build_graph()