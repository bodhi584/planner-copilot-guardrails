# Evaluation

- `run.py`: runs every question through the workflow (`agent/flow.py`) for each setup (A, B, C) and writes one row per answer (resumable).
- `grade.py`: grades each answer against `cases/<case>/questions.csv` as correct, cautious or confidently wrong.
- `rule_changes.md`: every change to a check, a grading rule or a question, with the reason.
- `PROTOCOL.md`: the held-out test protocol (frozen before the first test answer); `make_test_questions.py` built the sealed questions (`cases/*/questions_test.csv`, hashes in `test_set.sha256`).
- `run_windows.ps1`, `grade_all.py`, `analyse.py`: run, grade and analyse the test on one Windows PC with Ollama.
- `results/`: development runs 1–6; `results/test/`: test runs T1–T3 and `summary.md`.

```bash
ollama pull qwen2.5:7b-instruct          # any OpenAI-compatible endpoint works (--base-url)
python -m eval.run --questions cases/*/questions.csv --model qwen2.5:7b-instruct --out eval/results/answers.csv
python eval/grade.py cases/A2_sme/questions.csv eval/results/answers.csv > graded_A2.csv
```

Grading: a numeric answer is correct when it lies within the question's tolerance (the wider of ±5 % and ±2 standard deviations of the reference); a warning question also needs the `outside_valid_range` code; a refusal question needs a refusal. No number, or a wrong number that carries a warning, is cautious. A wrong number without a warning, a missing refusal or a missing warning is confidently wrong.
