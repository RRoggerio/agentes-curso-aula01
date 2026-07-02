# app/metrics.py
# Métrica de NEGÓCIO: conta eventos de valor gerados pelo agente.
# Simples de propósito — o primeiro tijolo da medição de valor.

from collections import defaultdict
from threading import Lock

# Contador em memória. Em produção, isto iria para um banco ou serviço
# de métricas; aqui basta para começar a medir e criar o hábito.
_business_metrics = defaultdict(int)
_lock = Lock()


def record_event(name: str, amount: int = 1) -> None:
    """Registra um evento de valor (ex.: 'tarefas_concluidas')."""
    with _lock:
        _business_metrics[name] += amount


def get_metrics() -> dict:
    """Devolve um instantâneo das métricas de negócio acumuladas."""
    with _lock:
        return dict(_business_metrics)
