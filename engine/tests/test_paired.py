from conftest import KPI, NORM, codes, make


def test_identical_scenarios_difference_exactly_zero(eng):
    r = eng.compare("FAKE_case", KPI, NORM, NORM)
    assert r["difference_b_minus_a"] == 0 and r["ci95"] == [0, 0]
    assert r["verdict"] == "not_distinguishable" and "not_distinguishable" in codes(r) and r["replications"] == 30


def test_clear_difference_gives_verdict(eng):
    r = eng.compare("FAKE_case", KPI, NORM, {**NORM, "workers": 4})
    assert r["verdict"] == "b_lower" and r["difference_b_minus_a"] < 0 and r["ci95"][1] < 0
    assert r["params_a"]["workers"] == 3 and r["params_b"]["workers"] == 4 and r["params"] is None
    assert r["replications"] < 30 and "not_distinguishable" not in codes(r)
    assert eng.compare("FAKE_case", KPI, {**NORM, "workers": 4}, NORM)["verdict"] == "b_higher"


def test_paired_off_uses_other_replication_indices():
    e = make(checks={"paired": False})
    r = e.compare("FAKE_case", KPI, NORM, NORM)
    assert r["difference_b_minus_a"] != 0  # B runs on replication indices cap+1 = 31.. instead of 1..
    a = e._adapter("FAKE_case")
    assert a.run({"workers": 3, "portfolio": "norm", "shift_length": 480, "rush_share": 10}, 1, start=31)[0] == \
        e._cache[("FAKE_case", '{"portfolio": "norm", "rush_share": 10, "shift_length": 480, "workers": 3}', 31)][0]


def test_adapter_without_start_argument_uses_slow_fallback():
    from conftest import FIXTURES
    from engine import Engine
    from engine.adapters.fake import Adapter

    class Plain:  # run(params, n) only, as in DESIGN.md section 4
        run = lambda self, params, n, event_log=False: Adapter().run(params, n)
    e = Engine(FIXTURES, adapters={"FAKE_case": Plain()}, checks={"paired": False})
    assert e.compare("FAKE_case", KPI, NORM, NORM)["difference_b_minus_a"] != 0


def test_adaptive_off_compare_is_naive_sign():
    r = make(checks={"adaptive_reps": False}).compare("FAKE_case", KPI, NORM, {**NORM, "workers": 4})
    assert r["replications"] == 1 and r["ci95"] is None and r["verdict"] == "b_lower"
