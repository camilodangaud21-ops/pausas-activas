"""Bus de mensajes (pub/sub) que conecta a todos los agentes del sistema.

Cada agente se suscribe a los "topics" (temas) que le interesan y recibe una
única cola (queue.Queue) donde llegan, en orden, todos los mensajes de esos
temas. Publicar es simplemente poner un Message en las colas de todos los
suscriptores de ese topic. Este es el mecanismo de coordinación central del
sistema multiagente: los agentes no se conocen entre sí directamente, solo
conocen el bus.
"""

import queue
import threading
from typing import Dict, List

from core.messages import Message


class MessageBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List["queue.Queue[Message]"]] = {}
        self._lock = threading.Lock()

    def subscribe(self, topics: List[str]) -> "queue.Queue[Message]":
        """Registra una cola nueva para recibir todos los mensajes de `topics`."""
        q: "queue.Queue[Message]" = queue.Queue()
        with self._lock:
            for topic in topics:
                self._subscribers.setdefault(topic, []).append(q)
        return q

    def publish(self, message: Message) -> None:
        """Entrega el mensaje a todas las colas suscritas a message.topic."""
        with self._lock:
            queues = list(self._subscribers.get(message.topic, []))
        for q in queues:
            q.put(message)
