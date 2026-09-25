import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.geometry import angle_2d, distance_2d


def test_angle_straight_leg_is_180():
    hip, knee, ankle = (0, 0), (0, 1), (0, 2)
    assert math.isclose(angle_2d(hip, knee, ankle), 180.0, abs_tol=1e-6)


def test_angle_right_angle_is_90():
    hip, knee, ankle = (0, 0), (0, 1), (1, 1)
    assert math.isclose(angle_2d(hip, knee, ankle), 90.0, abs_tol=1e-6)


def test_angle_degenerate_points_returns_zero():
    # a y b coinciden -> magnitud cero -> se evita división por cero
    assert angle_2d((0, 0), (0, 0), (1, 1)) == 0.0


def test_distance_2d():
    assert math.isclose(distance_2d((0, 0), (3, 4)), 5.0, abs_tol=1e-6)
