"""Detección de estiramiento con brazos levantados por encima de los hombros."""

from exercises.base_exercise import BaseExercise

L_SHOULDER, R_SHOULDER = 11, 12
L_WRIST, R_WRIST = 15, 16


class ArmRaises(BaseExercise):
    name = "Estiramiento de brazos"
    instructions = "Levanta ambos brazos por encima de los hombros y bájalos, de forma repetida."

    def _is_active_pose(self, lm) -> bool:
        return lm[L_WRIST][1] < lm[L_SHOULDER][1] and lm[R_WRIST][1] < lm[R_SHOULDER][1]

    def _update_reps(self, lm) -> None:
        active = self._is_active_pose(lm)
        if active and self._state != "up":
            self.reps += 1
            self._state = "up"
        elif not active:
            self._state = "down"
