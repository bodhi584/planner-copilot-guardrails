# Guardrail engine

The code layer between the language model and the simulators: the model picks a tool and parameter values, the engine runs the checks (scope, units, validated range, adaptive replications, paired comparison) and returns numbers, confidence intervals and warnings. Design: [DESIGN.md](DESIGN.md).

## Python API
```python
from engine import Engine
e = Engine("cases")                                   # adapters load from cases/<case_id>/adapter.py
e.capabilities("A2_sme")
e.estimate("A2_sme", "overtime_after_shift", {"workers": 4, "portfolio": "busy week", "shift_length": {"value": 8, "unit": "h"}})
e.compare("A2_sme", "overtime_after_shift", {"workers": 3, "portfolio": "norm"}, {"workers": 4, "portfolio": "norm"})
```
Options: `Engine(cases_root, adapters=None, checks={"scope": False, ...}, rel_precision=0.01, batch=10, replications_when_off=1)`.
All methods return plain dicts that validate against `result.schema.json` (regenerate with `python -m engine.result`).

## MCP server (stdio)
```bash
python -m engine.server --cases cases                         # capabilities, knowledge_lookup, estimate, compare
python -m engine.server --cases cases --raw                   # + raw_simulate (no checks; evaluation setups A and B)
python -m engine.server --cases cases --off scope,validity    # ablation: switch checks off (scope, units, validity, adaptive_reps, paired)
```
Results with `status: error` become MCP tool errors (`isError`) with message and hint; refusals are normal results.

## Adding a simulation model
1. Write `cases/<case_id>/case_card.yaml` with the fields in DESIGN.md section 5 (validated ranges, `hard_min`/`hard_max` + `hint`, `allowed`, `abs_precision`, `refuse_keywords`, `synonyms`).
2. Copy `engine/adapters/fake.py` to `cases/<case_id>/adapter.py` and replace the toy model by a call to your simulator. Contract: DESIGN.md section 4 (`run(params, n, start=1)`, replication i always on random stream i).
3. Test with `Engine("cases").estimate(...)` before connecting a model.
