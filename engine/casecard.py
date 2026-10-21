"""Load and validate cases/<case_id>/case_card.yaml (fields: engine/DESIGN.md section 5)."""
import yaml


def validate(card):
    """Return a list of problems (empty list = card is usable by the engine)."""
    bad = []
    if not isinstance(card, dict):
        return ["case card is not a YAML mapping"]
    for key in ("case_id", "parameters", "outputs", "replications", "cannot_answer"):
        if key not in card:
            bad.append(f"missing top-level field '{key}'")
    for p in card.get("parameters") or []:
        if "name" not in p:
            bad.append(f"parameter without name: {p}")
    for o in card.get("outputs") or []:
        if "name" not in o:
            bad.append(f"output without name: {o}")
    if not isinstance((card.get("replications") or {}).get("ours_min"), int):
        bad.append("replications.ours_min must be an integer")
    return bad


def load_card(path):
    with open(path, encoding="utf-8") as f:
        card = yaml.safe_load(f)
    bad = validate(card)
    if bad:
        raise ValueError(f"{path}: " + "; ".join(bad))
    card.setdefault("refuse_keywords", [])
    card.setdefault("synonyms", {})
    return card
