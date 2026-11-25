"""Grade one answers file against several question files at once (development and test), with eval/grade.py unchanged.
Adds case_id, split and question type to every row so the analysis can group by them.
Usage: python eval/grade_all.py answers.csv cases/*/questions*.csv > answers_graded.csv
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grade import grade  # noqa: E402

if __name__ == "__main__":
    qs = {}
    for qf in sys.argv[2:]:
        for r in csv.DictReader(open(qf, encoding="utf-8")):
            qs[r["qid"]] = r
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["qid", "case_id", "split", "type", "model", "arm", "repeat", "outcome"])
    for a in csv.DictReader(open(sys.argv[1], encoding="utf-8")):
        q = qs.get(a["qid"])
        if q:
            out.writerow([a["qid"], q["case_id"], q.get("split") or "dev", q["type"], a.get("model"), a.get("arm"), a.get("repeat"), grade(q, a)])
