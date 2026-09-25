import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agents.scheduler_agent as scheduler_module
from core.message_bus import MessageBus


def _make_scheduler(tmp_path):
    # Aísla el archivo de posposiciones para que el test no dependa ni
    # ensucie el data/postpones.json real del proyecto.
    scheduler_module._POSTPONES_PATH = os.path.join(tmp_path, "postpones.json")
    bus = MessageBus()
    # threading.Thread.__init__ ya deja todo listo sin necesidad de start().
    return scheduler_module.SchedulerAgent(bus, interval_minutes=30)


def test_postpone_allowed_up_to_daily_max(tmp_path):
    sched = _make_scheduler(str(tmp_path))
    results = []
    sched.send = lambda topic, **payload: results.append((topic, payload))

    for _ in range(scheduler_module.MAX_POSTPONES_PER_DAY):
        sched._handle_postpone()

    allowed_flags = [payload["allowed"] for topic, payload in results if topic == "postpone_result"]
    assert allowed_flags == [True] * scheduler_module.MAX_POSTPONES_PER_DAY


def test_postpone_denied_after_daily_max(tmp_path):
    sched = _make_scheduler(str(tmp_path))
    results = []
    sched.send = lambda topic, **payload: results.append((topic, payload))

    for _ in range(scheduler_module.MAX_POSTPONES_PER_DAY + 1):
        sched._handle_postpone()

    last_topic, last_payload = results[-1]
    assert last_topic == "postpone_result"
    assert last_payload["allowed"] is False


def test_postpone_count_persists_across_instances(tmp_path):
    sched1 = _make_scheduler(str(tmp_path))
    sched1.send = lambda topic, **payload: None
    sched1._handle_postpone()

    sched2 = _make_scheduler(str(tmp_path))
    assert sched2._postpones_today == 1
