# app/mas.py
# Sistema multiagente: um supervisor coordena dois trabalhadores
# especializados, comunicando-se por um estado compartilhado.

from typing import Annotated, Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.types import Command

from app.graph import build_checkpointer

class MASState(TypedDict):
    # --- dados ---
    messages: Annotated[list, add_messages]
    tarefa: str          # o pedido original do usuário
    pesquisa: str        # escrito pelo pesquisador, lido pelo redator
    resposta: str        # escrito pelo redator (saída final)
    # --- controle (evita o loop infinito) ---
    pesquisa_feita: bool
    redacao_feita: bool

def pesquisador_node(state: MASState) -> Command[Literal["supervisor"]]:
    """Trabalhador 1: busca informação sobre a tarefa.
    No seu projeto, aqui entraria o RAG (Aula 3) ou uma ferramenta (Aula 4)."""
    tarefa = state["tarefa"]
    # Exemplo didático; troque por uma busca real (retriever/ferramenta).
    achado = f"informações coletadas sobre: {tarefa}"
    return Command(
        goto="supervisor",
        update={
            "pesquisa": achado,
            "pesquisa_feita": True,
            "messages": [{"role": "assistant", "content": f"[pesquisador] {achado}"}],
        },
    )


def redator_node(state: MASState) -> Command[Literal["supervisor"]]:
    """Trabalhador 2: redige a resposta final a partir da pesquisa.
    Lê 'pesquisa' do estado — este é o handoff via estado compartilhado."""
    pesquisa = state["pesquisa"]
    texto = f"Resposta final, fundamentada em: {pesquisa}"
    return Command(
        goto="supervisor",
        update={
            "resposta": texto,
            "redacao_feita": True,
            "messages": [{"role": "assistant", "content": f"[redator] {texto}"}],
        },
    )

def supervisor_node(
    state: MASState,
) -> Command[Literal["pesquisador", "redator", "__end__"]]:
    """Decide o próximo passo OLHANDO O QUE JÁ FOI FEITO (não a última fala).
    Plano: pesquisar -> redigir -> terminar."""
    if not state.get("pesquisa_feita"):
        return Command(goto="pesquisador")
    if not state.get("redacao_feita"):
        return Command(goto="redator")
    # Ambas as etapas concluídas: encerra o fluxo do time.
    return Command(goto="__end__")

def build_team_graph():
    builder = StateGraph(MASState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("pesquisador", pesquisador_node)
    builder.add_node("redator", redator_node)

    # O time sempre começa pelo supervisor; o resto é roteamento dinâmico.
    builder.add_edge(START, "supervisor")

    return builder.compile(checkpointer=build_checkpointer())


team_graph = build_team_graph()
