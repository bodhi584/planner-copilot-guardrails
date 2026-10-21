"""Run one SMT2020 scenario with a static dispatching rule (FIFO or CR).
Uses the open-source simulator of Tassel et al. (2023), MIT licence:
https://github.com/ingambe/RL4SemiconductorFabSched (commit 89467c6).
Set FAB_SIM to the cloned repo (default: ./RL4SemiconductorFabSched). Python 3.9 only.
Example: python run_static.py --dataset HVLM --rule fifo --days 180 --seed 0 --out hvlm_fifo_s0.json
"""
import sys, os, random, time, json, argparse
HERE=os.path.dirname(os.path.abspath(__file__))
FAB=os.environ.get('FAB_SIM', os.path.join(HERE,'RL4SemiconductorFabSched'))
sys.path.insert(0, FAB); sys.path.insert(0, os.path.join(HERE,'stubs'))
OUTDIR=os.getcwd(); os.chdir(os.path.join(FAB,'simulation','es'))
import numpy as np, cloudpickle
from simulation.classes import Lot
from simulation.dispatching.dispatcher import Dispatchers
from simulation.greedy import build_batch
from simulation.plugins.stats_plugin import StatPlugin
from simulation.randomizer import Randomizer
p=argparse.ArgumentParser();p.add_argument('--dataset',default='HVLM');p.add_argument('--rule',default='fifo')
p.add_argument('--days',type=float,default=2);p.add_argument('--seed',type=int,default=0);p.add_argument('--out',default=None)
a=p.parse_args()
PT={'fifo':Dispatchers.fifo_ptuple_for_lot,'cr':Dispatchers.cr_ptuple_for_lot}[a.rule]
def select(instance, current_time, last_sort_time):
    if last_sort_time != current_time:
        for lot in instance.usable_lots:
            lot.ptuple = PT(lot, current_time, None)
        last_sort_time = current_time
        instance.usable_lots.sort(key=lambda k: k.ptuple)
    lots = instance.usable_lots
    setup_machine = setup_batch = mrm = mrb = None; family_lock=None
    for i in range(len(lots)):
        lot = lots[i]
        if family_lock is None or family_lock == lot.actual_step.family:
            family_lock = lot.actual_step.family
            if lot.actual_step.setup_needed == "":
                for m in lot.waiting_machines:
                    if m.current_setup == "": return m, build_batch(lot, lots[i+1:]), last_sort_time
            for m in lot.waiting_machines:
                if lot.actual_step.setup_needed == "" or lot.actual_step.setup_needed == m.current_setup:
                    return m, build_batch(lot, lots[i+1:]), last_sort_time
                else:
                    if setup_machine is None and m.min_runs_left is None: setup_machine, setup_batch = m, i
                    if mrm is None: mrm, mrb = m, i
    if setup_machine is not None: return setup_machine, build_batch(lots[setup_batch], lots[setup_batch+1:]), last_sort_time
    return mrm, (build_batch(lots[mrb], lots[mrb+1:]) if mrm is not None else None), last_sort_time
t0=time.time()
plugins=[StatPlugin()]
with open(f"365days_{a.dataset}.pkl","rb") as f: inst=cloudpickle.load(f, fix_imports=True)
inst.plugins=plugins
for pl in plugins: pl.on_sim_init(inst)
t1=time.time()
random.seed(a.seed); np.random.seed(a.seed); Randomizer().random.seed(a.seed)
run_to=3600*24*(365+a.days); last=-1
while not inst.done:
    done=inst.next_decision_point()
    if done or inst.current_time>run_to: break
    m,lots,last=select(inst,inst.current_time,last)
    if lots is None:
        inst.usable_lots.clear(); inst.lot_in_usable.clear(); inst.next_step()
    else: inst.dispatch(m,lots)
inst.finalize()
cost,rows=inst.plugins[0].get_output_value()
res=dict(dataset=a.dataset,rule=a.rule,days=a.days,seed=a.seed,cost=float(cost),rows=[[str(r[0])]+[float(x) for x in r[1:]] for r in rows],load_s=t1-t0,run_s=time.time()-t1)
print(json.dumps(res))
if a.out: json.dump(res,open(os.path.join(OUTDIR,a.out),"w"))
