# app/main.py
# API FastAPI: agente conversacional (/chat) + fluxo human-in-the-loop (/action, /resume).

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langfuse.langchain import CallbackHandler
from langgraph.types import Command

from app.graph import graph, approval_graph
from app.metrics import record_event, get_metrics
from app.mas import team_graph

from app.evals import run_evals, agente_do_projeto

from app.governance import guardrail_entrada, guardrail_saida, audit_log

langfuse_handler = CallbackHandler()
app = FastAPI(title="Agentes de IA — Projeto do Curso (Aula 10 · Final)")


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    product: str = ""       # descrição do produto (Aula 1), layerada no system prompt


class ActionRequest(BaseModel):
    message: str
    thread_id: str = "default"


class ResumeRequest(BaseModel):
    decision: str           # "aprovar" ou "rejeitar"
    thread_id: str = "default"


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}, "callbacks": [langfuse_handler]}


@app.get("/")
def index():
    """Serve a página interativa do agente. Mesma origem da API: sem CORS,
    um único container, uma única URL no Render."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


def _extrair_passos(mensagens) -> list:
    """Expõe o que o agente FEZ: quais ferramentas chamou e o que voltou.
    É isto que faz a interface parecer um agente, e não um chatbot — o aluno
    vê o raciocínio-em-ação (RAG, tools, skills) por trás da resposta final."""
    passos = []
    for m in mensagens:
        for tc in (getattr(m, "tool_calls", None) or []):
            passos.append({"tipo": "chamada", "tool": tc.get("name", "?"),
                           "args": tc.get("args", {})})
        if m.__class__.__name__ == "ToolMessage":
            passos.append({"tipo": "resultado", "tool": getattr(m, "name", "?"),
                           "conteudo": guardrail_saida(str(m.content))[:500]})
    return passos


@app.post("/action")
def action(req: ActionRequest):
    """Dispara o fluxo com aprovação humana. Se pausar, devolve a ação proposta."""
    state = {"messages": [{"role": "user", "content": req.message}],
             "pending_action": None, "approved": None}
    result = approval_graph.invoke(state, config=_config(req.thread_id))

    snapshot = approval_graph.get_state(_config(req.thread_id))
    if snapshot.interrupts:
        payload = snapshot.interrupts[0].value
        return {
            "status": "aguardando_aprovacao",
            "acao_proposta": payload.get("acao_proposta"),
            "pergunta": payload.get("pergunta"),
        }
    # Fluxo terminou sem pausar: devolve a resposta final.
    return {"status": "concluido", "answer": result["messages"][-1].content}


@app.post("/resume")
def resume(req: ResumeRequest):
    """Retoma o fluxo pausado com a decisão humana (aprovar/rejeitar)."""
    # Guarda: só faz sentido retomar se HÁ uma pausa pendente neste thread_id.
    snapshot = approval_graph.get_state(_config(req.thread_id))
    if not snapshot.interrupts:
        return {"status": "erro",
                "detail": "Nenhuma aprovação pendente para este thread_id. "
                          "Dispare o fluxo em /action primeiro."}
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


@app.get("/evals")
def evals(judge: bool = False):
    """Roda o harness de avaliação contra o agente e devolve a nota.
    Com ?judge=true, adiciona a nota 1-5 do LLM-as-judge a cada caso."""
    return run_evals(agente_do_projeto, com_judge=judge)


@app.post("/chat")
async def chat(req: ChatRequest):
    """Agente conversacional (Aulas 2-4/9) com a CAMADA DE GOVERNANÇA:
    guardrail de entrada, execução do agente, guardrail de saída e auditoria."""
    # 1) Guardrail de ENTRADA — barra o proibido antes de gastar uma chamada.
    permitido, motivo = guardrail_entrada(req.message)
    if not permitido:
        audit_log({"thread_id": req.thread_id, "acao": "chat",
                   "permitido": False, "motivo": motivo})
        return {"status": "bloqueado", "answer": "Não posso ajudar com esse pedido."}

    # 2) O agente age (igual à Aula 9), agora enquadrado pelo produto do aluno.
    state = {"messages": [{"role": "user", "content": req.message}],
             "pending_action": None, "approved": None,
             "product": req.product}
    # ainvoke (async): as tools vindas do MCP são async-only; um invoke()
    # síncrono levantaria 'StructuredTool does not support sync invocation'.
    result = await graph.ainvoke(state, config=_config(req.thread_id))
    resposta = result["messages"][-1].content

    # 3) Guardrail de SAÍDA — sanitiza antes de devolver.
    resposta = guardrail_saida(resposta)

    # 4) Auditoria do que foi permitido e concluído.
    record_event("tarefas_concluidas")
    audit_log({"thread_id": req.thread_id, "acao": "chat", "permitido": True})
    return {"status": "concluido", "answer": resposta,
            "steps": _extrair_passos(result["messages"])}
