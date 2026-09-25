"""Clase base para los ejercicios detectables por estimación de pose.

El criterio de éxito de la pausa activa es simple y robusto: el usuario debe
acumular `active_seconds_required` segundos (por defecto 60) realizando el
movimiento correcto frente a la cámara. Las repeticiones se cuentan además
como feedback visual, pero el requisito de desbloqueo es el tiempo activo,
para garantizar que realmente se movió y no que solo se quedó quieto en una
postura válida.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class BaseExercise(ABC):
    name: str = "Ejercicio"
    instructions: str = ""

    def __init__(self, active_seconds_required: float = 60.0):
        self.active_seconds_required = active_seconds_required
        self.active_seconds: float = 0.0
        self.reps: int = 0
        self._state: str = "unknown"

    @abstractmethod
    def _is_active_pose(self, lm: List[Tuple[float, float, float]]) -> bool:
        """True si el landmark actual corresponde a un movimiento correcto."""

    @abstractmethod
    def _update_reps(self, lm: List[Tuple[float, float, float]]) -> None:
        """Actualiza el conteo de repeticiones vía una pequeña máquina de estados."""

    def update(self, landmarks, dt: float) -> Dict:
        if landmarks:
            if self._is_active_pose(landmarks):
                self.active_seconds += dt
            self._update_reps(landmarks)
        return {
            "exercise": self.name,
            "active_seconds": round(min(self.active_seconds, self.active_seconds_required), 1),
            "required_seconds": self.active_seconds_required,
            "reps": self.reps,
        }

    def is_complete(self) -> bool:
        return self.active_seconds >= self.active_seconds_required
