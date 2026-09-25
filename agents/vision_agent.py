"""VisionAgent: encapsula la cámara y MediaPipe Pose.

Usa la **Tasks API** de MediaPipe (`mediapipe.tasks.vision.PoseLandmarker`),
que es la que exigen las versiones actuales del paquete (>=0.10, y toda la
serie 1.0.x): Google eliminó la API vieja `mp.solutions.pose`. La Tasks API
necesita un archivo de modelo (.task) que se descarga automáticamente la
primera vez que corres el programa (requiere internet solo esa vez; luego
queda cacheado en `models/pose_landmarker_lite.task`).

Permanece inactivo (sin tocar la cámara) hasta recibir "start_pause". Mientras
la pausa está activa, captura frames, extrae landmarks de pose y publica:
  - "frame_ready": frame anotado (numpy array BGR), para mostrarlo en pantalla.
  - "landmarks": lista de (x, y, visibility) de los 33 puntos de MediaPipe,
    o None si no se detectó a la persona en ese frame.
Se detiene al recibir "stop_pause" y libera la cámara.
"""

import os
import queue
import time
import urllib.request

from agents.base_agent import BaseAgent
from core.messages import Message

try:
    import cv2
    import mediapipe as mp
    _HAS_CV = True
except ImportError:
    _HAS_CV = False

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"
)
_MODEL_PATH = os.path.join(_MODEL_DIR, "pose_landmarker_lite.task")

# Conexiones del esqueleto (torso, brazos, piernas) usadas solo para dibujar
# y para nuestros ejercicios. Antes venían de mp.solutions.drawing_utils,
# que también fue eliminado, así que las definimos a mano con los índices
# estándar de los 33 landmarks de MediaPipe Pose.
_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (27, 31),
    (24, 26), (26, 28), (28, 30), (28, 32),
]


def _ensure_model_downloaded() -> None:
    if os.path.exists(_MODEL_PATH):
        return
    os.makedirs(_MODEL_DIR, exist_ok=True)
    urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)


class VisionAgent(BaseAgent):
    def __init__(self, bus, camera_index: int = 0, target_fps: int = 15):
        super().__init__(name="VisionAgent", bus=bus, topics=["start_pause", "stop_pause"])
        self.camera_index = camera_index
        self.target_fps = target_fps
        self._active = False
        self._cap = None
        self._landmarker = None
        self._start_time = time.time()
        if _HAS_CV:
            self._init_landmarker()

    def _init_landmarker(self) -> None:
        try:
            _ensure_model_downloaded()
            base_options = mp.tasks.BaseOptions(model_asset_path=_MODEL_PATH)
            options = mp.tasks.vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_poses=1,
                min_pose_detection_confidence=0.6,
                min_tracking_confidence=0.6,
            )
            self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        except Exception as exc:  # degradar sin tumbar el programa si falla la descarga/init
            print(f"[VisionAgent] No se pudo inicializar MediaPipe Pose: {exc}")
            self._landmarker = None

    def handle_message(self, message: Message) -> None:
        if message.topic == "start_pause":
            if not _HAS_CV or self._landmarker is None:
                self.send("landmarks", landmarks=None)
                return
            self._active = True
            self._capture_loop()
        elif message.topic == "stop_pause":
            self._active = False

    def _drain_control_messages(self) -> None:
        """Revisa sin bloquear si llegó una orden de detener la pausa."""
        try:
            while True:
                msg = self.inbox.get_nowait()
                if msg.topic == "stop_pause":
                    self._active = False
        except queue.Empty:
            pass

    def _draw_skeleton(self, frame, landmarks_px) -> None:
        for a, b in _CONNECTIONS:
            if a < len(landmarks_px) and b < len(landmarks_px):
                cv2.line(frame, landmarks_px[a], landmarks_px[b], (56, 189, 248), 2)
        for x, y in landmarks_px:
            cv2.circle(frame, (x, y), 4, (34, 197, 94), -1)

    def _capture_loop(self) -> None:
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        delay = 1.0 / self.target_fps
        while self._active and self._running.is_set():
            self._drain_control_messages()
            if not self._active:
                break

            ok, frame = self._cap.read()
            if not ok:
                time.sleep(delay)
                continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int((time.time() - self._start_time) * 1000)
            result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

            landmarks = None
            if result.pose_landmarks:
                pose = result.pose_landmarks[0]  # una sola persona (num_poses=1)
                landmarks = [(lm.x, lm.y, lm.visibility) for lm in pose]
                h, w = frame.shape[:2]
                landmarks_px = [(int(lm.x * w), int(lm.y * h)) for lm in pose]
                self._draw_skeleton(frame, landmarks_px)

            self.send("frame_ready", frame=frame)
            self.send("landmarks", landmarks=landmarks)
            time.sleep(delay)

        if self._cap is not None:
            self._cap.release()
            self._cap = None
