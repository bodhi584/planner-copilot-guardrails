from conftest import KPI, NORM, make


def test_unknown_kpi_refused(eng):
    r = eng.estimate("FAKE_case", "profit", NORM)
    assert r["status"] == "refused" and "profit" in r["refusal"]["reason"]
    assert r["refusal"]["cannot_answer"] == ["costs in euros", "buying or removing machines"]
    assert r["mean"] is None


def test_unknown_parameter_refused(eng):
    r = eng.estimate("FAKE_case", KPI, {**NORM, "machines": 5})
    assert r["status"] == "refused" and "machines" in r["refusal"]["reason"]


def test_refuse_keyword_in_question(eng):
    r = eng.estimate("FAKE_case", KPI, NORM, question="How many euros would a 4th worker save?")
    assert r["status"] == "refused" and "euro" in r["refusal"]["reason"]
    assert eng.estimate("FAKE_case", KPI, NORM, question="How long is the overtime?")["status"] == "ok"


def test_compare_checks_both_scenarios(eng):
    assert eng.compare("FAKE_case", KPI, NORM, {**NORM, "oven": 1})["status"] == "refused"


def test_unknown_case_is_error(eng):
    for case in ("NOPE", "../etc"):
        r = eng.estimate(case, KPI, {})
        assert r["status"] == "error" and r["error"]["code"] == "unknown_case"
    assert eng.capabilities("NOPE")["error"]["code"] == "unknown_case"


def test_scope_off_passes_unknown_names_to_adapter():
    e = make(checks={"scope": False})
    assert e.estimate("FAKE_case", KPI, {**NORM, "machines": 5}, question="cost in euro?")["status"] == "ok"
    r = e.estimate("FAKE_case", "profit", NORM)  # adapter has no such KPI -> not swallowed
    assert r["status"] == "error" and r["error"]["code"] == "simulator_failed"


def test_capabilities(eng):
    c = eng.capabilities("FAKE_case")
    assert c["status"] == "ok" and [p["name"] for p in c["parameters"]][:2] == ["workers", "portfolio"]
    assert c["parameters"][2]["hint"].startswith("looks like hours") and c["outputs"][1]["abs_precision"] == 2.0
