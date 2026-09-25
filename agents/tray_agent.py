"""TrayAgent: ícono en la bandeja del sistema (system tray) con un menú para:

  - Pausar / reanudar el programa (ej. antes de una videollamada), sin
    cerrarlo del todo.
  - Ver un resumen rápido de las estadísticas de hoy.
  - Cambiar el intervalo entre pausas sin reiniciar el programa.
  - Salir de la aplicación.

Depende de `pystray` (opcional, ver requirements.txt). Si no está instalado,
el agente se desactiva solo con un log y el resto del programa sigue
funcionando exactamente igual, sin ícono.

Detalle de arquitectura: como Tkinter debe correr en el hilo principal
(igual que LockScreenAgent), este agente NO puede abrir el diálogo de
"cambiar intervalo" directamente. En vez de eso publica
"request_interval_dialog" y es LockScreenAgent (que sí vive en el hilo
principal) quien realmente abre el `simpledialog`. El ícono de pystray
corre en su propio hilo nativo aparte del hilo de mensajes de este agente.
"""

import logging
import threading

from agents.base_agent import BaseAgent
from core.messages import Message
from core.stats_store import StatsStore

logger = logging.getLogger(__name__)

try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_TRAY_LIBS = True
except ImportError:
    _HAS_TRAY_LIBS = False


def _build_icon_image():
    """Ícono simple generado en memoria (un círculo), para no depender de
    un archivo .ico/.png externo."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, size - 4, size - 4), fill=(56, 189, 248, 255))
    draw.ellipse((18, 14, size - 18, size - 30), fill=(15, 23, 42, 255))
    return img


class TrayAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__(name="TrayAgent", bus=bus,
                          topics=["enabled_state", "config_updated"])
        self.stats_store = StatsStore()
        self._enabled = True
        self._interval_minutes = None
        self.icon = None
        self._icon_thread = None

    # ---------------- ciclo de mensajes (estado en memoria) ----------------
    def handle_message(self, message: Message) -> None:
        if message.topic == "enabled_state":
            self._enabled = bool(message.payload.get("enabled", True))
            self._refresh_menu()
        elif message.topic == "config_updated":
            self._interval_minutes = message.payload.get("interval_minutes")

    def run(self) -> None:
        if not _HAS_TRAY_LIBS:
            logger.info("pystray/Pillow no instalados: se omite el ícono de bandeja")
            return
        self._start_icon()
        super().run()  # sigue atendiendo mensajes del bus en este mismo hilo

    # ---------------- pystray ----------------
    def _start_icon(self) -> None:
        self.icon = pystray.Icon(
            "pausa_activa", _build_icon_image(), "Pausa activa", self._build_menu()
        )
        self._icon_thread = threading.Thread(target=self.icon.run, daemon=True)
        self._icon_thread.start()

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(
                lambda item: "Reanudar programa" if not self._enabled else "Pausar programa",
                self._toggle_enabled,
            ),
            pystray.MenuItem("Cambiar intervalo...", self._request_interval_dialog),
            pystray.MenuItem("Ver estadísticas de hoy", self._show_stats),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", self._quit),
        )

    def _refresh_menu(self) -> None:
        if self.icon is not None:
            self.icon.update_menu()

    def _toggle_enabled(self, icon=None, item=None) -> None:
        self.send("set_enabled", enabled=not self._enabled)

    def _request_interval_dialog(self, icon=None, item=None) -> None:
        self.send("request_interval_dialog")

    def _show_stats(self, icon=None, item=None) -> None:
        summary = self.stats_store.today_summary()
        text = (
            f"Pausas completadas: {summary.get('pauses_completed', 0)}\n"
            f"Pospuestas: {summary.get('pauses_postponed', 0)}\n"
            f"Desbloqueos de emergencia: {summary.get('emergency_unlocks', 0)}"
        )
        logger.info("Estadísticas de hoy -> %s", text.replace("\n", " | "))
        if self.icon is not None:
            try:
                self.icon.notify(text, title="Pausa activa: hoy")
            except NotImplementedError:
                # Algunos backends (ej. ciertas versiones de GTK/AppIndicator)
                # no soportan notificaciones; el resumen ya quedó en el log.
                pass

    def _quit(self, icon=None, item=None) -> None:
        logger.info("Saliendo desde el ícono de bandeja")
        self.send("quit_app")
        if self.icon is not None:
            self.icon.stop()
        self.stop()
