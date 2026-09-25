"""Punto de entrada del sistema multiagente de pausas activas.

Arquitectura (ver README.md para el diagrama completo):
  ConfigAgent          -> configuración persistente (config.json)
  SchedulerAgent        -> temporizador, dispara "pause_due" cada X minutos
  VisionAgent           -> cámara + MediaPipe Pose -> "landmarks", "frame_ready"
  ExerciseDetectorAgent -> elige ejercicio y evalúa "landmarks" -> progreso
  LockScreenAgent       -> UI de bloqueo (hilo principal, Tkinter)

Todos se comunican exclusivamente a través del MessageBus, sin referencias
directas entre sí (bajo acoplamiento propio de un sistema multiagente).
"""

import tkinter as tk
from tkinter import simpledialog

from core.message_bus import MessageBus
from agents.config_agent import ConfigAgent
from agents.scheduler_agent import SchedulerAgent
from agents.vision_agent import VisionAgent
from agents.exercise_detector_agent import ExerciseDetectorAgent
from agents.lock_screen_agent import LockScreenAgent


def ask_interval(default_minutes: int) -> int:
    """Pregunta al usuario, al iniciar, cada cuántos minutos quiere la pausa."""
    root = tk.Tk()
    root.withdraw()
    minutes = simpledialog.askinteger(
        "Pausa activa para programadores",
        "¿Cada cuántos minutos quieres que se active la pausa activa?",
        initialvalue=default_minutes, minvalue=1, maxvalue=240, parent=root,
    )
    root.destroy()
    return minutes or default_minutes


def main() -> None:
    bus = MessageBus()

    config_agent = ConfigAgent(bus)
    interval_minutes = ask_interval(config_agent.data["interval_minutes"])
    config_agent.data["interval_minutes"] = interval_minutes
    config_agent.save()

    activity_seconds = config_agent.data["activity_seconds_required"]
    camera_index = config_agent.data["camera_index"]

    scheduler = SchedulerAgent(bus, interval_minutes=interval_minutes)
    vision = VisionAgent(bus, camera_index=camera_index)
    detector = ExerciseDetectorAgent(bus, activity_seconds_required=activity_seconds)

    for agent in (config_agent, scheduler, vision, detector):
        agent.start()  # cada uno en su propio hilo

    lock_screen = LockScreenAgent(bus)  # corre en el hilo principal (Tkinter)
    lock_screen.start()


if __name__ == "__main__":
    main()
