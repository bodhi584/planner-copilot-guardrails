"""Flow tests with a scripted model on the fake case of the engine tests (no LLM, no real simulator)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine" / "tests"))

from conftest import FIXTURES, KPI  # noqa: E402

from agent import flow  # noqa: E402
from agent.flow import _parse, answer  # noqa: E402
from agent.llm import ScriptedLLM  # noqa: E402

CASE = "FAKE_case"


def j(**kw):
    return json.dumps(kw)


def test_parse_handles_fences_and_prose():
    assert _parse('Sure!\n```json\n{"action": "final", "value": 3}\n```') == {"action": "final", "value": 3}
    assert _parse("no json") is None


def test_guarded_flow_copies_engine_warnings_not_model_claims():
    llm = ScriptedLLM([j(action="tool", tool="estimate", args={"kpi": KPI, "params": {"workers": 6, "portfolio": "norm"}}),
                       j(action="final", value=1.0, refused=False, warnings=["made_up"], text="ok")])
    r = answer("What if 6 workers?", CASE, "C", llm, cases_root=FIXTURES)
    assert r["tools"][0]["status"] == "ok"
    assert "outside_valid_range" in r["flags"] and "made_up" not in r["flags"]


def test_engine_refusal_marks_answer_refused():
    llm = ScriptedLLM([j(action="tool", tool="estimate", args={"kpi": "euro_cost", "params": {}}),
                       j(action="final", value=None, refused=False, text="cannot")])
    r = answer("How much does it cost?", CASE, "C", llm, cases_root=FIXTURES)
    assert r["refused"] is True and r["value"] is None


def test_raw_arm_has_no_guarded_tools_and_keeps_model_flags():
    llm = ScriptedLLM([j(action="tool", tool="estimate", args={"kpi": KPI}),
                       j(action="tool", tool="raw_simulate", args={"params": {"workers": 6, "portfolio": "norm"}, "replications": 2}),
                       j(action="final", value=2.5, warnings=["outside_valid_range"], text="ok")])
    r = answer("6 workers?", CASE, "A", llm, cases_root=FIXTURES)
    assert r["tools"][0]["status"] == "error" and r["tools"][1]["status"] == "ok"
    assert r["flags"] == ["outside_valid_range"] and r["value"] == 2.5


def test_bad_replies_end_in_refusal():
    r = answer("?", CASE, "C", ScriptedLLM(["blah", "blah", "blah"]), cases_root=FIXTURES)
    assert r["refused"] is True


def test_tool_call_limit():
    calls = [j(action="tool", tool="capabilities", args={})] * (flow.MAX_TOOL_CALLS + 2)
    r = answer("?", CASE, "C", ScriptedLLM(calls), cases_root=FIXTURES)
    assert len(r["tools"]) == flow.MAX_TOOL_CALLS and r["refused"] is True


def test_estimate_with_two_scenarios_is_routed_to_compare():
    llm = ScriptedLLM([j(action="tool", tool="estimate", args={"kpi": KPI, "params_a": {"workers": 3, "portfolio": "norm"},
                                                            "params_b": {"workers": 3, "portfolio": "norm"}}),
                       j(action="final", value=None, choice="no_difference", text="same")])
    r = answer("Which is better?", CASE, "C", llm, cases_root=FIXTURES)
    assert r["tools"][0]["tool"] == "compare" and r["tools"][0]["status"] == "ok"


def test_value_check_flags_a_number_no_tool_returned():
    llm = ScriptedLLM([j(action="tool", tool="estimate", args={"kpi": KPI, "params": {"workers": 3, "portfolio": "norm"}}),
                       j(action="final", value=987654.0, refused=False, text="made up")])
    r = answer("Overtime with 3 workers?", CASE, "C", llm, cases_root=FIXTURES)
    assert "value_not_from_tool" in r["flags"]


def test_value_check_accepts_the_tool_mean_rounded():
    probe = answer("Overtime with 3 workers?", CASE, "C",
                   ScriptedLLM([j(action="tool", tool="estimate", args={"kpi": KPI, "params": {"workers": 3, "portfolio": "norm"}}),
                                j(action="final", value=None, refused=True, text="probe")]), cases_root=FIXTURES)
    assert probe["tools"][0]["status"] == "ok"
    from agent.tools import Toolbox
    res, _, _ = Toolbox(FIXTURES, "C", CASE, "q").call("estimate", {"kpi": KPI, "params": {"workers": 3, "portfolio": "norm"}})
    llm = ScriptedLLM([j(action="tool", tool="estimate", args={"kpi": KPI, "params": {"workers": 3, "portfolio": "norm"}}),
                       j(action="final", value=round(res["mean"], 2), refused=False, text="ok")])
    r = answer("Overtime with 3 workers?", CASE, "C", llm, cases_root=FIXTURES)
    assert "value_not_from_tool" not in r["flags"]


def test_value_from_tool_unit_conversion():
    assert flow.value_from_tool(120.0, [2.0])        # 2 h given as 120 min
    assert flow.value_from_tool(35.0, [0.35])        # fraction given as percent
    assert not flow.value_from_tool(50.0, [2.0, 0.35])
