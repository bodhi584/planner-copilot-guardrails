# A2 · Sheet-metal job shop (SME)

A small make-to-order job shop: 69 real orders per week, 4 machines (sheet laser, tube laser, punching, bending) and 3 operators shared by all machines, with breaks. Planner questions: how much overtime after the Friday shift, how many orders are unfinished, what changes with a fourth operator or a busier week.

| | |
|---|---|
| Model and data | Jurczyk-Bunkowska, M. (2026). *JaamSim models, order portfolios, and replication results for capacity planning in an SME manufacturing system*. Zenodo, doi:10.5281/zenodo.23229885. Licence CC BY 4.0. The files in `model/` are copied unchanged from that record. |
| Simulator | [JaamSim](https://github.com/jaamsim/jaamsim), built from source by `setup.sh`, run headless |
| Reproduction | Our runs equal the 30 published replications **exactly** (difference 0) for the normal and the +20 % order book |

```bash
bash setup.sh          # builds JaamSim (needs Java 17+, a few minutes, once)
python reproduce.py    # 2 × 30 replications, compared one by one with the published report files
bash run.sh M3 norm    # one scenario, report in runs/
```

The 4-operator scenario is our own run of the published model (the fourth operator's break is placed like the others); it is marked as an assumption in `case_card.yaml`.
