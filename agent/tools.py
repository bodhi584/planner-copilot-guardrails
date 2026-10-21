"""Tool sets for the three experimental setups. The case is fixed by the UI (the planner chose the factory), so tools take
no case_id; the user's question is passed to the engine by code (scope check), not by the model.

  A  raw      : raw_simulate only (every check off), no rules in the prompt
  B  rules    : raw_simulate + agent/prompt_rules.md section of the case in the prompt
  C  guarded  : capabilities, knowledge_lookup, estimate, compare (engine checks on)
"""
import json

from engine import Engine

ARMS = ("A", "B", "C")

TOOL_DOCS = {
    "raw_simulate": 'raw_simulate(params: {name: value}, replications: int) -> per-replication KPI values of one scenario. '
                    'Missing parameters take their default.',
    "capabilities": "capabilities() -> parameters with units, defaults, validated ranges; KPIs; what the model can and cannot answer.",
    "knowledge_lookup": "knowledge_lookup(query: str) -> up to 3 short notes from the method notes and the case card.",
    "estimate": "estimate(kpi: str, params: {name: value}) -> mean and 95% CI of one KPI for one scenario (replications added automatically), plus warnings.",
    "compare": "compare(kpi: str, params_a: {...}, params_b: {...}) -> difference B - A with 95% CI and a verdict "
               "(b_higher, b_lower, not_distinguishable), plus warnings.",
}
ARM_TOOLS = {"A": ["raw_simulate"], "B": ["raw_simulate"], "C": ["capabilities", "knowledge_lookup", "estimate", "compare"]}


class Toolbox:
    def __init__(self, cases_root, arm, case_id, question):
        if arm not in ARMS:
            raise ValueError(f"arm must be one of {ARMS}")
        self.arm, self.case_id, self.question = arm, case_id, question
        self.engine = Engine(cases_root)
        self.raw_engine = Engine(cases_root, checks={k: False for k in ("scope", "units", "validity", "adaptive_reps", "paired")})
        self.names = ARM_TOOLS[arm]

    def card(self):
        return self.engine._card(self.case_id)

    def call(self, name, args):
        """Returns (result dict for the model, engine warning codes, refused?)."""
        if name not in self.names:
            return {"status": "error", "error": f"unknown tool {name}; available: {self.names}"}, [], False
        args = args if isinstance(args, dict) else {}
        if name == "estimate" and "compare" in self.names and "params_a" in args and "params_b" in args:
            name = "compare"  # shape repair: a two-scenario call to estimate is a comparison (rule change 2026-10-17)
        self.last_tool = name
        try:
            if name == "raw_simulate":
                n = int(args.get("replications", 1) or 1)
                r = self.raw_engine.raw_simulate(self.case_id, args.get("params") or {}, max(1, min(n, 100)))
            elif name == "capabilities":
                r = self.engine.capabilities(self.case_id)
            elif name == "knowledge_lookup":
                r = self.engine.knowledge_lookup(str(args.get("query", "")), self.case_id)
            elif name == "estimate":
                r = self.engine.estimate(self.case_id, str(args.get("kpi", "")), args.get("params") or {}, question=self.question)
            else:
                r = self.engine.compare(self.case_id, str(args.get("kpi", "")), args.get("params_a") or {},
                                        args.get("params_b") or {}, question=self.question)
        except Exception as e:  # never crash the flow: the model sees the error and may retry
            return {"status": "error", "error": f"{type(e).__name__}: {e}"}, [], False
        codes = [w["code"] for w in (r.get("warnings") or []) if isinstance(w, dict)]
        return r, codes, r.get("status") == "refused"


def compact(result, limit=3500):
    """Tool result as text for the model: drop bulky fields, cap the length."""
    r = dict(result)
    for k in ("checks", "engine_version", "event_log"):
        r.pop(k, None)
    ex = r.get("extras")
    if isinstance(ex, dict):
        r["extras"] = {k: v for k, v in ex.items() if k != "rows"}
    if "runs" in r:
        r["runs"] = [{k: v for k, v in run.items()} for run in r["runs"]]
    s = json.dumps(r, default=str)
    return s if len(s) <= limit else s[:limit] + " ...(truncated)"
