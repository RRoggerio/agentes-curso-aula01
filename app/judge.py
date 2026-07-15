# app/judge.py
# LLM-as-judge: um modelo forte pontua a resposta segundo uma rubrica.

import json
from langchain_openai import ChatOpenAI

# Rubrica explícita + pedir para JUSTIFICAR ANTES da nota (mitiga vieses).
JUDGE_PROMPT = """Você avalia a resposta de um agente segundo o critério abaixo.

Critério: {criterio}
Pergunta do usuário: {pergunta}
Resposta do agente: {resposta}

Pense brevemente e então devolva APENAS um JSON válido, sem texto ao redor,
neste formato: {{"justificativa": "<uma frase>", "nota": <inteiro de 1 a 5>}}"""


def parse_judge(texto: str) -> dict:
    """Extrai o JSON da resposta do juiz de forma robusta."""
    inicio = texto.find("{")
    fim = texto.rfind("}") + 1
    return json.loads(texto[inicio:fim])


def judge(pergunta: str, resposta: str, criterio: str) -> dict:
    """Devolve {'nota': 1-5, 'justificativa': str} para uma resposta."""
    # temperature=0 para avaliação mais estável entre execuções.
    modelo = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = JUDGE_PROMPT.format(criterio=criterio, pergunta=pergunta, resposta=resposta)
    saida = modelo.invoke(prompt).content
    try:
        return parse_judge(saida)
    except Exception:
        # Se o juiz não devolver JSON válido, falha de forma segura.
        return {"nota": None, "justificativa": f"resposta não-parseável: {saida[:80]}"}
