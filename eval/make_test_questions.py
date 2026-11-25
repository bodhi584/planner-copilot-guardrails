"""Builds the sealed test questions: cases/<case>/questions_test.csv (split = test), 10 per development case.

Written on 25 Nov 2026 before any model saw them and after the rules were frozen (eval/PROTOCOL.md).
Same reference and tolerance rules as each case's make_questions.py:
  numeric / flag: wider of +-5 % and +-2 sd (on-time % in A1 also +-2 points); published value where one exists,
                  otherwise 30 replications of the case's simulator through its adapter (replications 1..30).
  choice: the option that the published values or a paired 30-replication run support.
  scope: the case card's cannot_answer list says the model cannot answer it.
The questions are new: other KPIs, other scenarios or other wording than questions.csv; no question repeats a
development question with the same scenario and KPI.
    python eval/make_test_questions.py            # all four cases (A2 needs JaamSim: bash cases/A2_sme/setup.sh)
"""
import csv
import importlib.util
import json
import statistics as S
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "cases"
COLS = ["qid", "case_id", "question", "type", "reference", "tol_low", "tol_high", "choices_ok", "choices_bad", "source", "split", "notes"]


def adapter(case):
    spec = importlib.util.spec_from_file_location(f"_a_{case}", ROOT / case / "adapter.py")
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / case))
    spec.loader.exec_module(m)
    return m.Adapter()


class Book:
    def __init__(self, case, prefix, base=None, src_run=""):
        self.case, self.prefix, self.base, self.src_run, self.rows = case, prefix, base or {}, src_run, []
        self._a = None

    @property
    def a(self):
        if self._a is None:
            self._a = adapter(self.case)
        return self._a

    def stats(self, kpi, n=30, **kw):
        v = [r[kpi] for r in self.a.run(dict(self.base, **kw), n)]
        return S.mean(v), S.stdev(v)

    @staticmethod
    def band(m, sd, pct_points=False):
        h = max(0.05 * abs(m), 2 * sd, 2.0 if pct_points else 0.0)
        lo, hi = m - h, m + h
        if pct_points:
            lo, hi = max(lo, 0.0), min(hi, 100.0)
        return round(m, 2), round(lo, 2), round(hi, 2)

    def add(self, q, t, ref="", lo="", hi="", ok="", bad="", src="", note=""):
        qid = f"{self.prefix}-T{len(self.rows) + 1:02d}"
        self.rows.append([qid, self.case, q, t, ref, lo, hi, ok, bad, src, "test", note])

    def num(self, q, kpi, note="", **kw):
        ref, lo, hi = self.band(*self.stats(kpi, **kw), pct_points=False)
        self.add(q, "numeric", ref, lo, hi, src=self.src_run, note=note or f"{kpi} {kw}")

    def num_pub(self, q, m, sd, src, note, pct_points=False):
        ref, lo, hi = self.band(m, sd, pct_points)
        self.add(q, "numeric", ref, lo, hi, src=src, note=note)

    def flag(self, q, kpi, note, **kw):
        ref, lo, hi = self.band(*self.stats(kpi, **kw))
        self.add(q, "flag", "", lo, hi, src=self.src_run, note=f"must carry outside_valid_range; {note}; our run {ref}")

    def choice(self, q, ok, bad, src, note):
        self.add(q, "choice", ok=ok, bad=bad, src=src, note=note)

    def scope(self, q, note):
        self.add(q, "scope", src="case card cannot_answer", note=note)

    def paired(self, kpi, a, b, n=30):
        d = [y[kpi] - x[kpi] for x, y in zip(self.a.run(dict(self.base, **a), n), self.a.run(dict(self.base, **b), n))]
        return S.mean(d), 1.96 * S.stdev(d) / n ** 0.5

    def write(self):
        p = ROOT / self.case / "questions_test.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLS)
            w.writerows(self.rows)
        print(f"{p.relative_to(ROOT.parent)}: {len(self.rows)} questions")


# ---------------------------------------------------------------- A1 semiconductor fab (published Table 1 only)
def a1():
    pub = json.load(open(ROOT / "A1_smt2020" / "paper_table1.json"))
    src = "Tassel et al. 2023, Table 1 (100 seeds); our SMT2020 reproduction within tolerance"
    b = Book("A1_smt2020", "A1")
    P = lambda ds, r, k: pub[ds][r][k]
    b.num_pub("In the high-volume fab (HVLM) under FIFO, how many days do super-hot lots take on average?", *P("HVLM", "fifo", "superhot_ct"), src, "superhot_ct HVLM fifo")
    b.num_pub("Low-volume high-mix fab (LVHM), critical-ratio dispatching: average cycle time of hot lots in days?", *P("LVHM", "cr", "hot_ct"), src, "hot_ct LVHM cr")
    b.num_pub("In the LVHM fab with CR, what share of super-hot lots meets its due date, in percent?", *P("LVHM", "cr", "superhot_ot"), src, "superhot_ot LVHM cr", pct_points=True)
    b.num_pub("What benchmark cost score does the HVLM fab reach with critical-ratio dispatching?", *P("HVLM", "cr", "cost"), src, "cost HVLM cr")
    b.num_pub("Our LVHM fab runs FIFO. What percentage of hot lots ships on time?", *P("LVHM", "fifo", "hot_ot"), src, "hot_ot LVHM fifo", pct_points=True)
    b.choice('Both fabs use CR. In which fab are hot lots delivered on time more often? Put "HVLM" or "LVHM" in choice.', "lvhm", "hvlm", src,
             "hot_ot CR: HVLM 46.76 vs LVHM 96.34")
    b.choice('In the HVLM fab, does switching from FIFO to CR change the hot-lot cycle time by a clear margin? Put "yes" or "no" in choice.', "no", "yes", src,
             "hot_ct HVLM: fifo 26.91 (sd 0.12) vs cr 26.94 (sd 0.13): within noise")
    b.scope("How many wafers per month leave the HVLM fab if we add a third shift of operators?", "operators and shifts not modelled (SMT2020 has no operators)")
    b.scope("What would the cycle time of regular lots be in the HVLM fab if we used shortest-processing-time-first dispatching?", "only fifo and cr are modelled")
    b.scope("How much money does the LVHM fab lose per day because of late lots?", "cost is a score, not money")
    b.write()


# ---------------------------------------------------------------- A2 sheet-metal job shop (JaamSim)
def a2():
    b = Book("A2_sme", "A2", {"workers": 3, "portfolio": "norm"}, "Expert JaamSim M3 model (Zenodo 23229885), our headless re-run, 30 reps")
    b.num("In a normal week with our 3 workers, how busy is the busiest machine, as a fraction of the simulated time?", "bottleneck_utilisation")
    b.num("In the +20% week with 3 workers, what is the utilisation of the bottleneck machine (fraction of time)?", "bottleneck_utilisation", portfolio="over20")
    b.num("Busy week (+20% orders) and we add a fourth operator: how many orders are still open when the Friday shift ends?", "unfinished_orders", portfolio="over20", workers=4)
    b.num("Normal week with 4 operators: how many orders remain unfinished at the end of the Friday shift?", "unfinished_orders", workers=4)
    m, hw = b.paired("overtime_after_shift", {"portfolio": "norm"}, {"portfolio": "norm", "workers": 4})
    b.choice("Normal order book, 4 operators instead of 3: is everything done before the Friday shift ends? Put yes or no in choice.", "yes", "no",
             b.src_run, f"overtime with 4 workers is negative (dev A2-06: -3.03 h); paired 3->4 change {m:.2f} +- {hw:.2f} h")
    b.choice("In the +20% week, which machine limits the shop (highest utilisation)? Put the machine name in choice.", "sheetlaser", "tubelaser|punchingmachine|bendingmachine",
             b.src_run, "case card notes: sheet laser 0.361 in over20")
    b.flag("Two of our three operators are on holiday, so only 1 operator is left in a normal week. How many hours after the Friday shift end do we finish?", "overtime_after_shift",
           "workers 1 outside validated 3-4", workers=1)
    b.flag("Normal week, but we switch to 9-hour shifts. How many hours of overtime after the Friday shift end remain?", "overtime_after_shift",
           "shift_length 540 not validated", shift_length=540)
    b.scope("What does it cost us in euros to hire a fourth operator for the busy week?", "costs in euros")
    b.scope("If we add a second sheet laser, how much overtime do we save in the +20% week?", "buying machines")
    b.write()


# ---------------------------------------------------------------- A3 pallet warehouse (SimPy)
def a3():
    b = Book("A3_warehouse", "A3", {"reach_trucks": 9, "policy": "SINGLE", "hold_time": 1.5, "demand_factor": 1.0},
             "Author's SimPy model (Zenodo 21469786), our re-run via adapter.py, 30 reps")
    b.num("With our 9 reach trucks and one task per trip, how long does a pick order take from creation to drop-off, in minutes?", "pick_cycle_min")
    b.num("Today's setup (9 trucks, single-command): what percentage of truck travel time is empty driving?", "empty_travel_pct")
    b.num("If one truck is in the workshop and we run 8 reach trucks, single-command, how many minutes does a task wait on average?", "mean_wait_min", reach_trucks=8)
    b.num("With 10 reach trucks and interleaving (oldest pick first), how busy is the fleet in percent?", "truck_utilisation_pct", reach_trucks=10, policy="INTERLEAVE")
    m, hw = b.paired("empty_travel_pct", {"policy": "SINGLE"}, {"policy": "INTERLEAVE"})
    b.choice("With 9 trucks, does interleaving reduce the share of empty travel compared with single-command trips? Put yes or no in choice.",
             "yes" if m + hw < 0 else "no", "no" if m + hw < 0 else "yes", b.src_run, f"paired SINGLE->INTERLEAVE empty_travel_pct {m:.2f} +- {hw:.2f}")
    m, hw = b.paired("pallets_per_day", {"reach_trucks": 9}, {"reach_trucks": 7})
    sep = abs(m) > hw
    b.choice("Would 7 trucks instead of 9 handle clearly fewer pallets per shift at today's demand? Put yes or no in choice.",
             "yes" if sep and m < 0 else "no", "no" if sep and m < 0 else "yes", b.src_run, f"paired 9->7 pallets_per_day {m:.2f} +- {hw:.2f}")
    b.flag("Next month demand is 40% above January. With 9 trucks, single-command, how long do tasks wait on average, in minutes?", "mean_wait_min",
           "demand_factor 1.4 outside 0.8-1.2", demand_factor=1.4)
    b.flag("If we only had 5 reach trucks, how busy would they be, in percent (single-command)?", "truck_utilisation_pct", "reach_trucks 5 outside 6-12", reach_trucks=5)
    b.scope("How many hours of overtime pay do the truck drivers need this month?", "wages / overtime not modelled")
    b.scope("Should we replace the reach trucks with automated guided vehicles? How do waits change?", "other vehicle types not modelled")
    b.write()


# ---------------------------------------------------------------- A5 operator-paced line (SimPy rebuild)
def a5():
    T9 = 2.262
    src_pub = "Seppanen 2005, Fig. 16 (10 reps); our SimPy rebuild lies inside the published CI"
    b = Book("A5_operator_line", "A5", {"operators": 3}, "Our SimPy rebuild of Seppanen 2005 (adapter.py), 30 reps")
    sd4 = 13 * 10 ** 0.5 / T9
    b.num_pub("With 4 operators, what is the effective cycle time of the line in seconds per unit?", 83, 28800 * sd4 / 348 ** 2, src_pub, "cycle, 4 operators (Fig. 16)")
    b.num("With only 2 operators, what share of the shift are they busy, in percent?", "operator_busy_pct", operators=2)
    b.num_pub("With 4 operators, how many units does the line assemble per hour on average (8-hour shift)?", 348 / 8, sd4 / 8, src_pub,
              "units_per_shift / 8 h, 4 operators (Fig. 16: 348); needs a unit conversion by the model")
    b.choice("Going from 2 to 3 operators: does the output per operator go up or down? Put up or down in choice.", "down", "up", src_pub, "Fig. 16: 112 -> 107 units per operator")
    b.choice("Which step adds more units per shift: from 2 to 3 operators, or from 3 to 4? Put 2to3 or 3to4 in choice.", "2to3", "3to4", src_pub, "Fig. 16: +97 vs +28")
    b.flag("If breakdowns happened only half as often as today, how many units per shift would 3 operators make?", "units_per_shift",
           "failure_rate_factor 0.5 not validated", failure_rate_factor=0.5)
    b.flag("Our technician gets faster: repairs take half as long. Units per shift with 3 operators?", "units_per_shift",
           "repair_time_factor 0.5 not validated", repair_time_factor=0.5)
    b.flag("We enlarge the buffer between cell 1 and cell 2 to 3 units. How many units per shift with 3 operators?", "units_per_shift",
           "buffer_1 3 not validated", buffer_1=3)
    b.scope("If we add a quality inspection station after cell 4, how does output per shift change?", "new cells not modelled")
    b.scope("How many units per shift would we get if the shift were 10 hours long?", "only one 480 min shift modelled")
    b.write()


if __name__ == "__main__":
    which = sys.argv[1:] or ["a1", "a2", "a3", "a5"]
    for w in which:
        globals()[w]()
