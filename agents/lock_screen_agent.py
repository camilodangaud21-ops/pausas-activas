"""LockScreenAgent: agente de interfaz/bloqueo.

Por requisito de Tkinter, el mainloop debe correr en el hilo principal, así
que este agente NO hereda de BaseAgent (que usa threading.Thread). En su
lugar implementa el mismo patrón de suscripción al bus, pero se integra al
mainloop de Tk vía `root.after(...)`, revisando su bandeja de entrada sin
bloquear cada 50 ms.

Responsabilidades:
  - Al recibir "pause_due": abre una ventana a pantalla completa, siempre
    encima, sin botón de cerrar funcional y con grab_set() (captura todo el
    input), y dispara "start_pause" para que VisionAgent/ExerciseDetector
    empiecen a trabajar.
  - Muestra el ejercicio elegido, el video de la cámara con el esqueleto de
    pose dibujado, y el progreso (segundos activos / requeridos, repeticiones).
  - Al recibir "exercise_complete": cierra la ventana y notifica
    "stop_pause" + "pause_resolved" para que el resto del sistema vuelva a
    su estado de reposo y el temporizador se reinicie.

Limitación conocida (Windows): esta ventana bloquea el uso normal del
computador mientras está abierta, pero al ser una app de usuario no puede
impedir combinaciones reservadas por el sistema operativo como
Ctrl+Alt+Supr o el cambio de usuario. Es un bloqueo de aplicación, no un
reemplazo del lock screen de Windows.
"""

import queue
import tkinter as tk

from core.message_bus import MessageBus
from core.messages import Message

try:
    import cv2
    from PIL import Image, ImageTk
    _HAS_VISION_LIBS = True
except ImportError:
    _HAS_VISION_LIBS = False


class LockScreenAgent:
    TOPICS = ["pause_due", "exercise_selected", "exercise_progress",
              "exercise_complete", "frame_ready", "tick"]

    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.inbox: "queue.Queue[Message]" = bus.subscribe(self.TOPICS)

        self.root = tk.Tk()
        self.root.withdraw()  # la ventana raíz nunca se muestra

        self.overlay = None
        self.video_label = None
        self.title_label = None
        self.progress_var = tk.StringVar(value="")
        self._locked = False
        self._photo = None  # referencia viva para que Tk no la recolecte

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
        if message.topic == "pause_due" and not self._locked:
            self._open_overlay()
        elif message.topic == "exercise_selected":
            self._set_instructions(message.payload["name"], message.payload["instructions"])
        elif message.topic == "exercise_progress":
            self._update_progress(message.payload)
        elif message.topic == "exercise_complete":
            self._close_overlay()
        elif message.topic == "frame_ready" and self._locked:
            self._update_frame(message.payload["frame"])

    # ---------------- construcción de la ventana ----------------
    def _open_overlay(self) -> None:
        self._locked = True
        self.overlay = tk.Toplevel(self.root)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(bg="#0f172a")
        self.overlay.protocol("WM_DELETE_WINDOW", lambda: None)  # no se puede cerrar con la X
        self.overlay.bind("<Escape>", lambda e: None)  # ni con Escape
        self.overlay.grab_set()
        self.overlay.focus_force()

        tk.Label(self.overlay, text="⏰ Pausa activa: ¡Levántate!",
                 font=("Segoe UI", 32, "bold"), fg="white", bg="#0f172a").pack(pady=(60, 10))

        self.title_label = tk.Label(self.overlay, text="Preparando ejercicio...",
                                     font=("Segoe UI", 18), fg="#38bdf8", bg="#0f172a",
                                     wraplength=800, justify="center")
        self.title_label.pack(pady=10)

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

    def start(self) -> None:
        self.root.mainloop()
