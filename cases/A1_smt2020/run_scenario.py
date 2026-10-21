"""Run one SMT2020 scenario (Python 3.9, open-source simulator of Tassel et al. 2023) and print KPIs as JSON.

Extends run_static.py with breakdown what-ifs and Table-1 style KPIs:
  --mtbf_factor F   multiplies every unscheduled-breakdown interval (2 = machines fail half as often)
  --mttr_factor F   multiplies every breakdown repair time
Preventive maintenance is left unchanged. The pickled state 365days_<dataset>.pkl is the fab after one year
(the simulator's warm-up); KPIs count lots finished after day 365, as in the simulator's StatPlugin.
Example: .venv/bin/python run_scenario.py --dataset HVLM --rule cr --days 180 --seed 3 --mttr_factor 2
"""
import argparse
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FAB = os.environ.get("FAB_SIM", os.path.join(HERE, "RL4SemiconductorFabSched"))
sys.path.insert(0, FAB)
sys.path.insert(0, os.path.join(HERE, "stubs"))
os.chdir(os.path.join(FAB, "simulation", "es"))
import cloudpickle  # noqa: E402
import numpy as np  # noqa: E402
from simulation.dispatching.dispatcher import Dispatchers  # noqa: E402
from simulation.events import BreakdownEvent  # noqa: E402
from simulation.greedy import build_batch  # noqa: E402
from simulation.plugins.stats_plugin import StatPlugin  # noqa: E402
from simulation.randomizer import Randomizer  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--dataset", default="HVLM", choices=["HVLM", "LVHM"])
p.add_argument("--rule", default="fifo", choices=["fifo", "cr"])
p.add_argument("--days", type=float, default=180)
p.add_argument("--seed", type=int, default=0)
p.add_argument("--mtbf_factor", type=float, default=1.0)
p.add_argument("--mttr_factor", type=float, default=1.0)
a = p.parse_args()
PT = {"fifo": Dispatchers.fifo_ptuple_for_lot, "cr": Dispatchers.cr_ptuple_for_lot}[a.rule]


class Scaled:
    """Distribution wrapper: sample() of the base distribution times a factor."""

    def __init__(self, base, f):
        self.base, self.f = base, f

    def sample(self):
        return self.base.sample() * self.f

    def avg(self):
        return self.base.avg() * self.f


def select(instance, current_time, last_sort_time):  # identical to run_static.py (hierarchical rule + setup avoidance)
    if last_sort_time != current_time:
        for lot in instance.usable_lots:
            lot.ptuple = PT(lot, current_time, None)
        last_sort_time = current_time
        instance.usable_lots.sort(key=lambda k: k.ptuple)
    lots = instance.usable_lots
    setup_machine = setup_batch = mrm = mrb = None
    family_lock = None
    for i in range(len(lots)):
        lot = lots[i]
        if family_lock is None or family_lock == lot.actual_step.family:
            family_lock = lot.actual_step.family
            if lot.actual_step.setup_needed == "":
                for m in lot.waiting_machines:
                    if m.current_setup == "":
                        return m, build_batch(lot, lots[i + 1:]), last_sort_time
            for m in lot.waiting_machines:
                if lot.actual_step.setup_needed == "" or lot.actual_step.setup_needed == m.current_setup:
                    return m, build_batch(lot, lots[i + 1:]), last_sort_time
                else:
                    if setup_machine is None and m.min_runs_left is None:
                        setup_machine, setup_batch = m, i
                    if mrm is None:
                        mrm, mrb = m, i
    if setup_machine is not None:
        return setup_machine, build_batch(lots[setup_batch], lots[setup_batch + 1:]), last_sort_time
    return mrm, (build_batch(lots[mrb], lots[mrb + 1:]) if mrm is not None else None), last_sort_time


t0 = time.time()
plugins = [StatPlugin()]
with open(f"365days_{a.dataset}.pkl", "rb") as f:
    inst = cloudpickle.load(f, fix_imports=True)
inst.plugins = plugins
for pl in plugins:
    pl.on_sim_init(inst)
n_scaled = 0
if a.mtbf_factor != 1.0 or a.mttr_factor != 1.0:
    for ev in inst.events.event_array:
        if isinstance(ev, BreakdownEvent) and ev.is_breakdown:
            ev.repeat_interval = Scaled(ev.repeat_interval, a.mtbf_factor)
            ev.length = Scaled(ev.length, a.mttr_factor)
            n_scaled += 1
random.seed(a.seed)
np.random.seed(a.seed)
Randomizer().random.seed(a.seed)
run_to = 3600 * 24 * (365 + a.days)
last = -1
while not inst.done:
    done = inst.next_decision_point()
    if done or inst.current_time > run_to:
        break
    m, lots, last = select(inst, inst.current_time, last)
    if lots is None:
        inst.usable_lots.clear()
        inst.lot_in_usable.clear()
        inst.next_step()
    else:
        inst.dispatch(m, lots)
inst.finalize()
cost, rows = inst.plugins[0].get_output_value()

# Table-1 classes: Lot_* = regular, HotLot_* = hot, SuperHotLot_* = superhot. Pooled over products (weights = completed lots).
cls = {"regular": "Lot_", "hot": "HotLot_", "superhot": "SuperHotLot_"}
out = {}
for c, prefix in cls.items():
    rs = [r for r in rows if str(r[0]).startswith(prefix)]
    done_n = sum(r[2] for r in rs)
    out[f"{c}_completed"] = done_n
    out[f"{c}_wip"] = sum(r[1] for r in rs)
    out[f"{c}_ct"] = sum(r[2] * r[5] for r in rs) / done_n if done_n else None
    out[f"{c}_ot"] = 100.0 * sum(r[3] for r in rs) / done_n if done_n else None
out.update(cost=float(cost), dataset=a.dataset, rule=a.rule, days=a.days, seed=a.seed, mtbf_factor=a.mtbf_factor,
           mttr_factor=a.mttr_factor, breakdown_events_scaled=n_scaled, run_s=round(time.time() - t0, 1),
           rows=[[str(r[0])] + [float(x) for x in r[1:]] for r in rows])
print(json.dumps(out))
