# A5 · Operator-paced assembly line

Four assembly cells with small buffers, a shared pool of operators who also handle product changes, materials and rejects, machine failures and repairs, and breaks. Planner questions: units per shift for 2–4 operators, and the effect of failures and buffers.

| | |
|---|---|
| Source | Seppanen, M. S. (2005). *Operator-Paced Assembly Line Simulation*. Proc. Winter Simulation Conference, pp. 1343–1349, doi:10.1109/WSC.2005.1574396 |
| Model | The original Arena model is not available, so `model.py` rebuilds it in SimPy from the paper; every input cites its figure. |
| Reproduction | Units per shift for 2, 3 and 4 operators fall inside the published 95 % confidence intervals (Fig. 16) with 100 replications. For 3 and 4 operators the means sit at the upper edge; with only 30 replications (seeds 101–130) they fall just above it. |

| Operators | Ours (100 replications) | Published (95 % CI) |
|---|---|---|
| 2 | 221.8 | 223 (214–232) |
| 3 | 334.0 | 320 (305–335) |
| 4 | 358.7 | 348 (335–361) |

Four inputs are not given in the paper and were calibrated on 2 and 4 operators only (`calibrate.py`): walking time 1.0 s per cell, buffer transit 5 s, no assembly-time variability, a freed operator serves the most downstream waiting cell first. With these, the model predicts 331–335 units for 3 operators, which it was not calibrated on.

```bash
pip install simpy
python reproduce.py 100 1001
```
