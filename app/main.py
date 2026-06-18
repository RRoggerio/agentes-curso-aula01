# app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from langfuse.langchain import CallbackHandler

from app.graph import graph

langfuse_handler = CallbackHandler()
app = FastAPI(title="Agente de IA — Aula 3")


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"   # identifica a conversa (memória)


class ChatResponse(BaseModel):
    answer: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    state = {"messages": [{"role": "user", "content": req.message}]}
    # thread_id habilita a memória; callbacks habilitam a observabilidade.
    config = {
        "configurable": {"thread_id": req.thread_id},
        "callbacks": [langfuse_handler],
    }
    result = graph.invoke(state, config=config)
    return ChatResponse(answer=result["messages"][-1].content)
