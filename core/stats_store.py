"""Persistencia simple (JSON) de estadísticas diarias.

Estructura del archivo:

{
  "2026-09-25": {
    "pauses_completed": 4,
    "pauses_postponed": 1,
    "emergency_unlocks": 0,
    "exercises": {"Sentadillas": 2, "Saltos de tijera": 2}
  },
  ...
}

Un solo `Lock` protege lectura/escritura porque StatsAgent corre en su
propio hilo pero varios eventos pueden llegar en sucesión rápida.
"""

import json
import os
import threading
from datetime import date
from typing import Dict


class StatsStore:
    def __init__(self, path: str = os.path.join("data", "stats.json")):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)

    def _load(self) -> Dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save(self, data: Dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _today_key() -> str:
        return date.today().isoformat()

    def _today_bucket(self, data: Dict) -> Dict:
        key = self._today_key()
        return data.setdefault(key, {
            "pauses_completed": 0,
            "pauses_postponed": 0,
            "emergency_unlocks": 0,
            "exercises": {},
        })

    def increment(self, field: str, amount: int = 1) -> None:
        with self._lock:
            data = self._load()
            bucket = self._today_bucket(data)
            bucket[field] = bucket.get(field, 0) + amount
            self._save(data)

    def add_exercise_completion(self, exercise_name: str) -> None:
        with self._lock:
            data = self._load()
            bucket = self._today_bucket(data)
            bucket["pauses_completed"] += 1
            bucket["exercises"][exercise_name] = bucket["exercises"].get(exercise_name, 0) + 1
            self._save(data)

    def today_summary(self) -> Dict:
        with self._lock:
            data = self._load()
            return dict(self._today_bucket(data))
