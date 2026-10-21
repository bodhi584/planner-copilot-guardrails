"""Compare the rebuild with Fig. 16 of Seppanen (2005).

    python reproduce.py [reps] [first_seed]     # default 30 reps, seeds 101..130 (not the calibration seeds 1..10)
Pass criterion (case acceptance standard): our mean lies inside the published 95% CI.
Operator moves are compared with the number of cells walked past (see calibrate.py).
"""
import statistics as S
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import Params, run_once  # noqa: E402

# Fig. 16: operators -> (mean units, half-width, lower, upper, operator moves, units per operator, cycle s)
FIG16 = {2: (223, 9, 214, 232, 2196, 112, 129), 3: (320, 15, 305, 335, 1748, 107, 90), 4: (348, 13, 335, 361, 473, 87, 83)}

reps = int(sys.argv[1]) if len(sys.argv) > 1 else 30
first = int(sys.argv[2]) if len(sys.argv) > 2 else 101
ok = 0
print(f"{reps} replications, seeds {first}..{first + reps - 1}")
print("ops | units ours (95% CI)      published (CI)      inside | moves ours  published | cycle s ours  published")
for n, (m, h, lo, hi, mv, upo, cyc) in FIG16.items():
    runs = [run_once(Params(operators=n), s) for s in range(first, first + reps)]
    u = [r["units_per_shift"] for r in runs]
    mu, hw = S.mean(u), 1.96 * S.stdev(u) / len(u) ** 0.5
    inside = lo <= mu <= hi
    ok += inside
    print(f"{n:3d} | {mu:6.1f} ({mu - hw:5.1f}-{mu + hw:5.1f})   {m} ({lo}-{hi})   {'yes' if inside else 'NO':>6} |"
          f" {S.mean(r['operator_move_segments'] for r in runs):9.0f} {mv:10d} | {S.mean(r['cycle_time_s'] for r in runs):12.1f} {cyc:10d}")
print(f"\n{ok} of 3 scenarios inside the published 95% CI")
sys.exit(0 if ok == 3 else 1)
