"""Definición del mensaje estándar que viaja por el bus del sistema multiagente."""

from dataclasses import dataclass, field
from typing import Any, Dict
import time


@dataclass
class Message:
    """Unidad de comunicación entre agentes.

    topic: nombre del evento (ej. "pause_due", "landmarks", "exercise_complete").
    sender: nombre del agente que publica el mensaje.
    payload: datos asociados al evento.
    timestamp: momento de creación, útil para depuración y métricas.
    """

    topic: str
    sender: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
