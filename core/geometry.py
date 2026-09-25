"""Utilidades geométricas para interpretar landmarks de MediaPipe Pose."""

import math
from typing import Tuple


def angle_2d(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    """Ángulo en grados, medido en el vértice b, formado por los puntos a-b-c.

    Los puntos son tuplas (x, y) en coordenadas normalizadas de MediaPipe
    (0..1). Se usa, por ejemplo, para medir el ángulo de la rodilla en las
    sentadillas: a=cadera, b=rodilla, c=tobillo.
    """
    ax, ay = a[0] - b[0], a[1] - b[1]
    cx, cy = c[0] - b[0], c[1] - b[1]
    mag_a = math.hypot(ax, ay)
    mag_c = math.hypot(cx, cy)
    if mag_a * mag_c == 0:
        return 0.0
    cos_angle = (ax * cx + ay * cy) / (mag_a * mag_c)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))


def distance_2d(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])
