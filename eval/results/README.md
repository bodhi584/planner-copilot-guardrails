# Results

Development runs. Each answer is graded **correct / cautious / confidently wrong** by `eval/grade.py`. Setups: **A** model + simulation without checks, **B** the same rules written into the prompt, **C** model + guardrail engine. One answer per question and setup (temperature 0).

| Run | Date | Model | Questions | A | B | C | Files |
|---|---|---|---|---|---|---|---|
| 1 | 16 Oct 2026 | Qwen 2.5 7B | 40 (A3, A5) | 20 / 4 / 16 | 26 / 8 / 6 | 38 / 1 / 1 | `run1_*.csv` |
| 2 | 17 Oct 2026 | Qwen 2.5 7B | 80 (A1, A2, A3, A5) | 42 / 9 / 29 | 62 / 7 / 11 | 75 / 2 / 3 | `run2_*`, [summary](run2_summary.md) |
| 3 | 17 Oct 2026 | Qwen 2.5 7B | 80 | 43 / 9 / 28 | 63 / 7 / 10 | **76 / 2 / 2** | `run3_*`, [summary](run3_summary.md) |
| 4 | 18 Oct 2026 | Llama 3.1 8B | 80 | 27 / 13 / 40 | 42 / 24 / 14 | **63 / 10 / 7** | totals from the log, [summary](run4_summary.md) |
| 5 | 18 Oct 2026 | Gemma 2 9B | 80 | 25 / 19 / 36 | 33 / 30 / 17 | **71 / 5 / 4** | `run5_gemma2_9b_*`, [summary](run5_summary.md) |

Between runs 2 and 3 two rules changed (see `../rule_changes.md`). Because the rules were adjusted on these same questions, the numbers are development results, not a held-out test.

Run 1 was on a free Colab T4 GPU, runs 2–5 on Kaggle (2 × T4), all with Ollama.
