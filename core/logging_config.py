"""Configuración centralizada de logging.

Antes el proyecto usaba `print()` sueltos (ej. en VisionAgent al fallar la
descarga del modelo). Con esto, cualquier módulo puede hacer:

    import logging
    logger = logging.getLogger(__name__)
    logger.info("...")

y el mensaje queda tanto en consola como en un archivo rotativo, con
timestamp y nivel, sin tener que tocar código en cada agente que ya usaba
print. `setup_logging()` se llama una sola vez, al inicio de main.py.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "logs"
)
_LOG_PATH = os.path.join(_LOG_DIR, "pausa_activa.log")


def setup_logging(level: int = logging.INFO) -> None:
    os.makedirs(_LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Evita duplicar handlers si setup_logging() se llama más de una vez
    # (ej. en tests).
    if root.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        _LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
