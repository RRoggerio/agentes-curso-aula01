from fastapi import FastAPI
from pydantic import BaseModel
from langfuse.langchain import CallbackHandler
from langgraph.types import Command

from app.graph import graph

langfuse_handler = CallbackHandler()
app = FastAPI(title="Agente de IA — Aula 5")


class ChatRequest(BaseModel):
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
    """Executa o grafo. Se ele pausar numa aprovação, devolve a ação proposta."""
    state = {
        "messages": [{"role": "user", "content": req.message}],
        "pending_action": None, "approved": None,
    }
    result = graph.invoke(state, config=_config(req.thread_id))

    # Se o grafo pausou, há uma interrupção pendente no estado.
    snapshot = graph.get_state(_config(req.thread_id))
    if snapshot.interrupts:
        payload = snapshot.interrupts[0].value
        return {
            "status": "aguardando_aprovacao",
            "acao_proposta": payload.get("acao_proposta"),
            "pergunta": payload.get("pergunta"),
        }

    # Caso não tenha pausado, devolve a resposta final normalmente.
    return {"status": "concluido", "answer": result["messages"][-1].content}


@app.post("/resume")
def resume(req: ResumeRequest):
    """Retoma o grafo pausado com a decisão humana."""
    # Command(resume=...) entrega o valor ao interrupt() que estava esperando.
    result = graph.invoke(Command(resume=req.decision), config=_config(req.thread_id))
    return {"status": "concluido", "answer": result["messages"][-1].content}
