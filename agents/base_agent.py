"""Clase base para todos los agentes del sistema.

Cada agente:
  - Corre en su propio hilo (autonomía).
  - Se suscribe a uno o más "topics" del MessageBus (percepción del entorno
    compartido, es decir, los mensajes de otros agentes).
  - Reacciona a los mensajes recibidos implementando `handle_message`.
  - Puede publicar nuevos mensajes con `self.send(topic, **payload)` (acción
    sobre el entorno compartido).

La excepción es LockScreenAgent, que por requisito de Tkinter debe correr en
el hilo principal; por eso no hereda de BaseAgent sino que implementa el
mismo patrón de suscripción manualmente (ver agents/lock_screen_agent.py).
"""

import queue
import threading
from abc import ABC, abstractmethod
from typing import List

from core.message_bus import MessageBus
from core.messages import Message


class BaseAgent(threading.Thread, ABC):
    def __init__(self, name: str, bus: MessageBus, topics: List[str]):
        threading.Thread.__init__(self, name=name, daemon=True)
        self.bus = bus
        self.inbox: "queue.Queue[Message]" = bus.subscribe(topics)
        self._running = threading.Event()
        self._running.set()

    def send(self, topic: str, **payload) -> None:
        self.bus.publish(Message(topic=topic, sender=self.name, payload=payload))

    def stop(self) -> None:
        self._running.clear()

    def run(self) -> None:
        """Bucle por defecto: espera mensajes y los despacha a handle_message."""
        while self._running.is_set():
            try:
                message = self.inbox.get(timeout=0.2)
            except queue.Empty:
                continue
            self.handle_message(message)

    @abstractmethod
    def handle_message(self, message: Message) -> None:
        """Reacciona a un mensaje recibido. Cada agente concreto lo implementa."""
