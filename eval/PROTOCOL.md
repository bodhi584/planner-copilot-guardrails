# Evaluation protocol v1 (written and frozen on 25 Nov 2026, before any test run)

Development runs 1–5 (`results/`) tuned the rules on the same 80 questions they report. This protocol fixes, before the
first test answer exists, what is run, on which questions, and how it is judged. Nothing below changes after the first
test run; a harness bug found later is fixed, logged in `rule_changes.md` and every affected run is repeated.

## 1. What is frozen

| Part | Frozen state |
|---|---|
| Check engine, case cards A1–A5, prompts, prompt rules (setup B), grader | git tag `eval-freeze-v1` |
| Value check (`value_not_from_tool`) | on in setup C (added after the development runs, so it is new to every model) |
| Test questions | `cases/*/questions_test.csv` (split = `test`), SHA-256 in `eval/test_set.sha256` |

Only the experiment switches added for this protocol (`eval/run.py --off --temperature --seed-base --label`) are new;
they change nothing when left at their defaults.

## 2. Test set

- **Sealed questions on the four development cases:** 40 questions, 10 per case, written by `eval/make_test_questions.py`
  with the same reference and tolerance rules as the development questions. Each asks a KPI, scenario or wording not
  in `questions.csv`. Mix: 16 numeric, 8 choice, 7 flag (answer with the `outside_valid_range` warning), 9 scope (refuse).
- **A new case, A6 (steel works, torpedo-car transport, AnyLogic):** a case no rule was tuned on. Its case card is
  written from the course data and the validated AnyLogic model, and its questions are sealed (hash added to
  `test_set.sha256`) before any language model answers a question on A6.

## 3. Runs

Local Ollama on one RTX 3060 (12 GB); one answer per question, setup and repeat.

| Run | Models | Setups | Questions | Temperature / seeds | Purpose |
|---|---|---|---|---|---|
| T1 main | qwen2.5:7b-instruct, llama3.1:8b, gemma2:9b | A, B, C | test | 0 / seed 0 | main result |
| T2 repeats | qwen2.5:7b-instruct | A, B, C | test | 0.7 / seeds 1, 2, 3 | spread under sampling |
| T3 ablation | qwen2.5:7b-instruct | C with one check off: scope, units, validity, adaptive_reps, paired, value_check | test | 0 / seed 0 | what each check contributes |
| D4 rerun | llama3.1:8b | A, B, C | development (80) | 0 / seed 0 | per-answer files that run 4 did not save |

Mistral 7B is dropped: in run 4 it did not end its turns (no answer in 5 h); this is reported, not retried.

## 4. Grading and statistics

- Every answer is graded by `eval/grade.py` unchanged: **correct / cautious / confidently wrong**.
- **Primary endpoint:** number of confidently wrong answers. **H1:** setup C has fewer confidently wrong answers than
  setup B, for each model. **Secondary:** number of correct answers (**H2:** C > B), correct refusals on scope
  questions, warnings on flag questions.
- C and B answer the same questions, so the comparison is paired: exact McNemar test on the discordant pairs, one-sided,
  α = 0.05 per model, Holm correction across the three models. Proportions get Wilson 95 % confidence intervals.
- Targets set in the proposal, reported as met or not met: ≥ 90 % correct, ≤ 2 % confidently wrong, ≥ 90 % correct
  refusals.
- Results are reported per case and for A6 separately, because A6 is the only case no rule was tuned on.
