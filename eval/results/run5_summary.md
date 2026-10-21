# Run 5 — Gemma 2 9B (+ Mistral 7B partial, Llama rerun failed)

Kaggle GPU notebook, version 7 (GPU T4 x2, 18 Oct 2026).
Same bundle and rules as run 3/4 (rule changes 2026-10-17). Each model had a hard time cap.

## Totals over 80 questions (correct / cautious / confidently wrong)

| Model | A raw | B raw + rules | C guardrail engine |
|---|---|---|---|
| Qwen 2.5 7B (run 3) | 43 / 9 / 28 | 63 / 7 / 10 | 76 / 2 / 2 |
| Gemma 2 9B (run 5) | 25 / 19 / 36 | 33 / 30 / 17 | 71 / 5 / 4 |
| Llama 3.1 8B (run 4, from log) | 27 / 13 / 40 | 42 / 24 / 14 | 63 / 10 / 7 |
| Mistral 7B (run 5, A1 only, 21 q) | 8 / 3 / 10 | 4 / 16 / 1 | 4 / 17 / 0 |

## Gemma 2 9B per case

| Case | A | B | C |
|---|---|---|---|
| A1 SMT2020 | 9/5/7 | 13/8/0 | 17/4/0 |
| A2 SME | 4/11/4 | 8/4/7 | 18/0/1 |
| A3 warehouse | 4/2/14 | 3/13/4 | 18/1/1 |
| A5 operator line | 8/1/11 | 9/5/6 | 18/0/2 |

## Notes
- Three models, same ordering C > B > A on correct answers and on avoiding confident errors.
  Arm C keeps confidently-wrong answers at 2-7 of 80 for all three; arm A has 28-40.
- Gemma's biggest gain is B -> C (33 -> 71): the written rules alone do not help Gemma much, the engine does.
- Mistral 7B: hit its 40-min cap after A1 + 18 A2 answers (median 21-34 s per answer in B/C).
  In arm C it sends tool calls with empty `args` (`{"tool": "estimate", "args": {}}`), so the engine refuses
  and the 6-call limit ends the answer -> "cautious". It fails safe (0 wrong) but is not usable with the
  current JSON action format. Possible fix: accept flat parameters in `flow.py` parsing. Not done (would be a rule change).
- Llama 3.1 8B rerun: produced no output for its full 60-min cap (stuck in environment setup before the first answer),
  so no per-answer files; run 4 totals from the log stand.
- Files: run5_gemma2_9b_A1A2A3A5.csv, run5_gemma2_9b_graded_*.csv, run5_mistral7b_A1_partial.csv, run5_mistral7b_graded_A1_smt2020.csv
