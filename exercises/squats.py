"""Detección de sentadillas a partir del ángulo de la rodilla."""

from core.geometry import angle_2d
from exercises.base_exercise import BaseExercise

# Índices de landmarks de MediaPipe Pose (33 puntos).
L_HIP, L_KNEE, L_ANKLE = 23, 25, 27
R_HIP, R_KNEE, R_ANKLE = 24, 26, 28

DOWN_THRESHOLD = 110  # grados: pierna doblada
UP_THRESHOLD = 160    # grados: pierna extendida


class Squats(BaseExercise):
    name = "Sentadillas"
    instructions = "Baja doblando las rodillas y vuelve a subir, de forma continua."

    def _knee_angle(self, lm) -> float:
        left = angle_2d(lm[L_HIP][:2], lm[L_KNEE][:2], lm[L_ANKLE][:2])
        right = angle_2d(lm[R_HIP][:2], lm[R_KNEE][:2], lm[R_ANKLE][:2])
        return (left + right) / 2

    def _is_active_pose(self, lm) -> bool:
        # Cuenta como "activo" mientras no esté completamente de pie y quieto.
        return self._knee_angle(lm) < UP_THRESHOLD

    def _update_reps(self, lm) -> None:
        angle = self._knee_angle(lm)
        if angle < DOWN_THRESHOLD:
            self._state = "down"
        elif angle > UP_THRESHOLD and self._state == "down":
            self.reps += 1
            self._state = "up"
