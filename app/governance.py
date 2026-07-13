# app/governance.py
# Camada de governança: guardrails (bordas) + trilha de auditoria.
# Só biblioteca padrão — governança básica é disciplina, não ferramenta.

import re
import json
import logging
from datetime import datetime, timezone

# --- Guardrail de ENTRADA ---
# Termos que indicam pedido fora de política. Ajuste à sua realidade.
BLOCKLIST = ["senha", "cartão de crédito", "dados pessoais de terceiros"]


def guardrail_entrada(texto: str):
    """Retorna (permitido: bool, motivo: str|None). Roda ANTES do modelo."""
    baixo = texto.lower()
    for termo in BLOCKLIST:
        if termo in baixo:
            return False, f"pedido bloqueado: contém '{termo}'"
    return True, None


# --- Guardrail de SAÍDA ---
# Remove o que parece um segredo (ex.: chave de API) antes de responder.
_SEGREDO = re.compile(r"sk-[A-Za-z0-9]{8,}")


def guardrail_saida(texto: str) -> str:
    """Sanitiza a resposta. Roda ANTES de devolver ao usuário."""
    return _SEGREDO.sub("[REDACTED]", texto)

# Logger dedicado de auditoria (separado dos logs técnicos).
_audit = logging.getLogger("auditoria")
_audit.setLevel(logging.INFO)
if not _audit.handlers:
    _audit.addHandler(logging.StreamHandler())


def audit_log(evento: dict) -> str:
    """Registra um evento de auditoria estruturado (JSON por linha).
    Ex.: audit_log({'thread_id': 't1', 'acao': 'chat', 'permitido': True})."""
    registro = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **evento,
    }
    linha = json.dumps(registro, ensure_ascii=False)
    _audit.info(linha)   # em produção: enviar a um destino durável (banco, SIEM)
    return linha
