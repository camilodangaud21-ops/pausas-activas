"""ConfigAgent: dueño de la configuración persistente del sistema.

Carga config.json al iniciar, la expone a los demás agentes (vía main.py) y
escucha mensajes "set_interval" para actualizar y persistir cambios en
caliente, notificando al resto con "config_updated".
"""

import json
import os

from agents.base_agent import BaseAgent
from core.messages import Message

DEFAULT_CONFIG = {
    "interval_minutes": 30,
    "camera_index": 0,
    "activity_seconds_required": 60,
}


class ConfigAgent(BaseAgent):
    def __init__(self, bus, path: str = "config.json"):
        super().__init__(name="ConfigAgent", bus=bus, topics=["set_interval"])
        self.path = path
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
            except (json.JSONDecodeError, OSError):
                pass
        return dict(DEFAULT_CONFIG)

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def handle_message(self, message: Message) -> None:
        if message.topic == "set_interval":
            minutes = message.payload.get("minutes")
            if minutes and minutes > 0:
                self.data["interval_minutes"] = minutes
                self.save()
                self.send("config_updated", **self.data)
