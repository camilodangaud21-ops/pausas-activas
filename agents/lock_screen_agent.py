"""LockScreenAgent: agente de interfaz/bloqueo.

Por requisito de Tkinter, el mainloop debe correr en el hilo principal, así
que este agente NO hereda de BaseAgent (que usa threading.Thread). En su
lugar implementa el mismo patrón de suscripción al bus, pero se integra al
mainloop de Tk vía `root.after(...)`, revisando su bandeja de entrada sin
bloquear cada 50 ms.

Responsabilidades:
  - Al recibir "pause_warning": abre una ventana pequeña (no bloqueante,
    esquina superior derecha) avisando que la pausa activa está por llegar,
    con opción de "Posponer" (limitada por SchedulerAgent).
  - Al recibir "pause_due": abre una ventana a pantalla completa -en TODOS
    los monitores conectados-, siempre encima, sin botón de cerrar
    funcional y con grab_set() (captura todo el input), y dispara
    "start_pause" para que VisionAgent/ExerciseDetector empiecen a trabajar.
  - Muestra el ejercicio elegido, el video de la cámara con el esqueleto de
    pose dibujado, feedback de calibración ("no te veo") y el progreso
    (segundos activos / requeridos, repeticiones).
  - Botón de emergencia: mantener Ctrl+Shift+Esc presionado 5 segundos
    fuerza el desbloqueo (con aviso al bus para que quede registrado y no
    se abuse en silencio).
  - Al recibir "exercise_complete": cierra la ventana y notifica
    "stop_pause" + "pause_resolved" para que el resto del sistema vuelva a
    su estado de reposo y el temporizador se reinicie.

Limitación conocida (Windows): esta ventana bloquea el uso normal del
computador mientras está abierta, pero al ser una app de usuario no puede
impedir combinaciones reservadas por el sistema operativo como
Ctrl+Alt+Supr o el cambio de usuario. Es un bloqueo de aplicación, no un
reemplazo del lock screen de Windows.
"""

import logging
import queue
import sys
import tkinter as tk
from tkinter import simpledialog
import time

from core.message_bus import MessageBus
from core.messages import Message

logger = logging.getLogger(__name__)

try:
    import cv2
    from PIL import Image, ImageTk
    _HAS_VISION_LIBS = True
except ImportError:
    _HAS_VISION_LIBS = False

EMERGENCY_HOLD_SECONDS = 5.0


def _get_virtual_screen_bounds(root: tk.Tk):
    """Devuelve (x, y, width, height) que cubre TODOS los monitores.

    En Windows, la API de virtual screen de win32 reporta el rectángulo que
    engloba todos los monitores conectados (con coordenadas negativas si hay
    un monitor a la izquierda/arriba del principal). tkinter por sí solo solo
    conoce el monitor principal (winfo_screenwidth/height), por eso se usa
    ctypes cuando está disponible. Si algo falla (Linux/Mac, o error de
    ctypes), se degrada a un solo monitor sin romper el programa.
    """
    if sys.platform.startswith("win"):
        try:
            import ctypes
            SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
            SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
            user32 = ctypes.windll.user32
            x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            if w > 0 and h > 0:
                return x, y, w, h
        except Exception:
            logger.exception("No se pudo leer el tamaño del escritorio virtual")
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


class LockScreenAgent:
    TOPICS = [
        "pause_due", "pause_warning", "exercise_selected", "exercise_progress",
        "exercise_complete", "frame_ready", "tick", "postpone_result",
        "calibration_status", "request_interval_dialog", "quit_app",
    ]

    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.inbox: "queue.Queue[Message]" = bus.subscribe(self.TOPICS)

        self.root = tk.Tk()
        self.root.withdraw()  # la ventana raíz nunca se muestra

        self.overlay = None
        self.warning_window = None
        self.video_label = None
        self.title_label = None
        self.calibration_var = tk.StringVar(value="")
        self.progress_var = tk.StringVar(value="")
        self.warning_var = tk.StringVar(value="")
        self._locked = False
        self._photo = None  # referencia viva para que Tk no la recolecte

        # Estado del combo de emergencia.
        self._emergency_mods = {"ctrl": False, "shift": False, "escape": False}
        self._emergency_start = None
        self.emergency_var = tk.StringVar(value="")

        self._poll()

    # ---------------- ciclo de mensajes ----------------
    def _poll(self) -> None:
        try:
            while True:
                message = self.inbox.get_nowait()
                self._dispatch(message)
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    def _dispatch(self, message: Message) -> None:
        if message.topic == "pause_warning" and not self._locked:
            self._show_warning(message.payload.get("seconds", 0))
        elif message.topic == "pause_due" and not self._locked:
            self._close_warning()
            self._open_overlay()
        elif message.topic == "postpone_result":
            self._handle_postpone_result(message.payload)
        elif message.topic == "exercise_selected":
            self._set_instructions(message.payload["name"], message.payload["instructions"])
        elif message.topic == "exercise_progress":
            self._update_progress(message.payload)
        elif message.topic == "calibration_status":
            self._update_calibration(message.payload.get("visible", False))
        elif message.topic == "exercise_complete":
            self._close_overlay()
        elif message.topic == "frame_ready" and self._locked:
            self._update_frame(message.payload["frame"])
        elif message.topic == "tick" and self.warning_window is not None:
            self._update_warning_countdown(message.payload.get("remaining_seconds", 0))
        elif message.topic == "request_interval_dialog":
            self._open_interval_dialog()
        elif message.topic == "quit_app":
            self._quit()

    # ---------------- diálogo de cambio de intervalo (desde la bandeja) ----------------
    def _open_interval_dialog(self) -> None:
        minutes = simpledialog.askinteger(
            "Pausa activa para programadores",
            "¿Cada cuántos minutos quieres que se active la pausa activa?",
            minvalue=1, maxvalue=240, parent=self.root,
        )
        if minutes:
            self.bus.publish(Message(topic="set_interval", sender="LockScreenAgent",
                                      payload={"minutes": minutes}))

    def _quit(self) -> None:
        self._close_warning()
        if self.overlay is not None:
            self.overlay.grab_release()
            self.overlay.destroy()
            self.overlay = None
        self.root.quit()

    # ---------------- aviso previo (no bloqueante) ----------------
    def _show_warning(self, seconds: int) -> None:
        if self.warning_window is not None:
            return
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg="#1e293b")
        w, h = 320, 110
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        win.geometry(f"{w}x{h}+{sw - w - 20}+20")

        tk.Label(win, text="⏰ Pausa activa en camino",
                 font=("Segoe UI", 12, "bold"), fg="white", bg="#1e293b").pack(pady=(10, 2))
        tk.Label(win, textvariable=self.warning_var,
                 font=("Segoe UI", 11), fg="#38bdf8", bg="#1e293b").pack()

        btn = tk.Button(win, text="Posponer 10 min", command=self._request_postpone,
                         bg="#334155", fg="white", relief="flat", padx=10, pady=4)
        btn.pack(pady=(8, 10))

        self.warning_var.set(f"Faltan {seconds}s")
        self.warning_window = win

    def _update_warning_countdown(self, remaining_seconds: float) -> None:
        self.warning_var.set(f"Faltan {int(remaining_seconds)}s")

    def _request_postpone(self) -> None:
        self.bus.publish(Message(topic="postpone_pause", sender="LockScreenAgent"))

    def _handle_postpone_result(self, payload: dict) -> None:
        if self.warning_window is None:
            return
        if payload.get("allowed"):
            self._close_warning()
        else:
            self.warning_var.set("Ya usaste tus posposiciones de hoy")
            self.root.after(3000, self._close_warning)

    def _close_warning(self) -> None:
        if self.warning_window is not None:
            self.warning_window.destroy()
            self.warning_window = None

    # ---------------- construcción de la ventana de bloqueo ----------------
    def _open_overlay(self) -> None:
        self._locked = True
        self.overlay = tk.Toplevel(self.root)

        # Cubre TODOS los monitores conectados (no solo el principal), en
        # vez de usar attributes("-fullscreen", True) que en Windows suele
        # limitarse al monitor donde vive la ventana.
        x, y, w, h = _get_virtual_screen_bounds(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.geometry(f"{w}x{h}+{x}+{y}")
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(bg="#0f172a")
        self.overlay.protocol("WM_DELETE_WINDOW", lambda: None)  # no se puede cerrar con la X
        self.overlay.grab_set()
        self.overlay.focus_force()

        self._bind_emergency_unlock(self.overlay)

        tk.Label(self.overlay, text="⏰ Pausa activa: ¡Levántate!",
                 font=("Segoe UI", 32, "bold"), fg="white", bg="#0f172a").pack(pady=(60, 10))

        self.title_label = tk.Label(self.overlay, text="Preparando ejercicio...",
                                     font=("Segoe UI", 18), fg="#38bdf8", bg="#0f172a",
                                     wraplength=800, justify="center")
        self.title_label.pack(pady=10)

        tk.Label(self.overlay, textvariable=self.calibration_var,
                 font=("Segoe UI", 14), fg="#facc15", bg="#0f172a").pack(pady=(0, 6))

        self.video_label = tk.Label(self.overlay, bg="#020617")
        self.video_label.pack(pady=20)
        if not _HAS_VISION_LIBS:
            self.video_label.configure(
                text="(Instala opencv-python, mediapipe y pillow para ver la cámara)",
                fg="#f87171", font=("Segoe UI", 12)
            )

        tk.Label(self.overlay, textvariable=self.progress_var,
                 font=("Segoe UI", 18), fg="white", bg="#0f172a").pack(pady=10)

        tk.Label(self.overlay,
                 text="La pantalla se desbloqueará automáticamente al completar el ejercicio.",
                 font=("Segoe UI", 12), fg="#94a3b8", bg="#0f172a").pack(pady=(10, 0))

        tk.Label(self.overlay, textvariable=self.emergency_var,
                 font=("Segoe UI", 11), fg="#f87171", bg="#0f172a").pack(pady=(4, 0))
        tk.Label(self.overlay,
                 text="Emergencia: mantén Ctrl + Shift + Esc por 5s para forzar el desbloqueo.",
                 font=("Segoe UI", 9), fg="#64748b", bg="#0f172a").pack(pady=(2, 0))

        self.calibration_var.set("")
        self.bus.publish(Message(topic="start_pause", sender="LockScreenAgent"))

    def _set_instructions(self, name: str, instructions: str) -> None:
        if self.title_label:
            self.title_label.config(text=f"{name}: {instructions}")

    def _update_progress(self, payload: dict) -> None:
        seconds = payload.get("active_seconds", 0)
        required = payload.get("required_seconds", 60)
        reps = payload.get("reps", 0)
        self.progress_var.set(
            f"Tiempo en movimiento: {seconds:.0f}s / {required:.0f}s   |   Repeticiones: {reps}"
        )

    def _update_calibration(self, visible: bool) -> None:
        if visible:
            self.calibration_var.set("")
        else:
            self.calibration_var.set("No te veo bien: ubícate de cuerpo entero frente a la cámara")

    def _update_frame(self, frame) -> None:
        if not _HAS_VISION_LIBS or self.video_label is None:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb).resize((480, 360))
        self._photo = ImageTk.PhotoImage(img)
        self.video_label.configure(image=self._photo)

    def _close_overlay(self) -> None:
        self._locked = False
        self.bus.publish(Message(topic="stop_pause", sender="LockScreenAgent"))
        self.bus.publish(Message(topic="pause_resolved", sender="LockScreenAgent"))
        if self.overlay is not None:
            self.overlay.grab_release()
            self.overlay.destroy()
            self.overlay = None
        self._emergency_start = None
        self.emergency_var.set("")

    # ---------------- botón de emergencia (Ctrl+Shift+Esc por 5s) ----------------
    def _bind_emergency_unlock(self, widget: tk.Widget) -> None:
        widget.bind("<KeyPress-Control_L>", lambda e: self._set_mod("ctrl", True))
        widget.bind("<KeyPress-Control_R>", lambda e: self._set_mod("ctrl", True))
        widget.bind("<KeyRelease-Control_L>", lambda e: self._set_mod("ctrl", False))
        widget.bind("<KeyRelease-Control_R>", lambda e: self._set_mod("ctrl", False))

        widget.bind("<KeyPress-Shift_L>", lambda e: self._set_mod("shift", True))
        widget.bind("<KeyPress-Shift_R>", lambda e: self._set_mod("shift", True))
        widget.bind("<KeyRelease-Shift_L>", lambda e: self._set_mod("shift", False))
        widget.bind("<KeyRelease-Shift_R>", lambda e: self._set_mod("shift", False))

        widget.bind("<KeyPress-Escape>", lambda e: self._set_mod("escape", True))
        widget.bind("<KeyRelease-Escape>", lambda e: self._set_mod("escape", False))

    def _set_mod(self, name: str, pressed: bool) -> None:
        self._emergency_mods[name] = pressed
        combo_active = all(self._emergency_mods.values())

        if combo_active and self._emergency_start is None:
            self._emergency_start = time.time()
            self._poll_emergency_hold()
        elif not combo_active:
            self._emergency_start = None
            self.emergency_var.set("")

    def _poll_emergency_hold(self) -> None:
        if self._emergency_start is None or not self._locked:
            return
        if not all(self._emergency_mods.values()):
            self._emergency_start = None
            self.emergency_var.set("")
            return

        elapsed = time.time() - self._emergency_start
        remaining = EMERGENCY_HOLD_SECONDS - elapsed
        if remaining <= 0:
            self._trigger_emergency_unlock()
            return

        self.emergency_var.set(f"Desbloqueo de emergencia en {remaining:.1f}s...")
        self.overlay.after(100, self._poll_emergency_hold)

    def _trigger_emergency_unlock(self) -> None:
        logger.warning("Desbloqueo de emergencia activado por el usuario")
        self.bus.publish(Message(topic="emergency_unlock_used", sender="LockScreenAgent"))
        self._emergency_mods = {k: False for k in self._emergency_mods}
        self._emergency_start = None
        self._close_overlay()

    def start(self) -> None:
        self.root.mainloop()
