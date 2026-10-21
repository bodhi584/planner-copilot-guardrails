from conftest import KPI, NORM, codes, make


def p(eng, **given):
    return eng.estimate("FAKE_case", KPI, {**NORM, **given})


def test_defaults_are_silent_and_listed(eng):
    r = p(eng)
    assert r["status"] == "ok" and r["params"] == {"workers": 3, "portfolio": "norm", "shift_length": 480, "rush_share": 10}
    assert "assumption_default_used" not in codes(r)


def test_missing_parameter_without_default(eng):
    r = eng.estimate("FAKE_case", KPI, {})
    assert r["status"] == "error" and r["error"]["code"] == "missing_parameter" and "over20" in r["error"]["hint"]


def test_unit_conversion(eng):
    assert p(eng, shift_length={"value": 8, "unit": "h"})["params"]["shift_length"] == 480
    assert p(eng, shift_length={"value": 1, "unit": "day"})["params"]["shift_length"] == 1440
    assert p(eng, shift_length={"value": 480, "unit": "min"})["params"]["shift_length"] == 480
    assert p(eng, rush_share={"value": 0.2, "unit": "fraction"})["params"]["rush_share"] == 20
    assert p(eng, rush_share={"value": 30, "unit": "%"})["params"]["rush_share"] == 30


def test_bad_unit(eng):
    r = p(eng, shift_length={"value": 8, "unit": "kg"})
    assert r["status"] == "error" and r["error"]["code"] == "wrong_type"


def test_hard_bounds_give_hint(eng):
    r = p(eng, shift_length=8)
    assert r["status"] == "error" and r["error"]["code"] == "implausible_value"
    assert r["error"]["hint"] == "looks like hours; give minutes, 8 h = 480"
    assert p(eng, workers=0)["error"]["code"] == "implausible_value"
    assert p(eng, rush_share={"value": 2, "unit": "fraction"})["error"]["code"] == "implausible_value"  # 200 %


def test_wrong_type(eng):
    for bad in ("many", True, None, [3]):
        assert p(eng, workers=bad)["error"]["code"] == "wrong_type"


def test_allowed_values_case_insensitive_and_synonyms(eng):
    assert p(eng, portfolio="NORM")["params"]["portfolio"] == "norm"
    assert eng.estimate("FAKE_case", KPI, {"portfolio": "Busy Week"})["params"]["portfolio"] == "over20"
    assert p(eng, workers="extra operator")["params"]["workers"] == 4
    r = eng.estimate("FAKE_case", KPI, {"portfolio": "huge"})
    assert r["error"]["code"] == "wrong_type" and "norm" in r["error"]["hint"]


def test_units_off_takes_values_as_given():
    e = make(checks={"units": False})
    r = e.estimate("FAKE_case", KPI, {"portfolio": "norm", "shift_length": {"value": 8, "unit": "h"}, "workers": 0.5})
    assert r["status"] == "ok" and r["params"]["shift_length"] == 8 and r["params"]["workers"] == 0.5
