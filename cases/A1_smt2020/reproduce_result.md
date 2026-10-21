# A1 reproduction result (16 Oct 2026)

`python reproduce.py 2` against Tassel et al. (2023) Table 1 (`paper_table1.json`), 180 days, seeds 0 and 1, all four scenarios
(HVLM / LVHM x FIFO / critical ratio). Raw per-run KPIs: `reproduce_runs_2seeds.json` (HVLM FIFO run in this container,
the other three scenarios on a Colab CPU runtime, about 32-43 min per run).

**28 of 28 values within tolerance** (wider of +-5 %, +-2 published sd, +-2 points for on-time %).

| Scenario | Regular CT ours / paper (days) | Hot CT ours / paper | Cost ours / paper |
|---|---|---|---|
| HVLM FIFO | 71.33 / 72.57 | 26.86 / 26.91 | 38,240 / 38,014 |
| HVLM CR | 71.14 / 70.80 | 26.91 / 26.94 | 39,513 / 39,813 |
| LVHM FIFO | 54.03 / 52.38 | 23.86 / 23.80 | 102,816 / 102,171 |
| LVHM CR | 52.20 / 52.25 | 23.74 / 23.71 | 107,211 / 108,856 |

Caveats
- 2 seeds vs 100 in the paper: the means match, our spread is not yet estimated.
- Super-hot on-time % rests on 9-10 lots per run (HVLM CR 55.6 % vs 41.8 +- 12.5 %), so it passes only through the wide
  published sd; questions should not ask for super-hot on-time % without a warning.
- LVHM FIFO regular CT is 3.2 % above the paper (inside 5 %); the rest are within 1.5 %.

## Update 17 Oct 2026: 6 seeds (0-5) per scenario

Seeds 2-5 ran on Kaggle (4 CPU cores, headless); KPI summaries in `precomputed/`. `A1_CACHE_ONLY=1 python reproduce.py 6`:
**28 of 28 values within tolerance.** Regular CT ours / paper: HVLM FIFO 71.78 / 72.57, HVLM CR 70.43 / 70.80,
LVHM FIFO 53.96 / 52.38, LVHM CR 52.18 / 52.25.

Engine-only check of the 21 questions (no LLM, cache-only, graded with eval/grade.py): 20 correct, 1 cautious
(A1-15, LVHM cost FIFO vs CR: with 6 seeds the difference CI contains 0, so the engine says not_distinguishable;
the paper's 100 seeds favour FIFO).
