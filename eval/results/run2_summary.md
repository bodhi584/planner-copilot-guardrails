# Run 2: qwen2.5:7b-instruct, Kaggle GPU T4 x2, 17 Oct 2026

Kaggle GPU notebook, version 3 (47 min). Code of this repository + cases A1 (cache-only,
6 seeds precomputed), A2 (JaamSim M3), A3, A5. One answer per question and arm (repeat 1). Graded with eval/grade.py.

| Case | Questions | A correct / cautious / wrong | B | C |
|---|---|---|---|---|
| A1 SMT2020 fab | 21 | 12 / 3 / 6 | 18 / 2 / 1 | 20 / 1 / 0 |
| A2 SME metal shop | 19 | 8 / 5 / 6 | 14 / 3 / 2 | 18 / 0 / 1 |
| A3 warehouse | 20 | 13 / 0 / 7 | 15 / 1 / 4 | 17 / 1 / 2 |
| A5 operator line | 20 | 9 / 1 / 10 | 15 / 1 / 4 | 20 / 0 / 0 |
| **Total** | **80** | **42 / 9 / 29** | **62 / 7 / 11** | **75 / 2 / 3** |

Confidently wrong: A 36 %, B 14 %, C 4 %. Correct: A 53 %, B 78 %, C 94 %.
Per-answer files: `run2_qwen7b_A1A2A3A5.csv`, `run2_graded_<case>.csv`.

## The 5 setup-C answers that were not correct

| qid | outcome | what happened | cause | proposed fix |
|---|---|---|---|---|
| A1-15 | cautious | LVHM cost FIFO vs CR -> no_difference | 6 seeds: CI of the difference contains 0 (paper: 100 seeds) | none (honest answer); more seeds if wanted |
| A2-14 | wrong | machine breakdowns: engine error -> refused | the JaamSim expert model has no breakdown mechanism (adapter raises); the question expects a flagged number from the old SimPy pilot | question: by the three-tier rule (mechanism absent -> refuse) this should be a scope item; change in questions.csv, log it |
| A3-12 | cautious | tool-call limit | model called estimate with params_a/params_b six times instead of compare | shape repair in agent/tools.py: estimate with params_a+params_b -> compare |
| A3-13 | wrong | "12 trucks = more pallets? yes" | model ran one estimate (1,552) and did not compare with 9 trucks (1,555) | prompt hint "for more / less / better questions use compare"; engine cannot force it |
| A3-20 | wrong | "move fast movers closer to the dock" answered with INTERLEAVE | slotting/layout is out of scope but the question has no refuse keyword ("layout" is one); engine scope check passes on the KPI name | scope check: unknown change words; do NOT tune keywords on this test item |
