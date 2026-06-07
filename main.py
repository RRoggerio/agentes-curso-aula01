# app/main.py
# Expõe o agente por uma API FastAPI e instrumenta cada execução no Langfuse.

from fastapi import FastAPI
from pydantic import BaseModel
from langfuse.langchain import CallbackHandler

from app.agent import agent

# O CallbackHandler lê as chaves LANGFUSE_* do ambiente automaticamente.
langfuse_handler = CallbackHandler()

app = FastAPI(title="Agente de IA — Aula 1")


# --- Contrato da requisição e da resposta ---
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str


@app.get("/health")
def health():
    """Endpoint de saúde — usado pelo Render para checar se o serviço está no ar."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Recebe uma mensagem, executa o agente e devolve a resposta final."""
    # Monta o estado inicial no formato de mensagens esperado pelo agente.
    state = {"messages": [{"role": "user", "content": req.message}]}

    # O callback do Langfuse captura toda a execução (raciocínio, tools, tokens).
    result = agent.invoke(
        state,
        config={"callbacks": [langfuse_handler]},
    )

    # A última mensagem do estado é a resposta final do agente.
    final_message = result["messages"][-1]
    return ChatResponse(answer=final_message.content)
