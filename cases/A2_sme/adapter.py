"""Engine adapter for A2_sme: runs the expert JaamSim M3 model headless (see engine/DESIGN.md section 4).

Needs: `bash setup.sh` (builds JaamSim into ./jaamsim) and the Zenodo files in ./model (see README / reproduce.ipynb).
What the adapter can change in M3_weekly_backlog.cfg:
  workers       : 1..n operators. < 3: Worker3 (and Worker2) leave the ResourcePool. > 3: Worker4.. are added
                  (copies of Worker3). Breaks are spread evenly over the 180-240 min window (fraction i/(n-1));
                  for 3 workers this is exactly the published 0 / 0.5 / 1. For 4+ workers this is OUR assumption.
  portfolio     : norm | over20 (Orders DataFile).
  shift_length  : minutes per shift (Mon-Fri, shifts start at 0, 1440, 2880, 4320, 5760 min). Every shift end
                  in the cfg (480, 1920, 3360, 4800, 6240 min) moves with it; scheduled capacity (2400, 7200 min) too.
                  Only 480 is the expert model.
  machine_breakdowns : not in the expert model (Zenodo: failures excluded) -> NotImplementedError unless 0.
Replication i always uses GlobalSubstreamSeed i (common random numbers across scenarios); `start` shifts the index.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MACHINES = ("SheetLaser", "TubeLaser", "PunchingMachine", "BendingMachine")
SHIFT_STARTS = (0, 1440, 2880, 4320, 5760)  # min, Mon-Fri


def _parse_rep(path):
    """One dict per replication: {(entity, output): (value, unit)} (same parser as reproduce.ipynb)."""
    reps, cur = [], None
    for line in open(path, encoding="latin-1"):
        if line.startswith("##### SCENARIO"):
            cur = {}
            reps.append(cur)
            continue
        p = line.rstrip().split("\t")
        if cur is not None and len(p) >= 4:
            cur[(p[0], p[1])] = (p[2], p[3])
    return reps


class Adapter:
    case_id = "A2_sme"
    supports_event_log = False

    def __init__(self, jaamsim=HERE / "jaamsim", model=HERE / "model", timeout=600):
        self.jaamsim, self.model, self.timeout = Path(jaamsim), Path(model), timeout
        cfg = self.model / "M3_weekly_backlog.cfg"
        if not cfg.is_file() or not (self.jaamsim / "classes").is_dir():
            raise FileNotFoundError(f"A2 needs {cfg} and a built JaamSim in {self.jaamsim}: run setup.sh and download the Zenodo files")
        self.src = cfg.read_text(encoding="latin-1").splitlines()

    # ---- cfg generation -------------------------------------------------------------------------
    def make_cfg(self, workers, portfolio, shift_length, n, start):
        w, L = int(workers), float(shift_length)
        if w < 1:
            raise ValueError("workers must be >= 1")
        if not 60 <= L < 1440:
            raise ValueError("shift_length must be 60..1439 min (shifts start every 1440 min)")
        frac = [0.0] if w == 1 else [i / (w - 1) for i in range(w)]
        ends = {480: L, 1920: 1440 + L, 3360: 2880 + L, 4800: 4320 + L, 6240: 5760 + L, 2400: 5 * L, 7200: 15 * L}
        fmt = lambda x: f"{x:g}"
        out = []
        for line in self.src:
            if line.startswith("Define DowntimeEntity { Worker1Break") and w > 3:
                line = line.replace("Worker3Break }", " ".join(f"Worker{k}Break" for k in range(3, w + 1)) + " }")
            if line.startswith("Define ResourceUnit { Worker1") and w > 3:
                line = line.replace("Worker3 }", " ".join(f"Worker{k}" for k in range(3, w + 1)) + " }")
            m = re.match(r"Worker(\d+) ResourcePool ", line)
            if m and int(m.group(1)) > w:
                continue  # fewer than 3 workers: unit stays defined but leaves the pool
            m = re.match(r"Worker(\d+)Break FirstDowntime", line)
            if m and int(m.group(1)) <= w:
                k = int(m.group(1))
                line = f"Worker{k}Break FirstDowntime {{ '[BreakWindowStart].Value + {frac[k - 1]:.6g} * ([BreakWindowEnd].Value - [BreakWindowStart].Value)' }}"
            if line.startswith("Orders DataFile"):
                line = f"Orders DataFile {{ portf_{portfolio}_clean.tsv }}"
            if line.startswith("Simulation NumberOfReplications"):
                line = f"Simulation NumberOfReplications {{ {int(n)} }}"
            if line.startswith("Simulation GlobalSubstreamSeed"):
                line = f"Simulation GlobalSubstreamSeed {{ '{int(start)} + this.ReplicationNumber - 1' }}"
            if L != 480:
                if line.startswith("ShiftCalendar Value"):
                    line = "ShiftCalendar Value { " + " ".join(
                        f"{{ {s}  min  {fmt(s + L)} }} {{ {fmt(s + L)}  min  0 }}" for s in SHIFT_STARTS) + " }"
                else:  # every other shift-end constant written as "<x>[min]" or "<x>  min"
                    line = re.sub(r"(?<![\d.])(480|1920|3360|4800|6240|2400|7200)(?=\s*\[min\]|\s+min\b)",
                                  lambda mm: fmt(ends[int(mm.group(1))]), line)
            out.append(line)
        for k in range(4, w + 1):  # extra workers: copy Worker3's unit and break definitions
            out.append(f"Worker{k}Break FirstDowntime {{ '[BreakWindowStart].Value + {frac[k - 1]:.6g} * ([BreakWindowEnd].Value - [BreakWindowStart].Value)' }}")
            out += [l.replace("Worker3", f"Worker{k}") for l in self.src
                    if re.match(r"Worker3Break (Interval|Duration|MaxDowntimesPending) ", l) or re.match(r"Worker3 (ForcedMaintenanceList|ResourcePool) ", l)]
        return "\n".join(out) + "\n"

    # ---- engine interface ---------------------------------------------------------------------------
    def run(self, params, n, event_log=False, start=1):
        p = dict(params)
        if float(p.get("machine_breakdowns", 0) or 0) != 0:
            raise NotImplementedError("machine breakdowns are not part of the expert JaamSim model (Zenodo: failures excluded)")
        workers, portfolio, L = int(p.get("workers", 3)), str(p.get("portfolio", "norm")), float(p.get("shift_length", 480))
        friday_end_h = (SHIFT_STARTS[-1] + L) / 60.0
        cp = ":".join(str(self.jaamsim / x) for x in ("classes", "src/main/resources", "jar/jogl-all.jar", "jar/gluegen-rt.jar"))
        with tempfile.TemporaryDirectory(prefix="a2_") as d:
            Path(d, "m.cfg").write_text(self.make_cfg(workers, portfolio, L, n, start), encoding="latin-1")
            for f in ("portf_norm_clean.tsv", "portf_over20_clean.tsv"):
                shutil.copy(self.model / f, d)
            r = subprocess.run(["java", "-Djava.awt.headless=true", "-cp", cp, "com.jaamsim.ui.GUIFrame", "m.cfg", "-b", "-h"],
                               cwd=d, capture_output=True, text=True, timeout=self.timeout)
            rep = Path(d, "m.rep")
            if not rep.is_file():
                raise RuntimeError("JaamSim produced no report: " + (r.stderr or r.stdout)[-400:])
            reps = _parse_rep(rep)
        if len(reps) < n:
            raise RuntimeError(f"JaamSim report has {len(reps)} of {n} replications")
        out = []
        for x in reps[:n]:
            pc = x[("CompleteOrder", "PortfolioCompletion")]
            assert pc[1] == "h", pc
            util = {m: float(x[(m, "Utilisation")][0]) for m in MACHINES}
            out.append({"overtime_after_shift": float(pc[0]) - friday_end_h,
                        "unfinished_orders": float(x[("FridaySnapshot", "UnfinishedOrders")][0]),
                        "bottleneck_utilisation": max(util.values()),
                        "_extras": {"utilisation": util}})
        return out
