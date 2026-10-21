"""Engine adapter for A1_smt2020 (engine/DESIGN.md section 4).

Each replication is one run of run_scenario.py under the Python 3.9 venv made by setup.sh (one 180-day run takes
about 15 min on Colab/laptop). Results are cached on disk in cache/<key>.json, so a scenario is simulated once and
every later question reuses it; replication i uses simulator seed i - 1 (seeds 0..99 as in Tassel et al. 2023).
Parameters: dataset (HVLM | LVHM), rule (fifo | cr), days (180 = paper), mtbf_factor, mttr_factor (1 = paper).

Cache-only mode (A1_CACHE_ONLY=1, used in the experiments): never starts the simulator. Runs come from cache/ or the
tracked precomputed/ folder (KPI summaries without per-product rows); a request for more replications than are stored
returns the stored ones (consecutive seeds from `start`), a scenario with none stored raises RuntimeError.
"""
import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = HERE / ".venv" / "bin" / "python"
CACHE = HERE / "cache"
PRE = HERE / "precomputed"
KPIS = ("regular_ct", "regular_ot", "hot_ct", "hot_ot", "superhot_ct", "superhot_ot", "cost")


class Adapter:
    case_id = "A1_smt2020"
    supports_event_log = False

    def __init__(self, workers=None, timeout=7200):
        self.cache_only = os.environ.get("A1_CACHE_ONLY") == "1"
        if not PY.exists() and not self.cache_only:
            raise FileNotFoundError(f"{PY} missing: run setup.sh first")
        self.workers = workers or max(1, (os.cpu_count() or 2))
        self.timeout = timeout
        CACHE.mkdir(exist_ok=True)

    @staticmethod
    def _norm(params):
        q = dict(params)
        return dict(dataset=str(q.get("dataset", "HVLM")).upper(), rule=str(q.get("rule", "fifo")).lower(),
                    days=float(q.get("days", 180)), mtbf_factor=float(q.get("mtbf_factor", 1.0)),
                    mttr_factor=float(q.get("mttr_factor", 1.0)))

    def _one(self, p, seed):
        key = hashlib.sha1(json.dumps(dict(p, seed=seed), sort_keys=True).encode()).hexdigest()[:16]
        for f in (CACHE / f"{key}.json", PRE / f"{key}.json"):
            if f.exists():
                return json.loads(f.read_text())
        if self.cache_only:
            return None
        f = CACHE / f"{key}.json"
        args = [str(PY), str(HERE / "run_scenario.py"), "--dataset", p["dataset"], "--rule", p["rule"], "--days", str(p["days"]),
                "--seed", str(seed), "--mtbf_factor", str(p["mtbf_factor"]), "--mttr_factor", str(p["mttr_factor"])]
        r = subprocess.run(args, capture_output=True, text=True, timeout=self.timeout)
        if r.returncode != 0:
            raise RuntimeError(f"simulator failed (seed {seed}): {(r.stderr or r.stdout)[-400:]}")
        out = json.loads(r.stdout.strip().splitlines()[-1])
        f.write_text(json.dumps(out))
        return out

    def run(self, params, n, event_log=False, start=1):
        p = self._norm(params)
        if p["dataset"] not in ("HVLM", "LVHM") or p["rule"] not in ("fifo", "cr"):
            raise ValueError("dataset must be HVLM or LVHM, rule fifo or cr")
        if p["mtbf_factor"] <= 0 or p["mttr_factor"] <= 0 or p["days"] <= 0:
            raise ValueError("days, mtbf_factor and mttr_factor must be > 0")
        seeds = [i - 1 for i in range(start, start + n)]
        with ThreadPoolExecutor(self.workers) as ex:
            runs = list(ex.map(lambda s: self._one(p, s), seeds))
        if self.cache_only:
            k = next((i for i, r in enumerate(runs) if r is None), len(runs))
            runs = runs[:k]
            if not runs:
                raise RuntimeError("this A1 scenario is not precomputed (cache-only mode): only the four published "
                                   "scenarios (HVLM/LVHM x fifo/cr, 180 days, breakdown factors 1) are available")
        out = []
        for r in runs:
            d = {k: (float(r[k]) if r[k] is not None else float("nan")) for k in KPIS}
            d["_extras"] = {"completed": {c: r[f"{c}_completed"] for c in ("regular", "hot", "superhot")}, "rows": r.get("rows", [])}
            out.append(d)
        return out
