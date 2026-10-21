"""Grid search over the ASSUMED inputs of model.py against Fig. 16 of Seppanen (2005).

Targets (10 replications of one 8 h shift, 95% CI half-width):
  2 operators: 223 +- 9 units, 2,196 operator moves
  3 operators: 320 +- 15 units, 1,748 moves
  4 operators: 348 +- 13 units, 473 moves
Operator moves are compared with `operator_move_segments` (cells walked past), which matches the published
counts at 3 and 4 operators far better than counting trips. Score = sum of squared errors in units of the
published half-width (production) + 0.5 * relative squared error of moves.
    python calibrate.py            # prints the 10 best settings
"""
import itertools
import statistics as S
from multiprocessing import Pool

from model import Params, run_once

TARGET = {2: (223, 9, 2196), 3: (320, 15, 1748), 4: (348, 13, 473)}
REPS = 10
GRID = dict(
    dispatch_rule=["fifo", "downstream", "closest"],
    walk_s_per_cell=[0.0, 0.5, 1.0, 1.5, 2.0, 3.0],
    transit_s=[0.0, 5.0, 10.0],
    cycle_cv=[0.0, 0.1],
)


def evaluate(setting):
    kw = dict(zip(GRID, setting))
    res, score = {}, 0.0
    for n, (u, h, mv) in TARGET.items():
        runs = [run_once(Params(operators=n, **kw), seed) for seed in range(1, REPS + 1)]
        mu = S.mean(r["units_per_shift"] for r in runs)
        mm = S.mean(r["operator_move_segments"] for r in runs)
        res[n] = (round(mu, 1), round(mm))
        score += ((mu - u) / h) ** 2 + 0.5 * ((mm - mv) / mv) ** 2
    return score, kw, res


if __name__ == "__main__":
    with Pool() as pool:
        out = sorted(pool.map(evaluate, list(itertools.product(*GRID.values()))), key=lambda x: x[0])
    for score, kw, res in out[:10]:
        print(f"{score:7.2f} {kw} {res}")
