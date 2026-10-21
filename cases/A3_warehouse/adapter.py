"""Engine adapter for A3_warehouse: the published SimPy model of Saengphueng (2026), Zenodo 10.5281/zenodo.21469786.

Interface as engine/DESIGN.md section 4. Parameters (case-card units):
  reach_trucks   : number of reach trucks (each with a driver)          -> Params.n_reach_trucks
  policy         : SINGLE | INTERLEAVE | NEAREST                          (dispatching rule)
  hold_time      : minutes a pick waits before an idle truck may take it  -> Params.pick_hold_min
  demand_factor  : multiplier on January 2025 demand (740 put-away / 831 pick pallets per day)
Replication i (1-based) uses seed 42 + i - 1, the same seeds as the author's experiments_v2.py,
so replications 1..30 reproduce exp_results_v2.json exactly and scenarios share common random numbers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "model"))
from sim_interleaving import Params, run_once  # noqa: E402

PUTAWAY, PICK, SEED = 740, 831, 42
KPI = {  # engine name -> key in the author's result dict
    "pallets_per_day": "pallets/day",
    "empty_travel_pct": "empty travel %",
    "truck_utilisation_pct": "RT utilization %",
    "mean_wait_min": "mean wait (min)",
    "pick_cycle_min": "pick cycle (min)",
    "interleave_rate_pct": "interleave rate %",
}


class Adapter:
    case_id = "A3_warehouse"
    supports_event_log = False

    def run(self, params, n, event_log=False, start=1):
        p = dict(params)
        policy = str(p.get("policy", "SINGLE")).upper()
        if policy not in ("SINGLE", "INTERLEAVE", "NEAREST"):
            raise ValueError(f"unknown policy {policy}")
        f = float(p.get("demand_factor", 1.0))
        prm = Params(n_reach_trucks=int(p.get("reach_trucks", 9)), putaway_pallets_per_day=PUTAWAY * f,
                     pick_pallets_per_day=PICK * f, pick_hold_min=float(p.get("hold_time", 1.5)))
        out = []
        for i in range(start, start + n):
            r = run_once(policy, prm, SEED + i - 1)
            out.append({k: float(r[v]) for k, v in KPI.items()})
        return out
