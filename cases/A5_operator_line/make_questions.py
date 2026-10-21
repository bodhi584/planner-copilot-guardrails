"""Builds questions.csv for A5_operator_line.
Published scenarios (Fig. 16): reference = published mean, tolerance = wider of +-5% and +-2 sd, with
sd = CI half-width * sqrt(10) / t(0.975, 9). Other references: 30 replications of our rebuild (adapter.py).
Operator moves are not asked: the rebuild does not reproduce them within 5% (see case card).
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
T9 = 2.262
FIG16 = {2: (223, 9, 112, 129), 3: (320, 15, 107, 90), 4: (348, 13, 87, 83)}   # units, hw, units/operator, cycle s
SRC_PUB = "Seppanen 2005, Fig. 16 (10 reps); our SimPy rebuild lies inside the published CI"
SRC_RUN = "Our SimPy rebuild of Seppanen 2005 (adapter.py), 30 reps"
rows = []


def band(m, sd):
    h = max(0.05 * abs(m), 2 * sd)
    return round(m, 2), round(m - h, 2), round(m + h, 2)


def run(kpi, n=30, **kw):
    v = [r[kpi] for r in A.run(dict({"operators": 3}, **kw), n)]
    return S.mean(v), S.stdev(v)


def pub(q, ops, which):
    u, hw, upo, cyc = FIG16[ops]
    sd_u = hw * 10 ** 0.5 / T9
    if which == "units":
        m, sd = u, sd_u
    elif which == "upo":
        m, sd = upo, sd_u / ops
    else:  # cycle time 28,800 / units: delta-method sd
        m, sd = cyc, 28800 * sd_u / u ** 2
    ref, lo, hi = band(m, sd)
    rows.append([q, "numeric", ref, lo, hi, "", "", SRC_PUB, f"{which}, {ops} operators"])


def num(q, kpi, **kw):
    ref, lo, hi = band(*run(kpi, **kw))
    rows.append([q, "numeric", ref, lo, hi, "", "", SRC_RUN, f"{kpi} {kw}"])


def flag(q, kpi, note, **kw):
    ref, lo, hi = band(*run(kpi, **kw))
    rows.append([q, "flag", "", lo, hi, "", "", SRC_RUN, f"must carry outside_valid_range; {note}; our run {ref}"])


def scope(q, note):
    rows.append([q, "scope", "", "", "", "", "", "case card cannot_answer", note])


pub("With 3 operators on the line, how many units do we assemble in one 8-hour shift?", 3, "units")
pub("Two operators are off sick, so only 2 operators run the line. How many units per shift can we expect?", 2, "units")
pub("If we staff the line with 4 operators, how many units per shift do we get?", 4, "units")
pub("With 2 operators, how many units does each operator produce per shift on average?", 2, "upo")
pub("With 4 operators, how many units per operator per shift?", 4, "upo")
pub("With 3 operators, what is the effective cycle time of the line in seconds per unit?", 3, "cycle")
pub("With only 2 operators, what is the effective cycle time in seconds per unit?", 2, "cycle")
pub("With 3 operators, how many units per operator per shift?", 3, "upo")
num("With 3 operators, what share of the shift are the operators busy (assembly, duties, repairs), in percent?", "operator_busy_pct")
num("With 4 operators, what share of the shift are the operators busy, in percent?", "operator_busy_pct", operators=4)

rows.append(["Going from 3 to 4 operators: does output per operator go up or down? Put up or down in choice.", "choice", "", "", "", "down", "up",
             SRC_PUB, "Fig. 16: 107 -> 87 units per operator"])
d = [b["units_per_shift"] - a["units_per_shift"] for a, b in zip(A.run({"operators": 3}, 30), A.run({"operators": 4}, 30))]
hw = 1.96 * S.stdev(d) / len(d) ** 0.5
rows.append(["Does a 4th operator raise the line output per shift by a clear margin, or is the difference within noise? Put yes or no in choice.", "choice", "", "", "", "yes", "no",
             f"{SRC_PUB}; paired re-run (30 reps): +{S.mean(d):.1f} +- {hw:.1f} units", "published 320 -> 348"])
rows.append(["Can 2 operators reach 250 units per shift? Put yes or no in choice.", "choice", "", "", "", "no", "yes", SRC_PUB, "Fig. 16: 2 operators 223 (CI 214-232)"])

flag("If the machines failed twice as often as today, how many units per shift would 3 operators make?", "units_per_shift", "failure_rate_factor 2 not validated", failure_rate_factor=2.0)
flag("Repairs take three times longer because the technician is shared with another line. Units per shift with 3 operators?", "units_per_shift", "repair_time_factor 3 not validated", repair_time_factor=3.0)
flag("We could make the buffer between cell 2 and cell 3 hold 5 units. How many units per shift with 3 operators?", "units_per_shift", "buffer_2 5 not validated (paper: 2)", buffer_2=5)
flag("If we put 5 operators on the line, how many units per shift?", "units_per_shift", "operators 5 > valid_max 4", operators=5)

scope("What do the operator wages per assembled unit come to in euros with 4 operators?", "costs not modelled")
scope("We want to add a fifth cell for packaging after cell 4. How does output change?", "new cells not modelled")
scope("If we run a second shift with 3 operators, how many units per day do we get?", "only one 8 h shift modelled")

with open(HERE / "questions.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["qid", "case_id", "question", "type", "reference", "tol_low", "tol_high", "choices_ok", "choices_bad", "source", "split", "notes"])
    for i, (q, t, ref, lo, hi, ok, bad, src, note) in enumerate(rows, 1):
        w.writerow([f"A5-{i:02d}", "A5_operator_line", q, t, ref, lo, hi, ok, bad, src, "", note])
print(f"wrote {len(rows)} questions")
