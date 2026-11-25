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

## 2026-11-25: rules frozen for the test (eval/PROTOCOL.md)
No check, case card (A1–A5), prompt, prompt rule or grading rule changes from here on (commit `35a22f5`).
Added the same day, before the freeze and before any test answer: experiment switches in `eval/run.py`
(`--off`, `--temperature`, `--seed-base`, `--label`; defaults change nothing) and the sealed test questions
(`cases/*/questions_test.csv`, hashes in `eval/test_set.sha256`).
2026-11-25, after the freeze, before any test answer (harness only, no rule): `cases/A2_sme/adapter.py` joins the Java
classpath with `os.pathsep` (was ":"), so A2 also runs on Windows; results on Linux unchanged. Added `eval/run_windows.ps1`,
`eval/grade_all.py` (calls `grade.grade` unchanged for several question files) and `eval/analyse.py` (protocol section 4).
2026-11-25, during the runs (harness only): run T3 stopped at once because `--label -off_<check>` was read by argparse as a new
option; `eval/run_windows.ps1` now passes `--label=-off_<check>`. No answer had been produced; T3 was then run as planned.
