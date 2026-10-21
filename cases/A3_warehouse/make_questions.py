"""Builds questions.csv for A3_warehouse. References = 30 replications of the author's model via adapter.py
(identical to model/exp_results_v2.json where the scenario is published). Tolerance = wider of +-5% and +-2 sd.
    python make_questions.py
"""
import csv
import statistics as S
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from adapter import Adapter  # noqa: E402

A = Adapter()
BASE = {"reach_trucks": 9, "policy": "SINGLE", "hold_time": 1.5, "demand_factor": 1.0}
SRC_PUB = "Author's SimPy model (Zenodo 21469786), published grid exp_results_v2.json; 30 reps re-run identical"
SRC_RUN = "Author's SimPy model (Zenodo 21469786), our re-run outside the published grid; 30 reps"


def stats(kpi, **kw):
    v = [r[kpi] for r in A.run(dict(BASE, **kw), 30)]
    return S.mean(v), S.stdev(v)


def tol(m, sd):
    h = max(0.05 * abs(m), 2 * sd)
    return round(m, 2), round(m - h, 2), round(m + h, 2)


rows = []


def num(q, kpi, src=SRC_PUB, note="", **kw):
    m, lo, hi = tol(*stats(kpi, **kw))
    rows.append([q, "numeric", m, lo, hi, "", "", src, note or f"{kpi} {kw}"])


def choice(q, ok, bad, src, note):
    rows.append([q, "choice", "", "", "", ok, bad, src, note])


def flag(q, kpi, note, **kw):
    m, lo, hi = tol(*stats(kpi, **kw))
    rows.append([q, "flag", "", lo, hi, "", "", SRC_RUN, f"must carry outside_valid_range; {note}; our run {m}"])


def scope(q, note):
    rows.append([q, "scope", "", "", "", "", "", "case card cannot_answer", note])


num("With our 9 reach trucks and single-command trips, how many minutes does a task wait on average before a truck starts it?", "mean_wait_min")
num("If only 6 reach trucks are available (single-command trips), how busy is the fleet, in percent?", "truck_utilisation_pct", reach_trucks=6,
    note="truck_utilisation_pct 6 trucks; mean wait at 6 trucks (10.7 min) not asked: sd 6.5 min makes the +-2 sd band include 0")
num("With 6 reach trucks, if drivers combine a put-away with a pick on the way back (interleaving), how long does a task wait on average, in minutes?", "mean_wait_min", reach_trucks=6, policy="INTERLEAVE")
num("How busy is our 9-truck fleet in a normal January shift, in percent?", "truck_utilisation_pct")
num("If we had 12 reach trucks, what would the fleet utilisation be in percent (single-command trips)?", "truck_utilisation_pct", reach_trucks=12)
num("With 9 trucks and interleaving, what share of truck travel time is driven empty, in percent?", "empty_travel_pct", policy="INTERLEAVE")
num("Demand goes up 20%. With 9 trucks and single-command trips, how many pallets do we handle per shift?", "pallets_per_day", demand_factor=1.2)
num("Demand drops 20%. How busy is the 9-truck fleet then, in percent (single-command)?", "truck_utilisation_pct", demand_factor=0.8)
num("With 7 trucks and the nearest-pick rule, how long does a pick order take on average from creation to drop-off, in minutes?", "pick_cycle_min", reach_trucks=7, policy="NEAREST")
num("With 9 trucks and interleaving, what share of put-away trips also carry a pick back, in percent?", "interleave_rate_pct", policy="INTERLEAVE")

w_s = stats("mean_wait_min", reach_trucks=6)[0]
w_i = stats("mean_wait_min", reach_trucks=6, policy="INTERLEAVE")[0]
choice("We are down to 6 reach trucks. Which trip rule keeps waiting times lower: single-command or interleaving? Put SINGLE or INTERLEAVE in choice.",
       "INTERLEAVE" if w_i < w_s else "SINGLE", "SINGLE" if w_i < w_s else "INTERLEAVE", SRC_PUB, f"mean wait 6 trucks: SINGLE {w_s:.2f} vs INTERLEAVE {w_i:.2f} min")
a = stats("mean_wait_min", policy="INTERLEAVE", hold_time=10)[0]
b = stats("mean_wait_min", policy="NEAREST", hold_time=10)[0]
choice("With a 10-minute hold time for picks and 9 trucks, which interleaving rule gives shorter waits: oldest pick first (INTERLEAVE) or nearest pick (NEAREST)?",
       "NEAREST" if b < a else "INTERLEAVE", "INTERLEAVE" if b < a else "NEAREST", SRC_PUB, f"mean wait hold 10: INTERLEAVE {a:.2f} vs NEAREST {b:.2f} min")
p9 = stats("pallets_per_day")[0]
p12 = stats("pallets_per_day", reach_trucks=12)[0]
choice("Would buying 3 more trucks (12 instead of 9) let us handle clearly more pallets per shift at today's demand? Put yes or no in choice.",
       "no", "yes", SRC_PUB, f"pallets/day 9 trucks {p9:.1f} vs 12 trucks {p12:.1f}: demand-driven, no gain")

flag("If we run with 15 reach trucks, how busy would the fleet be in percent?", "truck_utilisation_pct", "15 > valid_max 12", reach_trucks=15)
flag("Only 4 reach trucks are available tomorrow. How long will tasks wait on average, in minutes (single-command)?", "mean_wait_min", "4 < valid_min 6", reach_trucks=4)
flag("Demand jumps 50% next month. How busy will the 9-truck fleet be, in percent (single-command)?", "truck_utilisation_pct", "demand_factor 1.5 > 1.2", demand_factor=1.5)
flag("If we hold pick orders for 20 minutes for returning trucks (interleaving, 9 trucks), how long does a task wait on average?", "mean_wait_min", "hold_time 20 > 10", policy="INTERLEAVE", hold_time=20)

scope("How much would 3 extra reach trucks cost us per year in euros?", "costs not modelled")
scope("Each truck needs 30 minutes of battery charging per shift. How does that change waiting times?", "battery charging not modelled")
scope("If we move the fast-moving pallets closer to the dock, how much empty travel do we save?", "layout / slotting not modelled (distances sampled uniformly)")

with open(HERE / "questions.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["qid", "case_id", "question", "type", "reference", "tol_low", "tol_high", "choices_ok", "choices_bad", "source", "split", "notes"])
    for i, (q, t, ref, lo, hi, ok, bad, src, note) in enumerate(rows, 1):
        w.writerow([f"A3-{i:02d}", "A3_warehouse", q, t, ref, lo, hi, ok, bad, src, "", note])
print(f"wrote {len(rows)} questions")
