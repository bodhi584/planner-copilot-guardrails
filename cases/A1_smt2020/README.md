# A1 · SMT2020 semiconductor fab

A large wafer fab with re-entrant flows, batching and machine breakdowns. Planner questions are about cycle time and on-time delivery per lot class (regular, hot, super-hot) under two dispatching rules (FIFO, CR) and two product mixes (HVLM, LVHM).

| | |
|---|---|
| Testbed | Kopp et al. (2020), SMT2020, IEEE Transactions on Semiconductor Manufacturing, doi:10.1109/TSM.2020.3001933 |
| Published results | Tassel et al. (2023), *Semiconductor Fab Scheduling with Self-Supervised and Reinforcement Learning*, Proc. Winter Simulation Conference, Table 1 (`paper_table1.json`, mean and sd over 100 seeds) |
| Simulator | [RL4SemiconductorFabSched](https://github.com/ingambe/RL4SemiconductorFabSched) (MIT), pinned to commit `89467c6` by `setup.sh` |
| Reproduction | **28 of 28** published values within tolerance (6 seeds per scenario), see `reproduce_result.md` |

One 180-day run takes 30–45 minutes, so the four published scenarios × seeds 0–5 are stored in `precomputed/`. With `A1_CACHE_ONLY=1` the adapter answers from these runs and never starts the simulator (this is how the experiments ran).

```bash
bash setup.sh                                   # simulator + Python 3.9 environment (uv)
A1_CACHE_ONLY=1 python reproduce.py 6           # compare the stored runs with Table 1
.venv/bin/python run_static.py --dataset HVLM --rule fifo --days 30 --seed 0 --out test.json   # one quick live run
```

Notes: the simulator needs Python 3.9 (numpy 1.22.4, cloudpickle 2.1.0); `wandb` is replaced by a stub in `stubs/`; the cost score is a benchmark score, not euros.
