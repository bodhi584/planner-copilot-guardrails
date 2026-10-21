"""Reproduce the published JaamSim results of the sheet-metal job shop (Zenodo 10.5281/zenodo.23229885).

Runs the expert model M3 headless for the normal and the +20 % order book, 30 replications each, and compares
every replication with the published report files in model/. Needs: bash setup.sh (builds JaamSim, a few minutes).
Usage: python reproduce.py
"""
from pathlib import Path

from adapter import Adapter, _parse_rep

HERE = Path(__file__).resolve().parent
FRIDAY_END_H = 104.0

ad = Adapter()
worst = 0.0
for portfolio in ("norm", "over20"):
    pub = _parse_rep(HERE / "model" / f"M3_{portfolio}_30replikacji.rep")
    pub_ot = [float(r[("CompleteOrder", "PortfolioCompletion")][0]) - FRIDAY_END_H for r in pub]
    ours = [r["overtime_after_shift"] for r in ad.run({"workers": 3, "portfolio": portfolio}, 30)]
    diff = max(abs(a - b) for a, b in zip(ours, pub_ot))
    worst = max(worst, diff)
    print(f"{portfolio:6s}  published mean {sum(pub_ot) / len(pub_ot):6.3f} h   ours {sum(ours) / len(ours):6.3f} h   "
          f"max |difference| per replication {diff:.2e}")

raise SystemExit(0 if worst < 1e-6 else "reproduction differs from the published replications")
