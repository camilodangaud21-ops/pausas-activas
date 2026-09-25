"""Detección de saltos de tijera (jumping jacks)."""

from core.geometry import distance_2d
from exercises.base_exercise import BaseExercise

L_SHOULDER, R_SHOULDER = 11, 12
L_WRIST, R_WRIST = 15, 16
L_ANKLE, R_ANKLE = 27, 28

LEG_SPREAD_FACTOR = 1.4  # separación de tobillos vs ancho de hombros para considerar "abierto"


class JumpingJacks(BaseExercise):
    name = "Saltos de tijera"
    instructions = "Abre brazos y piernas al saltar, luego ciérralos. Repite."

    def _is_open(self, lm) -> bool:
        shoulder_width = distance_2d(lm[L_SHOULDER][:2], lm[R_SHOULDER][:2]) + 1e-6
        arms_up = lm[L_WRIST][1] < lm[L_SHOULDER][1] and lm[R_WRIST][1] < lm[R_SHOULDER][1]
        legs_apart = distance_2d(lm[L_ANKLE][:2], lm[R_ANKLE][:2]) > shoulder_width * LEG_SPREAD_FACTOR
        return arms_up and legs_apart

    def _is_active_pose(self, lm) -> bool:
        return self._is_open(lm) or self._state == "open"

    def _update_reps(self, lm) -> None:
        open_now = self._is_open(lm)
        if open_now and self._state != "open":
            self._state = "open"
        elif not open_now and self._state == "open":
            self.reps += 1
            self._state = "closed"
