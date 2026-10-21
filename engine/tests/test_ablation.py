"""Each flag off changes behaviour as DESIGN.md section 2 says (details in the per-check test files)."""
import pytest

from conftest import KPI, NORM, codes, make


def test_all_on_by_default(eng):
    assert eng.estimate("FAKE_case", KPI, NORM)["checks"] == dict(scope=True, units=True, validity=True, adaptive_reps=True, paired=True)


def test_flags_are_reported():
    assert make(checks={"units": False})._safe  # constructor accepts it
    r = make(checks={"units": False, "paired": False}).estimate("FAKE_case", KPI, NORM)
    assert r["checks"]["units"] is False and r["checks"]["paired"] is False and r["checks"]["scope"] is True


def test_unknown_flag_rejected():
    with pytest.raises(ValueError):
        make(checks={"magic": False})


@pytest.mark.parametrize("flag,call,on,off", [
    ("scope", lambda e: e.estimate("FAKE_case", KPI, {**NORM, "x": 1})["status"], "refused", "ok"),
    ("units", lambda e: e.estimate("FAKE_case", KPI, {**NORM, "shift_length": 8})["status"], "error", "ok"),
    ("validity", lambda e: "outside_valid_range" in codes(e.estimate("FAKE_case", KPI, {**NORM, "workers": 5})), True, False),
    ("adaptive_reps", lambda e: e.estimate("FAKE_case", KPI, NORM)["replications"], 30, 1),
    ("paired", lambda e: e.compare("FAKE_case", KPI, NORM, NORM)["difference_b_minus_a"] == 0, True, False),
])
def test_flag_changes_behaviour(flag, call, on, off):
    assert call(make()) == on
    assert call(make(checks={flag: False})) == off
