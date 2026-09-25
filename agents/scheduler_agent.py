"""SchedulerAgent: lleva la cuenta del tiempo y dispara "pause_due" cada
`interval_minutes`. Reinicia su reloj cuando la configuración cambia o
cuando una pausa se resuelve (usuario completó el ejercicio).

Mejoras sobre la versión original:
  - Aviso previo ("pause_warning") `WARNING_SECONDS` antes del bloqueo, para
    no cortar al usuario a media frase.
  - Posponer limitado: máximo `MAX_POSTPONES_PER_DAY` veces al día, cada una
    corre el reloj `POSTPONE_MINUTES` minutos. El contador persiste en un
    JSON simple y se reinicia solo (por fecha).
  - Pausar/reanudar el programa completo (ej. antes de una videollamada),
    vía el topic "set_enabled". Mientras está deshabilitado no dispara
    "pause_due" ni "pause_warning", pero sigue emitiendo "tick".
"""

import json
import logging
import os
import queue
import time
from datetime import date

from agents.base_agent import BaseAgent
from core.messages import Message

logger = logging.getLogger(__name__)

WARNING_SECONDS = 20
MAX_POSTPONES_PER_DAY = 2
POSTPONE_MINUTES = 10
_POSTPONES_PATH = os.path.join("data", "postpones.json")


class SchedulerAgent(BaseAgent):
    def __init__(self, bus, interval_minutes: float):
        super().__init__(
            name="SchedulerAgent",
            bus=bus,
            topics=["config_updated", "pause_resolved", "postpone_pause", "set_enabled"],
        )
        self.interval_seconds = interval_minutes * 60
        self._next_trigger = time.time() + self.interval_seconds
        self._warning_sent = False
        self._enabled = True
        self._postpones_today = self._load_postpones_today()

    # ---------------- persistencia de posposiciones ----------------
    def _load_postpones_today(self) -> int:
        today = date.today().isoformat()
        if os.path.exists(_POSTPONES_PATH):
            try:
                with open(_POSTPONES_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("date") == today:
                    return int(data.get("count", 0))
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        return 0

    def _save_postpones_today(self) -> None:
        os.makedirs(os.path.dirname(_POSTPONES_PATH) or ".", exist_ok=True)
        with open(_POSTPONES_PATH, "w", encoding="utf-8") as f:
            json.dump({"date": date.today().isoformat(), "count": self._postpones_today}, f)

    # ---------------- mensajes ----------------
    def handle_message(self, message: Message) -> None:
        if message.topic == "config_updated":
            minutes = message.payload.get("interval_minutes")
            if minutes:
                self.interval_seconds = minutes * 60
                self._next_trigger = time.time() + self.interval_seconds
                self._warning_sent = False

        elif message.topic == "pause_resolved":
            self._next_trigger = time.time() + self.interval_seconds
            self._warning_sent = False

        elif message.topic == "postpone_pause":
            self._handle_postpone()

        elif message.topic == "set_enabled":
            self._enabled = bool(message.payload.get("enabled", True))
            logger.info("Programa %s", "reanudado" if self._enabled else "pausado")
            self.send("enabled_state", enabled=self._enabled)

    def _handle_postpone(self) -> None:
        # Revalida contra el archivo por si cambió el día desde el arranque.
        current_on_disk = self._load_postpones_today()
        self._postpones_today = max(self._postpones_today, current_on_disk)

        if self._postpones_today >= MAX_POSTPONES_PER_DAY:
            self.send("postpone_result", allowed=False,
                      remaining=0, max_per_day=MAX_POSTPONES_PER_DAY)
            return

        self._postpones_today += 1
        self._save_postpones_today()
        self._next_trigger = time.time() + POSTPONE_MINUTES * 60
        self._warning_sent = False
        remaining = MAX_POSTPONES_PER_DAY - self._postpones_today
        self.send("postpone_result", allowed=True,
                  remaining=remaining, max_per_day=MAX_POSTPONES_PER_DAY)

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

            if not self._enabled:
                continue

            if not self._warning_sent and 0 < remaining <= WARNING_SECONDS:
                self._warning_sent = True
                self.send("pause_warning", seconds=int(remaining))

            if remaining <= 0:
                self.send("pause_due")
                self._next_trigger = time.time() + self.interval_seconds
                self._warning_sent = False
