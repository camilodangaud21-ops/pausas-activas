"""SchedulerAgent: lleva la cuenta del tiempo y dispara "pause_due" cada
`interval_minutes`. Reinicia su reloj cuando la configuración cambia o
cuando una pausa se resuelve (usuario completó el ejercicio)."""

import queue
import time

from agents.base_agent import BaseAgent
from core.messages import Message


class SchedulerAgent(BaseAgent):
    def __init__(self, bus, interval_minutes: float):
        super().__init__(name="SchedulerAgent", bus=bus,
                          topics=["config_updated", "pause_resolved"])
        self.interval_seconds = interval_minutes * 60
        self._next_trigger = time.time() + self.interval_seconds

    def handle_message(self, message: Message) -> None:
        if message.topic == "config_updated":
            minutes = message.payload.get("interval_minutes")
            if minutes:
                self.interval_seconds = minutes * 60
                self._next_trigger = time.time() + self.interval_seconds
        elif message.topic == "pause_resolved":
            self._next_trigger = time.time() + self.interval_seconds

    def run(self) -> None:
        # Bucle propio: además de atender mensajes, vigila el reloj cada segundo.
        while self._running.is_set():
            try:
                message = self.inbox.get(timeout=1.0)
                self.handle_message(message)
            except queue.Empty:
                pass

            remaining = self._next_trigger - time.time()
            self.send("tick", remaining_seconds=max(0.0, remaining))
            if remaining <= 0:
                self.send("pause_due")
                self._next_trigger = time.time() + self.interval_seconds
