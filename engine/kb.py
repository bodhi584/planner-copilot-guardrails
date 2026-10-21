"""Keyword search over case-independent method notes
plus an index of the case card (meanings, notes, cannot_answer, synonyms)."""
import math
import re

METHOD_NOTES = [
    ("method:replications", "Simulation output is random. Never draw conclusions from a single run. Report the mean over several replications with a 95% confidence interval (t-distribution). If the CI is too wide for the decision, add replications. The engine does this automatically."),
    ("method:comparison", "To compare two alternatives use paired runs with common random numbers (same replication indices for both alternatives) and look at the CI of the difference. If the CI contains zero, the alternatives are not distinguishable at this sample size; say so instead of picking a winner, or add replications."),
    ("method:units", "Give every parameter in the unit of the case card (capabilities lists them), for example shift length in minutes: 8 h = 480 min. Alternatively pass {\"value\": 8, \"unit\": \"h\"}; the engine converts min, h, day and %, fraction. Values far outside the plausible range are rejected with a hint."),
    ("method:validity", "Results for parameter values outside the validated range of the case card are only indicative and carry the warning outside_valid_range. Report the warning to the user; do not drop it."),
    ("method:scope", "Questions the simulation model cannot answer (see cannot_answer of the case card, for example costs in euros) are refused. Say that the question is out of scope and what would be needed instead."),
]
STOP = set("the and for what does how many much with are can our this that from into than then when which will would should could about is it to of in on we a an be by or if do".split())


def _tok(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) >= 2 and w not in STOP]


def search(query, docs, k=3):
    """docs: list of (source, text). Score = sum of idf-like weights of query words found in the doc."""
    toks = [_tok(src + " " + text) for src, text in docs]
    df = {}
    for t in toks:
        for w in set(t):
            df[w] = df.get(w, 0) + 1
    n = len(docs)
    scored = sorted(((sum((w in t) * math.log(1 + n / df.get(w, n)) for w in set(_tok(query))), i)
                     for i, t in enumerate(toks)), reverse=True)
    return [{"source": docs[i][0], "text": docs[i][1]} for s, i in scored[:k] if s > 0]


def card_docs(card):
    """One document per parameter, output, note, plus cannot_answer and synonyms."""
    cid = card["case_id"]
    docs = []
    for p in card["parameters"]:
        extra = [f"{k} {p[k]}" for k in ("default", "valid_min", "valid_max", "allowed", "hint") if k in p]
        docs.append((f"case_card:{cid}:parameter:{p['name']}", f"{p['name']} ({p.get('unit')}): {p.get('meaning', '')} " + "; ".join(extra)))
    for o in card["outputs"]:
        docs.append((f"case_card:{cid}:output:{o['name']}", f"{o['name']} ({o.get('unit')}): {o.get('meaning', '')}"))
    for i, note in enumerate(card.get("notes") or []):
        docs.append((f"case_card:{cid}:note:{i + 1}", str(note)))
    docs.append((f"case_card:{cid}:cannot_answer", "This case cannot answer: " + "; ".join(card.get("cannot_answer") or [])))
    if card.get("synonyms"):
        docs.append((f"case_card:{cid}:synonyms", "Plain words and their parameter values: " + "; ".join(f"'{k}' means {v}" for k, v in card["synonyms"].items())))
    return docs


def lookup(query, card=None, k=3):
    return search(query, METHOD_NOTES + (card_docs(card) if card else []), k)
