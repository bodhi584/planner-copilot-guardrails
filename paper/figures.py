"""Figures for paper/planner_copilot.tex from the graded test files (run from the repository root)."""
import csv
import glob
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = ("correct", "cautious", "confidently_wrong")
COL = {"correct": "#2e7d32", "cautious": "#f9a825", "confidently_wrong": "#c62828"}
rows = [r for f in glob.glob("eval/results/test/T1_*_graded.csv") for r in csv.DictReader(open(f))]
c = Counter((r["type"], r["arm"], r["outcome"]) for r in rows)
types = ["numeric", "choice", "flag", "scope"]
fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.4), sharey=False)
for ax, t in zip(axes, types):
    bottom = [0, 0, 0]
    for o in OUT:
        v = [c[(t, a, o)] for a in "ABC"]
        ax.bar(list("ABC"), v, bottom=bottom, color=COL[o], label=o.replace("_", " "), width=0.7)
        bottom = [b + x for b, x in zip(bottom, v)]
    ax.set_title(t, fontsize=9)
    ax.tick_params(labelsize=8)
axes[0].set_ylabel("answers (3 models)", fontsize=8)
axes[-1].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.0, 1.0))
fig.tight_layout()
fig.savefig("paper/fig_types.pdf", bbox_inches="tight")

import sys
sys.path.insert(0, "eval")
from analyse import figure, load  # noqa: E402
figure(load("T1_*_graded.csv"), "paper/fig_main.pdf")
