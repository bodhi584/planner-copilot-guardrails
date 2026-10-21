# A3 · Pallet warehouse with reach trucks

One 8-hour shift in a real pallet warehouse: put-away and pick tasks arrive at January 2025 demand, served by 6–12 reach trucks under three dispatching rules (single command, interleave, nearest) and a task-holding time.

| | |
|---|---|
| Model and data | Saengphueng (2026), *Code and Data for: Task Interleaving in Warehouse Operations*, Zenodo, doi:10.5281/zenodo.21469786. MIT licence (`model/LICENSE.txt`). The simulation model `model/sim_interleaving.py` and the result file `model/exp_results_v2.json` are unchanged. |
| Simulator | SimPy |
| Reproduction | `reproduce.py` re-runs all 60 published cells (fleet 6–12, hold 0–10 min, demand ×0.8/1.0/1.2, 3 rules): **360 of 360** KPI means identical to the published file (about 80 s) |

```bash
pip install simpy
python reproduce.py
```

`questions.csv`: 20 questions (10 numeric, 3 choice, 4 warning, 3 refusal), built by `make_questions.py` from 30-replication runs; tolerance is the wider of ±5 % and ±2 sd.
