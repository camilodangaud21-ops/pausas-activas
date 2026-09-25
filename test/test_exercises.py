"""Tests unitarios para los detectores de ejercicio.

Squats, JumpingJacks y ArmRaises son funciones puras: landmarks (33 puntos
(x, y, visibility)) + dt -> progreso. No necesitan cámara ni MediaPipe para
probarse, solo listas de landmarks sintéticos que representan las poses
"arriba"/"abajo" de cada ejercicio.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from exercises.squats import Squats
from exercises.jumping_jacks import JumpingJacks
from exercises.arm_raises import ArmRaises


def _blank_landmarks():
    """33 landmarks por defecto, en el origen, totalmente visibles."""
    return [(0.0, 0.0, 1.0) for _ in range(33)]


# ---------------------------------------------------------------- Squats ---

def _squat_landmarks(bent: bool):
    lm = _blank_landmarks()
    if bent:
        # Rodilla doblada ~90°: cadera y ángulo recto en la rodilla.
        hip, knee, ankle = (0.0, 0.0, 1.0), (0.0, 0.5, 1.0), (0.5, 0.5, 1.0)
    else:
        # Pierna extendida ~180°: cadera, rodilla y tobillo alineados.
        hip, knee, ankle = (0.0, 0.0, 1.0), (0.0, 0.5, 1.0), (0.0, 1.0, 1.0)
    for hip_idx, knee_idx, ankle_idx in ((23, 25, 27), (24, 26, 28)):
        lm[hip_idx], lm[knee_idx], lm[ankle_idx] = hip, knee, ankle
    return lm


def test_squats_counts_one_rep_on_full_cycle():
    squat = Squats(active_seconds_required=60.0)
    squat.update(_squat_landmarks(bent=False), dt=0.1)  # arranca de pie
    squat.update(_squat_landmarks(bent=True), dt=0.1)    # baja
    squat.update(_squat_landmarks(bent=False), dt=0.1)   # sube -> 1 rep
    assert squat.reps == 1


def test_squats_active_seconds_accumulate_while_not_fully_up():
    squat = Squats(active_seconds_required=60.0)
    squat.update(_squat_landmarks(bent=True), dt=1.0)
    squat.update(_squat_landmarks(bent=True), dt=2.0)
    assert squat.active_seconds == 3.0
    assert not squat.is_complete()


def test_squats_is_complete_when_required_seconds_reached():
    squat = Squats(active_seconds_required=2.0)
    squat.update(_squat_landmarks(bent=True), dt=1.0)
    squat.update(_squat_landmarks(bent=True), dt=1.5)
    assert squat.is_complete()


def test_squats_no_landmarks_does_not_crash_or_advance():
    squat = Squats(active_seconds_required=60.0)
    progress = squat.update(None, dt=1.0)
    assert squat.active_seconds == 0.0
    assert progress["reps"] == 0


# --------------------------------------------------------- JumpingJacks ---

def _jumping_jack_landmarks(open_pose: bool):
    lm = _blank_landmarks()
    lm[11] = (0.4, 0.5, 1.0)  # hombro izq
    lm[12] = (0.6, 0.5, 1.0)  # hombro der
    if open_pose:
        lm[15] = (0.3, 0.1, 1.0)  # muñeca izq arriba
        lm[16] = (0.7, 0.1, 1.0)  # muñeca der arriba
        lm[27] = (0.1, 1.0, 1.0)  # tobillo izq separado
        lm[28] = (0.9, 1.0, 1.0)  # tobillo der separado
    else:
        lm[15] = (0.4, 0.8, 1.0)  # muñecas abajo
        lm[16] = (0.6, 0.8, 1.0)
        lm[27] = (0.48, 1.0, 1.0)  # tobillos juntos
        lm[28] = (0.52, 1.0, 1.0)
    return lm


def test_jumping_jacks_counts_one_rep_on_open_close_cycle():
    jj = JumpingJacks(active_seconds_required=60.0)
    jj.update(_jumping_jack_landmarks(open_pose=False), dt=0.1)
    jj.update(_jumping_jack_landmarks(open_pose=True), dt=0.1)
    jj.update(_jumping_jack_landmarks(open_pose=False), dt=0.1)
    assert jj.reps == 1


# ------------------------------------------------------------ ArmRaises ---

def _arm_raise_landmarks(up: bool):
    lm = _blank_landmarks()
    lm[11] = (0.4, 0.5, 1.0)
    lm[12] = (0.6, 0.5, 1.0)
    if up:
        lm[15] = (0.4, 0.1, 1.0)
        lm[16] = (0.6, 0.1, 1.0)
    else:
        lm[15] = (0.4, 0.8, 1.0)
        lm[16] = (0.6, 0.8, 1.0)
    return lm


def test_arm_raises_counts_rep_immediately_on_raise():
    ar = ArmRaises(active_seconds_required=60.0)
    ar.update(_arm_raise_landmarks(up=False), dt=0.1)
    ar.update(_arm_raise_landmarks(up=True), dt=0.1)
    assert ar.reps == 1


def test_arm_raises_second_rep_requires_going_down_first():
    ar = ArmRaises(active_seconds_required=60.0)
    ar.update(_arm_raise_landmarks(up=True), dt=0.1)
    ar.update(_arm_raise_landmarks(up=True), dt=0.1)  # sigue arriba, no cuenta de nuevo
    assert ar.reps == 1
    ar.update(_arm_raise_landmarks(up=False), dt=0.1)
    ar.update(_arm_raise_landmarks(up=True), dt=0.1)
    assert ar.reps == 2
