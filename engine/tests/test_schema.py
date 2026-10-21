import json
from pathlib import Path

import jsonschema
import pytest

from engine.result import Capabilities, Lookup, RawRun, Result
from conftest import KPI, NORM, make

SCHEMA = json.loads((Path(__file__).parents[1] / "result.schema.json").read_text())


def test_schema_file_is_current():
    assert SCHEMA == Result.model_json_schema(), "run: python -m engine.result"


def results(e):
    return [e.estimate("FAKE_case", KPI, NORM), e.estimate("FAKE_case", KPI, {**NORM, "workers": 5}),
            e.estimate("FAKE_case", "profit", NORM), e.estimate("FAKE_case", KPI, {}), e.estimate("NOPE", KPI, {}),
            e.estimate("FAKE_case", KPI, {**NORM, "shift_length": 8}),
            e.compare("FAKE_case", KPI, NORM, {**NORM, "workers": 4}), e.compare("FAKE_case", KPI, NORM, NORM)]


@pytest.mark.parametrize("engine_kw", [{}, {"checks": {"adaptive_reps": False, "paired": False}}])
def test_estimate_and_compare_validate(engine_kw):
    for r in results(make(**engine_kw)):
        jsonschema.validate(r, SCHEMA)
        Result.model_validate(r)
        json.dumps(r)


def test_required_fields_and_codes(eng):
    r = eng.estimate("FAKE_case", KPI, {**NORM, "workers": 5})
    assert {"status", "tool", "case_id", "engine_version", "kpi", "unit", "params", "mean", "ci95", "ci95_half_width", "replications",
            "precision_reached", "warnings", "extras", "event_log", "checks", "refusal", "error"} <= set(r)
    assert r["event_log"] is None and r["unit"] == "h" and r["engine_version"] == "1.0.0"
    bad = dict(r, warnings=[{"code": "made_up", "message": "x"}])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def test_other_tools_validate_against_models(eng):
    Capabilities.model_validate(eng.capabilities("FAKE_case"))
    Capabilities.model_validate(eng.capabilities("NOPE"))
    Lookup.model_validate(eng.knowledge_lookup("replications", "FAKE_case"))
    raw = eng.raw_simulate("FAKE_case", NORM, 3)
    RawRun.model_validate(raw)
    assert len(raw["runs"]) == 3 and set(raw["runs"][0]) == {KPI, "late_orders"}
    assert "warnings" not in raw and eng.raw_simulate("FAKE_case", {"portfolio": "norm", "workers": 99, "x": 1}, 1)["status"] == "ok"
