from conftest import KPI, NORM, codes, make


def test_precision_reached_with_relative_target():
    r = make(rel_precision=0.5).estimate("FAKE_case", KPI, {"portfolio": "over20"})
    assert r["precision_reached"] is True and "precision_not_reached" not in codes(r)
    assert r["ci95_half_width"] <= 0.5 * abs(r["mean"]) and r["ci95"][0] < r["mean"] < r["ci95"][1]
    assert r["replications"] >= 10  # replications.ours_min


def test_abs_precision_of_kpi_is_used(eng):
    r = eng.estimate("FAKE_case", "late_orders", NORM)  # abs_precision 2.0
    assert r["precision_reached"] is True and r["ci95_half_width"] <= 2.0 and r["replications"] < 30


def test_cap_gives_warning(eng):
    r = eng.estimate("FAKE_case", KPI, NORM)  # 1 % of a small mean is out of reach; cap = 30
    assert r["replications"] == 30 and r["precision_reached"] is False and "precision_not_reached" in codes(r)


def test_batch_size_and_start():
    r = make(rel_precision=1e-9, batch=7).estimate("FAKE_case", KPI, NORM)
    assert r["replications"] == 30  # 10, 17, 24, 30 (capped)


def test_adaptive_off_fixed_replications_no_ci():
    r = make(checks={"adaptive_reps": False}).estimate("FAKE_case", KPI, NORM)
    assert r["replications"] == 1 and r["ci95"] is None and r["ci95_half_width"] is None and r["precision_reached"] is None
    assert make(checks={"adaptive_reps": False}, replications_when_off=4).estimate("FAKE_case", KPI, NORM)["replications"] == 4


def test_extras_are_means_and_bottleneck(eng):
    r = eng.estimate("FAKE_case", KPI, NORM)
    u = r["extras"]["utilisation"]
    assert set(u) == {"SheetLaser", "TubeLaser", "Bending"} and r["extras"]["bottleneck"] == "SheetLaser"
    runs = eng._adapter("FAKE_case").run({"workers": 3, "portfolio": "norm", "shift_length": 480, "rush_share": 10}, 30)
    assert abs(u["SheetLaser"] - sum(x["_extras"]["utilisation"]["SheetLaser"] for x in runs) / 30) < 1e-4


def test_cache_does_not_call_adapter_again(eng):
    a = eng._adapter("FAKE_case")
    calls = []
    orig = a.run
    a.run = lambda *x, **k: (calls.append(1), orig(*x, **k))[1]
    eng.estimate("FAKE_case", KPI, NORM)
    n = len(calls)
    eng.estimate("FAKE_case", KPI, NORM)
    assert len(calls) == n


def test_simulator_failure_is_reported():
    class Boom:
        def run(self, params, n, event_log=False):
            raise RuntimeError("jaamsim crashed")
    from conftest import FIXTURES
    from engine import Engine
    r = Engine(FIXTURES, adapters={"FAKE_case": Boom()}).estimate("FAKE_case", KPI, NORM)
    assert r["status"] == "error" and r["error"]["code"] == "simulator_failed" and "jaamsim crashed" in r["error"]["message"]
