"""Re-run every published scenario of exp_results_v2.json (30 replications each) and compare.

    python reproduce.py            # all 60 scenario x policy cells, ~1 min
Prints one line per cell and a summary; exit code 1 if any mean differs by more than 1e-6.
"""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from adapter import KPI, Adapter  # noqa: E402

pub = json.load(open(HERE / "model" / "exp_results_v2.json"))
a = Adapter()
grids = {"fleet": ("reach_trucks", int), "hold": ("hold_time", float), "demand": ("demand_factor", float)}
base = {"reach_trucks": 9, "hold_time": 1.5, "demand_factor": 1.0}
cells = bad = 0
for grid, (param, cast) in grids.items():
    for level, by_policy in pub[grid].items():
        for policy, metrics in by_policy.items():
            params = dict(base, policy=policy, **{param: cast(level)})
            runs = a.run(params, 30)
            for name, key in KPI.items():
                m_pub, h_pub = metrics[key]
                m = statistics.mean(r[name] for r in runs)
                cells += 1
                if abs(m - m_pub) > 1e-6:
                    bad += 1
                    print(f"DIFF {grid}={level} {policy} {name}: ours {m:.4f} vs published {m_pub:.4f} (+-{h_pub:.4f})")
            print(f"{grid}={level:>4} {policy:10s} pallets/day {statistics.mean(r['pallets_per_day'] for r in runs):8.2f}"
                  f"  published {metrics['pallets/day'][0]:8.2f}")
print(f"\n{cells - bad} of {cells} KPI means identical to the published values")
sys.exit(1 if bad else 0)
