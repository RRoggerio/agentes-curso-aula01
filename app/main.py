# app/main.py
# API FastAPI que expõe o grafo do agente, instrumentado no Langfuse.

from fastapi import FastAPI
from pydantic import BaseModel
from langfuse.langchain import CallbackHandler

from app.graph import graph   # agora importamos o GRAFO, não o agente

langfuse_handler = CallbackHandler()

app = FastAPI(title="Agente de IA — Aula 2")


class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Executa o grafo do agente e devolve a resposta final."""
    state = {"messages": [{"role": "user", "content": req.message}]}

    # O callback do Langfuse captura TODO o grafo: cada nó, cada ferramenta.
    result = graph.invoke(state, config={"callbacks": [langfuse_handler]})

    final_message = result["messages"][-1]
    return ChatResponse(answer=final_message.content)