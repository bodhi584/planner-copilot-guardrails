# Rule-change log
Only failures on the **train** split may lead to a rule change. Validation results are used to choose, not to change rules.

| Date | Who | Rule changed (file / check) | Why | Split that showed it |
|---|---|---|---|---|
| 2026-10-16 | Yu Han | eval/grade.py, flag questions: only `outside_valid_range` counts as the required warning | any code (e.g. `precision_not_reached`) passed before, so a system warning about precision on every answer would score on all flag questions; same effect for all arms | none (found by reading the grader, before any run) |
| 2026-10-16 | Yu Han | eval/grade.py, choice questions: options compared case-insensitively (the answer was lower-cased, the options were not) | A3 options are upper case (INTERLEAVE), so a correct answer counted as cautious; same effect for all arms | run 1 (qwen2.5:7b, A3/A5, all questions): grader bug, not a system change |

## 2026-10-17: after run 2 (two changes, both before run 3)
1. agent/tools.py: a call to `estimate` with `params_a` and `params_b` (two scenarios) is routed to `compare` in condition C
   (shape repair like `_normalise`; content unchanged). Cause: A3-12 in run 2 hit the tool-call limit repeating that call.
2. A2-14 (machine breakdowns) changed from `flag` to `scope`: the JaamSim expert model has no breakdown mechanism
   (Zenodo: failures excluded; adapter raises), so by the three-tier rule (mechanism absent -> refuse) the correct answer
   is a refusal. The old expected value came from the SimPy pilot replica, not from the expert model.
Not changed on purpose: A3-20 (layout question passed the scope check) and A3-13 (model did not compare) stay as found,
to avoid tuning on test items; they are reported as limitations.
