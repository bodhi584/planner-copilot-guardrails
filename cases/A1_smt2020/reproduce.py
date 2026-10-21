"""Compare our runs with Tassel et al. (2023) Table 1 (paper_table1.json).

    python reproduce.py [seeds] [workers]     # default 10 seeds (0..9), 180 days; about 15 min per run, cached in cache/
Pass criterion: our mean within the wider of +-5 % and +-2 published sd (on-time % values near 0 use +-2 points).
"""
import json
import math
import statistics as S
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from adapter import Adapter  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
a = Adapter(workers=int(sys.argv[2]) if len(sys.argv) > 2 else None)
pub = json.load(open(HERE / "paper_table1.json"))
ok = total = 0
for ds in ("HVLM", "LVHM"):
    for rule in ("fifo", "cr"):
        runs = a.run({"dataset": ds, "rule": rule, "days": 180}, n)
        for kpi, (m, sd) in pub[ds][rule].items():
            v = [r[kpi] for r in runs if not math.isnan(r[kpi])]
            mu = S.mean(v)
            tol = max(0.05 * abs(m), 2 * sd, 2.0 if kpi.endswith("_ot") else 0.0)
            passed = abs(mu - m) <= tol
            ok += passed
            total += 1
            print(f"{ds} {rule:4s} {kpi:12s} ours {mu:10.2f} (n={len(v)})  paper {m:10.2f} +- {sd:<8} {'yes' if passed else 'NO'}")
print(f"\n{ok} of {total} values within tolerance ({n} seeds)")
raise SystemExit(0 if ok == total else 1)
