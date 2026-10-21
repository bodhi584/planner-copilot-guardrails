"""Builds questions.csv for A1_smt2020. References = Tassel et al. (2023) Table 1 (paper_table1.json, 100 seeds, mean and
sd). Tolerance = wider of +-5 %, +-2 published sd and, for on-time %, +-2 points (same rule as reproduce.py).
Our reproduction: 28 of 28 Table-1 values inside these bands (reproduce_result.md).
No flag items yet: breakdown what-ifs need extra
precomputed scenarios (each 180-day run takes 30-45 min).
    python make_questions.py
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUB = json.load(open(HERE / "paper_table1.json"))
SRC = "Tassel et al. 2023, Table 1 (100 seeds); our SMT2020 reproduction within tolerance"
rows = []


def num(q, ds, rule, kpi):
    m, sd = PUB[ds][rule][kpi]
    h = max(0.05 * abs(m), 2 * sd, 2.0 if kpi.endswith("_ot") else 0.0)
    lo, hi = m - h, m + h
    if kpi.endswith("_ot"):
        lo, hi = max(lo, 0.0), min(hi, 100.0)
    rows.append([q, "numeric", m, round(lo, 2), round(hi, 2), "", "", SRC, f"{kpi} {ds} {rule}"])


def choice(q, ok, bad, note, src=SRC):
    rows.append([q, "choice", "", "", "", ok, bad, src, note])


def scope(q, note):
    rows.append([q, "scope", "", "", "", "", "", "case card cannot_answer", note])


num("In the high-volume fab (HVLM) with FIFO dispatching, what is the average cycle time of regular lots, in days?", "HVLM", "fifo", "regular_ct")
num("In the HVLM fab with critical-ratio (CR) dispatching, what is the average cycle time of regular lots, in days?", "HVLM", "cr", "regular_ct")
num("In the low-volume high-mix fab (LVHM) with FIFO, what is the average cycle time of regular lots, in days?", "LVHM", "fifo", "regular_ct")
num("In the LVHM fab with CR dispatching, what is the average cycle time of regular lots, in days?", "LVHM", "cr", "regular_ct")
num("In the HVLM fab with CR, how many days does a hot lot take on average from release to completion?", "HVLM", "cr", "hot_ct")
num("In the HVLM fab with FIFO, what percentage of hot lots is finished by its due date?", "HVLM", "fifo", "hot_ot")
num("In the LVHM fab with CR, what percentage of hot lots is delivered on time?", "LVHM", "cr", "hot_ot")
num("In the LVHM fab with FIFO, what is the average cycle time of super-hot lots, in days?", "LVHM", "fifo", "superhot_ct")
num("In the HVLM fab with CR, what percentage of regular lots is delivered on time?", "HVLM", "cr", "regular_ot")
num("What is the benchmark cost score of the LVHM fab under FIFO?", "LVHM", "fifo", "cost")
num("Our high-volume fab works first-come-first-served. Roughly how many days does a normal lot spend in the fab?", "HVLM", "fifo", "regular_ct")
num("Low-volume high-mix fab, first-in-first-out: how long, in days, do standard lots take end to end?", "LVHM", "fifo", "regular_ct")
num("How reliable is delivery of our urgent (hot) lots in the high-volume fab with FIFO? Give the on-time percentage.", "HVLM", "fifo", "hot_ot")
choice('For the HVLM fab, which dispatching rule gives the lower cost score? Put "fifo", "cr" or "no_difference" in choice.',
       "fifo", "cr", "cost HVLM: fifo 38,014 vs cr 39,813 (sd 1,328 / 900); no_difference = cautious")
choice('For the LVHM fab, which dispatching rule gives the lower cost score? Put "fifo", "cr" or "no_difference" in choice.',
       "fifo", "cr", "cost LVHM: fifo 102,171 vs cr 108,856 (sd 2,498 / 2,044)")
choice('We run the HVLM fab with FIFO. Would switching to CR shorten the average cycle time of regular lots? Put "cr" if CR is faster, "fifo" if FIFO is faster, "no_difference" otherwise.',
       "cr", "fifo", "regular_ct HVLM: fifo 72.57 vs cr 70.80 (sd 0.61 / 0.60)")
choice('Is the SMT2020 cost score an amount of money in euros? Put "yes" or "no" in choice.', "no", "yes",
       "case card: cost is a benchmark score (tardiness + cycle-time penalty), not money", src="Tassel et al. 2023, Sec. 4")
scope("If we buy 5 more lithography tools for the HVLM fab, by how many days does the regular cycle time drop?", "buying tools")
scope("How many euros per year would the LVHM fab save by switching from FIFO to CR?", "costs in euros")
scope("What would the regular-lot cycle time of the HVLM fab be with the EDD (earliest due date) rule?", "other dispatching rules")
scope("With two more operators per shift in the HVLM fab, how much shorter would the cycle time be?", "operators: SMT2020 models none (Kopp 2020 p. 523)")

with open(HERE / "questions.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["qid", "case_id", "question", "type", "reference", "tol_low", "tol_high", "choices_ok", "choices_bad", "source", "split", "notes"])
    for i, r in enumerate(rows, 1):
        w.writerow([f"A1-{i:02d}", "A1_smt2020", r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], "", r[8]])
print(f"wrote {len(rows)} questions")
