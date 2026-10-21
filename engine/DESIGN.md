# Guardrail engine · design

The engine is the code layer between the LLM and the simulation models. The LLM only chooses **which tool** and **which parameter values**; every number comes from the simulator, and every warning, refusal and statistic is set by this code. Basis: LLM-Modulo (Kambhampati et al. 2024: the model proposes, external critics verify) and the validity domain of a simulation model (Sargent 2015).

```
LLM (workflow) ──▶ core.Engine (or MCP server.py) ──▶ ──▶ checks ──▶ stats (adaptive / paired) ──▶ adapter ──▶ simulator
                                         ▲ case_card.yaml (scope, units, valid ranges)     (one adapter per case)
```

## 1. Four tools

| Tool | Input | What the code does |
|---|---|---|
| `capabilities(case_id)` | case id | Returns parameters (unit, default, valid range, allowed values), KPIs, `can_answer`, `cannot_answer`, published scenarios. No simulation. |
| `knowledge_lookup(query, case_id?)` | free text | Keyword search over method notes (`engine/kb.py`) and the case card (meanings, notes, cannot_answer). Returns at most 3 snippets with their source. |
| `estimate(case_id, kpi, params)` | one scenario | Checks → adaptive replications → mean and 95% CI of one KPI, plus chart extras. |
| `compare(case_id, kpi, params_a, params_b)` | two scenarios | Checks on both → paired replications with common random numbers → mean difference (B − A), CI, verdict. |

Not one of the four, but needed for evaluation setups A and B: `raw_simulate(case_id, params, replications)` returns the per-replication KPI values with **every check off** (no refusal, no warnings, no CI). Served only when the server is started with `--raw`.

## 2. Checks (in this order; each can be switched off for the ablation)

| # | Flag | Rule | Outcome |
|---|---|---|---|
| 1 | `scope` | KPI must be in `outputs`; every parameter name must be in `parameters`; question text (if the caller passes `question`) must not contain a case card `refuse_keywords` entry | `status: refused`, reason + `cannot_answer` list |
| 2 | `units` | Value must be numeric (or in `allowed`); `{value, unit}` objects are converted (min ↔ h ↔ day, % ↔ fraction); value must lie in `[hard_min, hard_max]` | `status: error` with `hint` (MCP `isError: true`, so the LLM can correct itself) |
| 3 | `validity` | Value outside `[valid_min, valid_max]`, or a parameter marked `validated: false` | runs anyway, adds warning `outside_valid_range` |
| 4 | `adaptive_reps` | Add replications in batches until the 95% CI half-width ≤ `rel_precision` × \|mean\| (default 1%) or ≤ the KPI's `abs_precision`; never fewer than `replications.ours_min`, never more than `replications.max` (default 100) | if the cap is hit: warning `precision_not_reached` |
| 5 | `paired` | `compare` uses the same replication indices (common random numbers) for A and B, stops when the CI of the difference excludes 0 or at the cap | verdict `b_higher` / `b_lower` / `not_distinguishable` (+ warning `not_distinguishable`) |

Switched off: `scope` off → unknown names go to the adapter as they are; `units` off → no conversion, no hard bounds; `validity` off → no warning; `adaptive_reps` off → fixed `replications_when_off` (default 1, no CI); `paired` off → B uses different replication indices than A.

Warning codes are fixed strings, because the grader reads them: `outside_valid_range`, `precision_not_reached`, `not_distinguishable`. Missing parameters take the case-card default silently (the resolved values are listed in `params`); a missing parameter without default is an error `missing_parameter`. The LLM may not add or remove warnings: the workflow copies them from the result.

## 3. Result format (chart-ready, event log on request)

```json
{
  "status": "ok | refused | error",
  "tool": "estimate", "case_id": "A2_sme", "engine_version": "1.0.0",
  "kpi": "overtime_after_shift", "unit": "h",
  "params": {"workers": 4, "portfolio": "over20", "shift_length": 480},
  "mean": 3.66, "ci95": [3.55, 3.77], "ci95_half_width": 0.11, "replications": 30, "precision_reached": true,
  "warnings": [{"code": "outside_valid_range", "message": "workers = 5 is outside the validated range 3–4: indicative only"}],
  "extras": {"utilisation": {"SheetLaser": 0.36}, "bottleneck": "SheetLaser", "orders": [{"id": 17, "due": "...", "finish": "...", "late": true}]},
  "event_log": null,
  "checks": {"scope": true, "units": true, "validity": true, "adaptive_reps": true, "paired": true},
  "refusal": null, "error": null
}
```
- `compare` adds `"difference_b_minus_a"`, `"verdict"` and returns `params_a` / `params_b` instead of `params`.
- `extras` holds whatever the adapter reports beyond the KPI (means over replications); `event_log` is a file path, filled only when the caller passes `event_log: true` and the adapter supports it.
- `refusal = {"reason": "...", "cannot_answer": [...]}`; `error = {"code": "missing_parameter | implausible_value | wrong_type | unknown_case | simulator_failed", "message": "...", "hint": "..."}`. (An unknown parameter or KPI name is a scope refusal, not an error.)
- JSON Schema: `engine/result.schema.json`. The MCP server derives each tool's `outputSchema` from the same Pydantic model.

## 4. Adapter interface

One file per case: `cases/<case_id>/adapter.py` with a class `Adapter`:

```python
class Adapter:
    case_id = "A2_sme"
    supports_event_log = False
    def run(self, params: dict, n: int, event_log: bool = False) -> list[dict]:
        """Run replications 1..n of the scenario `params` (already checked, in case-card units).
        Replication i must always use the same random stream i, so that two scenarios
        with the same i share common random numbers. Return one dict per replication:
        {"<kpi>": float, ..., "_extras": {...optional...}, "_event_log": "path or None"}."""
```
- The engine may call `run` again with a larger `n`; adapters may re-run from 1 (JaamSim does) or cache.
- Optional: accept `start=1` (replications `start .. start+n-1`). Only the "paired off" ablation uses it (B starts at cap+1); without it the engine runs `cap+n` replications and drops the first `cap`.
- Adapter errors are returned as `status: error`, code `simulator_failed`, never swallowed.
- New cases: copy `engine/adapters/fake.py` as a template.

## 5. Case card fields the engine reads (all optional except the first line)

Required (already in the template): `parameters[].name/unit/default`, `outputs[].name/unit`, `replications.ours_min`, `cannot_answer`.
Optional, new in v1: `parameters[].valid_min/valid_max` (already used), `allowed`, `hard_min/hard_max`, `hint`, `validated: false`; `outputs[].abs_precision`; `replications.max`; `refuse_keywords` (e.g. `["euro", "cost", "buy", "new machine"]`).

## 6. Files

```
engine/core.py        Engine: capabilities, knowledge_lookup, estimate, compare, raw_simulate
engine/checks.py      scope, units, validity (pure functions)
engine/stats.py       CI, adaptive loop, paired loop
engine/casecard.py    load + validate case_card.yaml
engine/kb.py          method notes + case card index
engine/result.py      Pydantic result model + JSON schema export
engine/server.py      MCP server (mcp >= 2, MCPServer, stdio); --raw adds raw_simulate; --off scope,validity,... for the ablation
engine/adapters/fake.py   deterministic test model (template for new cases)
engine/tests/         pytest, one file per check + stats + server
```
