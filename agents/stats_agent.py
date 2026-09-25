"""StatsAgent: guarda estadísticas de cumplimiento sin tocar nada existente.

Se conecta al bus igual que los demás agentes (bajo acoplamiento). Escucha:
  - "exercise_complete": pausa cumplida -> +1 pausa completada, +1 al ejercicio.
  - "postpone_result": si fue aceptado -> +1 pausa postergada.
  - "emergency_unlock_used": +1 desbloqueo de emergencia.

Y responde a "request_stats_today" publicando "stats_today" con el resumen
del día, para que TrayAgent (o cualquier otra UI) lo muestre.
"""

import logging

from agents.base_agent import BaseAgent
from core.messages import Message
from core.stats_store import StatsStore

logger = logging.getLogger(__name__)


class StatsAgent(BaseAgent):
    def __init__(self, bus, store: StatsStore = None):
        super().__init__(
            name="StatsAgent",
            bus=bus,
            topics=[
                "exercise_complete",
                "postpone_result",
                "emergency_unlock_used",
                "request_stats_today",
            ],
        )
        self.store = store or StatsStore()

    def handle_message(self, message: Message) -> None:
        if message.topic == "exercise_complete":
            name = message.payload.get("name", "Ejercicio")
            self.store.add_exercise_completion(name)
            logger.info("Pausa completada: %s", name)

        elif message.topic == "postpone_result":
            if message.payload.get("allowed"):
                self.store.increment("pauses_postponed")
                logger.info("Pausa postergada")

        elif message.topic == "emergency_unlock_used":
            self.store.increment("emergency_unlocks")
            logger.warning("Desbloqueo de emergencia usado")

        elif message.topic == "request_stats_today":
            self.send("stats_today", **self.store.today_summary())
