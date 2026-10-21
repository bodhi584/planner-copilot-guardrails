from conftest import KPI, NORM, codes, make


def test_in_range_no_warning(eng):
    assert "outside_valid_range" not in codes(eng.estimate("FAKE_case", KPI, {**NORM, "workers": 4}))


def test_outside_range_warns_but_runs(eng):
    r = eng.estimate("FAKE_case", KPI, {**NORM, "workers": 5})
    assert r["status"] == "ok" and "outside_valid_range" in codes(r)
    assert "workers = 5 is outside the validated range 3–4" in r["warnings"][0]["message"]
    assert "outside_valid_range" in codes(eng.estimate("FAKE_case", KPI, {**NORM, "shift_length": 420}))


def test_unvalidated_parameter_warns_only_when_given(eng):
    assert not any("rush_share" in w["message"] for w in eng.estimate("FAKE_case", KPI, NORM)["warnings"])
    r = eng.estimate("FAKE_case", KPI, {**NORM, "rush_share": 10})
    assert any("rush_share is not validated" in w["message"] for w in r["warnings"])


def test_compare_labels_scenarios(eng):
    r = eng.compare("FAKE_case", KPI, NORM, {**NORM, "workers": 5})
    assert any(w["message"].startswith("B: workers") for w in r["warnings"])


def test_validity_off_no_warning():
    e = make(checks={"validity": False})
    assert "outside_valid_range" not in codes(e.estimate("FAKE_case", KPI, {"portfolio": "norm", "workers": 5, "rush_share": 20}))
