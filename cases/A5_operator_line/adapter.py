"""Engine adapter for A5_operator_line (SimPy rebuild of Seppanen 2005). Interface: engine/DESIGN.md section 4.

Parameters (case-card units):
  operators            : operators in the shared pool (paper: 2, 3, 4)
  buffer_1..buffer_3   : buffer capacities between cells (paper: 1, 2, 1)
  failure_rate_factor  : multiplies the failure rate of every cell (1 = paper; 2 = twice as many failures)
  repair_time_factor   : multiplies the mean repair time (1 = paper)
Replication i uses seed i, so scenarios share common random numbers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import Params, run_once  # noqa: E402

KPIS = ("units_per_shift", "operator_moves", "units_per_operator", "cycle_time_s", "operator_busy_pct")


class Adapter:
    case_id = "A5_operator_line"
    supports_event_log = False

    def run(self, params, n, event_log=False, start=1):
        q = dict(params)
        base = Params()
        f_fail = float(q.get("failure_rate_factor", 1.0))
        f_rep = float(q.get("repair_time_factor", 1.0))
        if f_fail <= 0 or f_rep <= 0:
            raise ValueError("failure_rate_factor and repair_time_factor must be > 0")
        p = Params(
            operators=int(q.get("operators", 3)),
            buffers=tuple(int(q.get(f"buffer_{i}", b)) for i, b in enumerate(base.buffers, 1)),
            up_mean_min=tuple(m / f_fail for m in base.up_mean_min),
            repair_mean_min=tuple(m * f_rep for m in base.repair_mean_min),
        )
        if p.operators < 2:
            raise ValueError("cell 4 needs two operators at once: at least 2 operators")
        out = []
        for i in range(start, start + n):
            r = run_once(p, i)
            out.append({k: float(r[k]) for k in KPIS} | {"_extras": {"operator_move_segments": r["operator_move_segments"]}})
        return out
