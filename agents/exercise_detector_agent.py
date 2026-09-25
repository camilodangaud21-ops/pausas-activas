"""ExerciseDetectorAgent: elige un ejercicio al iniciar cada pausa (según la
respuesta del usuario: "varios, elige uno al iniciar") y evalúa cada frame de
landmarks para medir progreso, hasta que se cumple el tiempo activo requerido.
"""

import random
import time

from agents.base_agent import BaseAgent
from core.messages import Message
from exercises.squats import Squats
from exercises.jumping_jacks import JumpingJacks
from exercises.arm_raises import ArmRaises

EXERCISES = [Squats, JumpingJacks, ArmRaises]


class ExerciseDetectorAgent(BaseAgent):
    def __init__(self, bus, activity_seconds_required: float = 60.0):
        super().__init__(name="ExerciseDetectorAgent", bus=bus,
                          topics=["start_pause", "stop_pause", "landmarks"])
        self.activity_seconds_required = activity_seconds_required
        self._exercise = None
        self._active = False
        self._last_ts = None

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
        self.send("exercise_selected", name=self._exercise.name,
                   instructions=self._exercise.instructions)

    def _process_landmarks(self, landmarks) -> None:
        now = time.time()
        dt = now - (self._last_ts or now)
        self._last_ts = now
        if self._exercise is None:
            return
        progress = self._exercise.update(landmarks, dt)
        self.send("exercise_progress", **progress)
        if self._exercise.is_complete():
            self.send("exercise_complete", name=self._exercise.name)
            self._active = False
