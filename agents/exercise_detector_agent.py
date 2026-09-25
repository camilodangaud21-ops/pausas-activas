"""ExerciseDetectorAgent: elige un ejercicio al iniciar cada pausa (según la
respuesta del usuario: "varios, elige uno al iniciar") y evalúa cada frame de
landmarks para medir progreso, hasta que se cumple el tiempo activo requerido.

Mejora: calibración inicial. Antes de empezar a contar los 60s de actividad,
se exige que el usuario esté "completamente visible" en cámara durante
`CALIBRATION_SECONDS` segundos continuos. Mientras no lo esté, el reloj de
actividad no corre y se publica "calibration_status" para que la UI muestre
feedback ("no te veo, ubícate frente a la cámara") en vez de quedarse muda.
"""

import logging
import random
import time

from agents.base_agent import BaseAgent
from core.messages import Message
from exercises.squats import Squats
from exercises.jumping_jacks import JumpingJacks
from exercises.arm_raises import ArmRaises

logger = logging.getLogger(__name__)

EXERCISES = [Squats, JumpingJacks, ArmRaises]

# Puntos clave que deben ser visibles (torso, hombros, caderas, rodillas,
# tobillos) para considerar que la persona está bien encuadrada. No exigimos
# los 33 landmarks porque manos/cara no importan para estos ejercicios.
_KEY_LANDMARKS = [11, 12, 23, 24, 25, 26, 27, 28]
_VISIBILITY_THRESHOLD = 0.6
_CALIBRATION_SECONDS = 1.0


class ExerciseDetectorAgent(BaseAgent):
    def __init__(self, bus, activity_seconds_required: float = 60.0):
        super().__init__(name="ExerciseDetectorAgent", bus=bus,
                          topics=["start_pause", "stop_pause", "landmarks"])
        self.activity_seconds_required = activity_seconds_required
        self._exercise = None
        self._active = False
        self._last_ts = None

        # Estado de calibración.
        self._calibrated = False
        self._calibration_progress = 0.0
        self._last_visible_state = None  # para no espamear calibration_status

    def handle_message(self, message: Message) -> None:
        if message.topic == "start_pause":
            self._start_new_exercise()
        elif message.topic == "stop_pause":
            self._active = False
            self._exercise = None
        elif message.topic == "landmarks" and self._active:
            self._process_landmarks(message.payload.get("landmarks"))

    def _start_new_exercise(self) -> None:
        exercise_cls = random.choice(EXERCISES)
        self._exercise = exercise_cls(active_seconds_required=self.activity_seconds_required)
        self._active = True
        self._last_ts = time.time()
        self._calibrated = False
        self._calibration_progress = 0.0
        self._last_visible_state = None
        logger.info("Ejercicio seleccionado: %s", self._exercise.name)
        self.send("exercise_selected", name=self._exercise.name,
                   instructions=self._exercise.instructions)

    @staticmethod
    def _is_fully_visible(landmarks) -> bool:
        if not landmarks:
            return False
        try:
            return all(landmarks[i][2] >= _VISIBILITY_THRESHOLD for i in _KEY_LANDMARKS)
        except (IndexError, TypeError):
            return False

    def _process_landmarks(self, landmarks) -> None:
        now = time.time()
        dt = now - (self._last_ts or now)
        self._last_ts = now
        if self._exercise is None:
            return

        if not self._calibrated:
            self._run_calibration(landmarks, dt)
            return

        progress = self._exercise.update(landmarks, dt)
        self.send("exercise_progress", **progress)
        if self._exercise.is_complete():
            logger.info("Pausa completada: %s", self._exercise.name)
            self.send("exercise_complete", name=self._exercise.name)
            self._active = False

    def _run_calibration(self, landmarks, dt: float) -> None:
        visible = self._is_fully_visible(landmarks)
        if visible != self._last_visible_state:
            self.send("calibration_status", visible=visible)
            self._last_visible_state = visible

        if visible:
            self._calibration_progress += dt
            if self._calibration_progress >= _CALIBRATION_SECONDS:
                self._calibrated = True
                logger.info("Calibración completa, iniciando conteo de actividad")
        else:
            self._calibration_progress = 0.0
