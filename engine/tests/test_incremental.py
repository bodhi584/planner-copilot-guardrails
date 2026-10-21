"""Adapters that accept `start` are only asked for the replications the engine does not have yet."""
from engine.adapters.fake import Adapter as Fake

from conftest import FIXTURES, KPI, NORM
from engine import Engine


class Counting(Fake):
    def __init__(self):
        super().__init__()
        self.asked = []

    def run(self, params, n, event_log=False, start=1):
        self.asked.append((start, n))
        return super().run(params, n, event_log=event_log, start=start)


def test_only_missing_replications_are_run():
    a = Counting()
    e = Engine(FIXTURES, adapters={"FAKE_case": a}, rel_precision=1e-9)  # force growth to the cap
    r = e.estimate("FAKE_case", KPI, NORM)
    starts = [s for s, _ in a.asked]
    assert sum(n for _, n in a.asked) == r["replications"]          # every replication simulated once
    assert starts == sorted(set(starts)) and starts[0] == 1          # contiguous, no re-runs from 1


def test_incremental_equals_full_run():
    a = Counting()
    vals = [x[KPI] for x in Engine(FIXTURES, adapters={"FAKE_case": a}, rel_precision=1e-9)._getter(
        "FAKE_case", a, {"workers": 3, "portfolio": "norm", "shift_length": 480, "rush_share": 10})(25)]
    full = [x[KPI] for x in Fake().run({"workers": 3, "portfolio": "norm", "shift_length": 480, "rush_share": 10}, 25)]
    assert vals == full
