import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.stats_store import StatsStore


def test_add_exercise_completion_increments_counters(tmp_path):
    store = StatsStore(path=os.path.join(str(tmp_path), "stats.json"))
    store.add_exercise_completion("Sentadillas")
    store.add_exercise_completion("Sentadillas")
    store.add_exercise_completion("Saltos de tijera")

    summary = store.today_summary()
    assert summary["pauses_completed"] == 3
    assert summary["exercises"]["Sentadillas"] == 2
    assert summary["exercises"]["Saltos de tijera"] == 1


def test_increment_generic_field(tmp_path):
    store = StatsStore(path=os.path.join(str(tmp_path), "stats.json"))
    store.increment("emergency_unlocks")
    store.increment("emergency_unlocks")
    assert store.today_summary()["emergency_unlocks"] == 2


def test_persists_across_instances(tmp_path):
    path = os.path.join(str(tmp_path), "stats.json")
    StatsStore(path=path).add_exercise_completion("Estiramiento de brazos")
    summary = StatsStore(path=path).today_summary()
    assert summary["pauses_completed"] == 1
