# app/main.py
# API FastAPI: agente conversacional (/chat) + fluxo human-in-the-loop (/action, /resume).

from fastapi import FastAPI
from pydantic import BaseModel
from langfuse.langchain import CallbackHandler
from langgraph.types import Command

from app.graph import graph, approval_graph
from app.metrics import record_event, get_metrics
from app.mas import team_graph

langfuse_handler = CallbackHandler()
app = FastAPI(title="Agente de IA — Aula 5")


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


class ActionRequest(BaseModel):
    message: str
    thread_id: str = "default"


class ResumeRequest(BaseModel):
    decision: str           # "aprovar" ou "rejeitar"
    thread_id: str = "default"


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}, "callbacks": [langfuse_handler]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    """Agente conversacional com ferramentas e memória (Aulas 2-4)."""
    state = {"messages": [{"role": "user", "content": req.message}],
             "pending_action": None, "approved": None}
    result = graph.invoke(state, config=_config(req.thread_id))
    # Evento de valor: uma tarefa foi concluída pelo agente.
    record_event("tarefas_concluidas")
    return {"status": "concluido", "answer": result["messages"][-1].content}


@app.post("/action")
def action(req: ActionRequest):
    """Dispara o fluxo com aprovação humana. Se pausar, devolve a ação proposta."""
    state = {"messages": [{"role": "user", "content": req.message}],
             "pending_action": None, "approved": None}
    approval_graph.invoke(state, config=_config(req.thread_id))

    snapshot = approval_graph.get_state(_config(req.thread_id))
    if snapshot.interrupts:
        payload = snapshot.interrupts[0].value
        return {
            "status": "aguardando_aprovacao",
            "acao_proposta": payload.get("acao_proposta"),
            "pergunta": payload.get("pergunta"),
        }
    return {"status": "concluido"}


@app.post("/resume")
def resume(req: ResumeRequest):
    """Retoma o fluxo pausado com a decisão humana (aprovar/rejeitar)."""
    # Command(resume=...) entrega o valor ao interrupt() que estava esperando.
    result = approval_graph.invoke(Command(resume=req.decision), config=_config(req.thread_id))
    # Evento de valor (negócio): conta aprovações e rejeições separadamente.
    if req.decision == "aprovar":
        record_event("acoes_aprovadas")
    else:
        record_event("acoes_rejeitadas")
    return {"status": "concluido", "answer": result["messages"][-1].content}


@app.get("/metrics")
def metrics():
    """Métricas de NEGÓCIO acumuladas (complementa o Langfuse, que é técnico)."""
    return {"business_metrics": get_metrics()}


class TeamRequest(BaseModel):
    tarefa: str
    thread_id: str = "default"


@app.post("/team")
def team(req: TeamRequest):
    """Executa o time multiagente (supervisor + pesquisador + redator)."""
    state = {
        "messages": [{"role": "user", "content": req.tarefa}],
        "tarefa": req.tarefa,
        "pesquisa": "", "resposta": "",
        "pesquisa_feita": False, "redacao_feita": False,
    }
    config = {"configurable": {"thread_id": req.thread_id}, "callbacks": [langfuse_handler]}
    result = team_graph.invoke(state, config=config)
    return {"resposta": result["resposta"], "etapas": [m.content for m in result["messages"]]}
