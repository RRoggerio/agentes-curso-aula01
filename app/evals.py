# app/evals.py
# Harness de avaliação: roda casos golden contra o agente e calcula uma nota.

from dataclasses import dataclass
from typing import Callable


@dataclass
class EvalCase:
    nome: str
    entrada: str
    # cada checagem: (descrição, função que recebe a resposta e devolve bool)
    checagens: list


# --- Helpers de checagem (componíveis e legíveis) ---
def contains(substr: str) -> Callable[[str], bool]:
    """A resposta DEVE conter o trecho (case-insensitive)."""
    return lambda resp: substr.lower() in resp.lower()


def not_contains(substr: str) -> Callable[[str], bool]:
    """A resposta NÃO deve conter o trecho (ex.: alucinação conhecida)."""
    return lambda resp: substr.lower() not in resp.lower()


# --- Dataset golden: os cenários mais críticos do SEU agente ---
# Estes são exemplos sobre o domínio de docs/politicas.md; troque pelos seus.
CASOS = [
    EvalCase(
        nome="reembolso_prazo",
        entrada="Qual o prazo para solicitar reembolso?",
        checagens=[
            ("menciona 30 dias", contains("30 dias")),
            ("não inventa garantia vitalícia", not_contains("vitalícia")),
        ],
    ),
    EvalCase(
        nome="fora_de_escopo",
        entrada="Qual a capital da França?",
        checagens=[
            ("admite não ter a informação na base", contains("não")),
        ],
    ),
]

def run_evals(agente: Callable[[str], str], casos=CASOS) -> dict:
    """Roda os casos contra o agente e devolve nota + detalhes.
    'agente' é qualquer função que recebe a entrada e devolve a resposta."""
    total, passou = 0, 0
    detalhes = []

    for caso in casos:
        resposta = agente(caso.entrada)
        resultados_caso = []
        for descricao, checagem in caso.checagens:
            ok = bool(checagem(resposta))
            total += 1
            passou += int(ok)
            resultados_caso.append({"checagem": descricao, "passou": ok})
        detalhes.append({"caso": caso.nome, "resultados": resultados_caso})

    score = round(passou / total * 100, 1) if total else 0.0
    return {"score": score, "passou": passou, "total": total, "detalhes": detalhes}

def agente_do_projeto(entrada: str) -> str:
    """Chama o grafo do agente (Aula 5/6) e devolve o texto da resposta."""
    import asyncio
    import uuid
    from app.graph import graph
    state = {
        "messages": [{"role": "user", "content": entrada}],
        "pending_action": None, "approved": None,
    }
    # thread_id único por caso: cada avaliação é uma conversa isolada.
    config = {"configurable": {"thread_id": f"eval-{uuid.uuid4()}"}}
    # ainvoke: o agente pode usar tools MCP (async-only, Aula 9). O /evals roda
    # numa thread sem event loop, então asyncio.run() executa a coroutine aqui —
    # e mantém a interface síncrona (str -> str) que run_evals espera.
    result = asyncio.run(graph.ainvoke(state, config=config))
    return result["messages"][-1].content
