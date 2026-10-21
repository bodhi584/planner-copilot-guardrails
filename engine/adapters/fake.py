"""Fake adapter: a tiny stochastic shop model. COPY THIS FILE as the template for cases/<case_id>/adapter.py.

What a new case must provide (engine/DESIGN.md section 4):
  * a class `Adapter` with `case_id`, `supports_event_log` and `run(params, n, event_log=False)`
  * `params` arrive complete and checked, in the units of the case card (the engine did that)
  * `run` returns one dict per replication 1..n: {"<kpi>": float, ..., "_extras": {...}}
  * replication i ALWAYS uses random stream i (here: default_rng(i)), so two scenarios with the same i
    share common random numbers and a comparison of identical scenarios gives exactly 0.
  * a real adapter calls its simulator (JaamSim, SimPy ...) inside `run`; it may re-run from 1 on every call.
"""
import math

import numpy as np

SHARES = {"SheetLaser": 0.5, "TubeLaser": 0.3, "Bending": 0.2}  # share of the work per machine


class Adapter:
    case_id = "FAKE_case"
    supports_event_log = False

    def run(self, params, n, event_log=False, start=1):
        """Replications start .. start+n-1 (`start` is optional; the engine uses it only for the 'paired off' ablation)."""
        return [self._one(params, i) for i in range(start, start + n)]

    def _one(self, p, i):
        rng = np.random.default_rng(i)  # stream i, independent of the parameters
        orders = 69 if p["portfolio"] == "norm" else 83
        work = rng.lognormal(math.log(1.7), 0.4, orders)  # work hours per order
        work[: int(orders * p.get("rush_share", 10) / 100)] *= 1.5  # rush orders need more work
        capacity = p["workers"] * p["shift_length"] / 60 * 5  # worker-hours in a 5-shift week
        finish = np.cumsum(work) / p["workers"]  # hour at which each order is finished
        shift_h = p["shift_length"] / 60 * 5
        return {
            "overtime_after_shift": float((work.sum() - capacity) / p["workers"]),
            "late_orders": float((finish > shift_h).sum()),
            "_extras": {"utilisation": {m: float(min(1.0, work.sum() * s / capacity)) for m, s in SHARES.items()}},
        }
