"""Builds the static web demo (docs/demo/index.html, served by GitHub Pages).

Tab 1 shows engine.estimate results for every input combination offered on the page.
Tab 2 replays the recorded answers of the sealed test (eval/results/test, T1).

    bash cases/A2_sme/setup.sh        # JaamSim, needed for A2
    A1_CACHE_ONLY=1 python docs/demo/make_demo.py
"""
import csv, glob, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("A1_CACHE_ONLY", "1")
from engine import Engine  # noqa: E402
import yaml  # noqa: E402

GRID = {
    "A2_sme": [{"workers": w, "portfolio": p} for w in [2, 3, 4, 5] for p in ["norm", "over20"]],
    "A3_warehouse": [{"reach_trucks": t, "policy": p} for t in [4, 6, 8, 9, 10, 12, 15] for p in ["SINGLE", "INTERLEAVE", "NEAREST"]],
    "A5_operator_line": [{"operators": n} for n in [1, 2, 3, 4, 5, 6]],
    "A1_smt2020": [{"dataset": d, "rule": r} for d in ["HVLM", "LVHM"] for r in ["fifo", "cr"]],
}
MODELS = [("Qwen 2.5 7B", "qwen2_5_7b-instruct"), ("Llama 3.1 8B", "llama3_1_8b"), ("Gemma 2 9B", "gemma2_9b")]


def key(params, kpi):
    return json.dumps(params, sort_keys=True, separators=(",", ":")) + "|" + kpi


def main():
    eng = Engine(str(ROOT / "cases"))
    cases = {}
    for c, grid in GRID.items():
        card = yaml.safe_load(open(ROOT / "cases" / c / "case_card.yaml"))
        res = {}
        for params in grid:
            for o in card["outputs"]:
                r = eng.estimate(c, o["name"], params)
                e = r.get("error") or {}
                ws = r.get("warnings") or []
                res[key(params, o["name"])] = {"s": r["status"], "m": r.get("mean"), "ci": r.get("ci95"), "n": r.get("replications"),
                                               "u": r.get("unit"), "w": [w.get("message") or w["code"] for w in ws],
                                               "wc": [w["code"] for w in ws], "e": e.get("message"), "pr": r.get("precision_reached")}
                print(c, params, o["name"], r["status"], flush=True)
        cases[c] = {"industry": card.get("industry"), "params": card["parameters"],
                    "outputs": [o["name"] + "|" + (o.get("unit") or "") for o in card["outputs"]],
                    "cannot": card.get("cannot_answer", []), "res": res}
    qs = []
    for f in sorted(glob.glob(str(ROOT / "cases/*/questions_test.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            qs.append({k: r[k] for k in ["qid", "case_id", "question", "type", "reference", "tol_low", "tol_high", "choices_ok", "source"]})
    ans = {}
    for name, f in MODELS:
        graded = {(r["qid"], r["arm"]): r["outcome"] for r in csv.DictReader(open(ROOT / f"eval/results/test/T1_{f}_graded.csv"))}
        for r in csv.DictReader(open(ROOT / f"eval/results/test/T1_{f}.csv", encoding="utf-8")):
            tools = json.loads(r["tools"] or "[]")
            ans[f'{name}|{r["qid"]}|{r["arm"]}'] = {
                "t": r["text"], "v": r["value"], "c": r["choice"], "r": r["refused"] == "1", "f": r["flags"],
                "o": graded[(r["qid"], r["arm"])],
                "tl": [[x["tool"], x.get("args"), x.get("status"), [w.get("code") if isinstance(w, dict) else w for w in x.get("warnings") or []]]
                       for x in tools]}
    data = json.dumps({"cases": cases, "qs": qs, "ans": ans}, default=str, separators=(",", ":"))
    here = Path(__file__).parent
    (here / "index.html").write_text((here / "template.html").read_text(encoding="utf-8").replace("__DATA__", data), encoding="utf-8")
    print("written", here / "index.html")


if __name__ == "__main__":
    main()
