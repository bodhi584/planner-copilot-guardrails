"""Experiment runner: questions x arms x repeats through the workflow (agent/flow.py); one answers.csv row per answer (resumable).

    python -m eval.run --cases cases --questions cases/A3_warehouse/questions.csv --arms A,B,C \
        --model qwen2.5:7b-instruct --base-url http://localhost:11434/v1 --repeats 1 --out eval/results/answers.csv
    python eval/grade.py cases/A3_warehouse/questions.csv eval/results/answers.csv > graded.csv
Use only train/val questions (split column) during development; --split train filters.
"""
import argparse
import csv
import json
import os
from pathlib import Path

from agent.flow import answer
from agent.llm import LLM

COLS = ["qid", "case_id", "model", "arm", "repeat", "value", "choice", "flags", "refused", "text", "seconds", "llm_seconds", "tools"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="cases")
    ap.add_argument("--questions", nargs="+", required=True)
    ap.add_argument("--arms", default="A,B,C")
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"))
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--split", default=None, help="only questions whose split column equals this (empty split = all)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default="eval/results/answers.csv")
    a = ap.parse_args(argv)
    llm = LLM(a.model, base_url=a.base_url)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {(r["qid"], r["model"], r["arm"], r["repeat"]) for r in csv.DictReader(open(out))}
    new = not out.exists()
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new:
            w.writeheader()
        qs = []
        for qf in a.questions:
            qs += [q for q in csv.DictReader(open(qf)) if not a.split or q.get("split") in ("", a.split)]
        qs = qs[: a.limit] if a.limit else qs
        for q in qs:
            for arm in a.arms.split(","):
                for rep in range(1, a.repeats + 1):
                    key = (q["qid"], a.model, arm, str(rep))
                    if key in done:
                        continue
                    try:
                        r = answer(q["question"], q["case_id"], arm, llm, cases_root=a.cases)
                    except Exception as e:  # keep the run going; the row records the failure
                        r = {"value": None, "choice": "", "refused": False, "flags": [], "text": f"ERROR {type(e).__name__}: {e}",
                             "seconds": 0, "llm_seconds": 0, "tools": []}
                    w.writerow({"qid": q["qid"], "case_id": q["case_id"], "model": a.model, "arm": arm, "repeat": rep,
                                "value": "" if r["value"] is None else r["value"], "choice": r["choice"], "flags": ";".join(r["flags"]),
                                "refused": int(bool(r["refused"])), "text": r["text"], "seconds": r["seconds"],
                                "llm_seconds": r["llm_seconds"], "tools": json.dumps(r["tools"], default=str)})
                    f.flush()
                    print(q["qid"], arm, rep, r["value"], r["choice"], r["flags"], "refused" if r["refused"] else "", f"{r['seconds']}s", flush=True)


if __name__ == "__main__":
    main()
