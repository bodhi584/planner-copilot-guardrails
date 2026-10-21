"""The checks of DESIGN.md section 2 as pure functions: scope, units (+ defaults), validity.
Refusals and errors are raised as exceptions; core.py turns them into results."""
import math
import re


class Refused(Exception):
    def __init__(self, reason, cannot_answer):
        super().__init__(reason)
        self.reason, self.cannot_answer = reason, list(cannot_answer)


class Fail(Exception):
    def __init__(self, code, message, hint=None):
        super().__init__(message)
        self.code, self.message, self.hint = code, message, hint


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def raw(v):
    """Unit conversion off: take the number of a {"value", "unit"} object as it is."""
    return v["value"] if isinstance(v, dict) and "value" in v else v


# ---- 1. scope ---------------------------------------------------------------------------------
def check_scope(card, kpi, param_sets, question=None):
    outs = [o["name"] for o in card["outputs"]]
    known = [p["name"] for p in card["parameters"]]
    why = []
    if kpi not in outs:
        why.append(f"KPI '{kpi}' is not an output of this case (available: {', '.join(outs)})")
    bad = sorted({n for ps in param_sets for n in ps if n not in known})
    if bad:
        why.append(f"parameter(s) {', '.join(bad)} do not exist in this case (parameters: {', '.join(known)})")
    for kw in card.get("refuse_keywords") or []:
        if question and re.search(r"\b" + re.escape(str(kw).lower()), question.lower()):
            why.append(f"the question mentions '{kw}', which this case cannot answer")
            break
    if why:
        raise Refused("; ".join(why), card.get("cannot_answer") or [])


# ---- 2. units, types, hard bounds, defaults ---------------------------------------------------
_ALIAS = {"min": ("t", 1), "mins": ("t", 1), "minute": ("t", 1), "minutes": ("t", 1),
          "h": ("t", 60), "hr": ("t", 60), "hrs": ("t", 60), "hour": ("t", 60), "hours": ("t", 60),
          "d": ("t", 1440), "day": ("t", 1440), "days": ("t", 1440),
          "fraction": ("r", 1), "ratio": ("r", 1), "%": ("r", 0.01), "pct": ("r", 0.01), "percent": ("r", 0.01)}


def _clean(x):
    x = round(x, 10)
    return int(x) if x == int(x) else x


def _to_unit(name, v, given, card_unit):
    g, c = str(given).strip().lower(), str(card_unit).strip().lower()
    if g == c:
        return v
    if g in _ALIAS and c in _ALIAS and _ALIAS[g][0] == _ALIAS[c][0]:
        return _clean(v * _ALIAS[g][1] / _ALIAS[c][1])
    raise Fail("wrong_type", f"{name}: cannot convert unit '{given}' to '{card_unit}'",
               f"give {name} as a plain number in '{card_unit}' or as {{\"value\": x, \"unit\": u}} with u in min/h/day or %/fraction")


def _synonym(card, name, text):
    for phrase, mapping in (card.get("synonyms") or {}).items():
        if str(phrase).strip().lower() == text.strip().lower() and isinstance(mapping, dict) and name in mapping:
            return mapping[name]
    return text


def _describe(p):
    if "allowed" in p:
        return f"allowed values: {p['allowed']}"
    return p.get("hint") or f"give a number in {p.get('unit')} (plausible range {p.get('hard_min')}..{p.get('hard_max')})"


def _convert(card, p, v):
    name, unit = p["name"], p.get("unit")
    given_unit = None
    if isinstance(v, dict):
        if "value" not in v:
            raise Fail("wrong_type", f"{name}: object needs a 'value' field", 'use {"value": 8, "unit": "h"}')
        v, given_unit = v["value"], v.get("unit")
    if isinstance(v, str):
        v = _synonym(card, name, v)
    if "allowed" in p:
        for a in p["allowed"]:
            if v == a or (isinstance(v, str) and v.strip().lower() == str(a).lower()):
                return a
        raise Fail("wrong_type", f"{name} = {v!r} is not an allowed value", _describe(p))
    if not _num(v):
        raise Fail("wrong_type", f"{name} must be a number in {unit}, got {v!r}", _describe(p))
    if given_unit is not None:
        v = _to_unit(name, v, given_unit, unit)
    lo, hi = p.get("hard_min"), p.get("hard_max")
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise Fail("implausible_value", f"{name} = {v:g} {unit} is outside the plausible range [{lo}, {hi}]", _describe(p))
    return v


def resolve_params(card, given, units_on=True):
    """Return the complete parameter dict in case-card units: given values converted and checked
    (units_on) or taken as they are, missing ones filled from the card default (silently).
    A missing parameter without default raises missing_parameter."""
    out = {}
    for p in card["parameters"]:
        n = p["name"]
        if n in given:
            out[n] = _convert(card, p, given[n]) if units_on else raw(given[n])
        elif p.get("default") is not None:
            out[n] = p["default"]
        else:
            raise Fail("missing_parameter", f"parameter '{n}' is required (the case card has no default)", _describe(p))
    for n in given:  # unknown names only reach here when the scope check is off
        out.setdefault(n, raw(given[n]))
    return out


# ---- 3. validity ------------------------------------------------------------------------------
def check_validity(card, given, resolved, label=""):
    """Warnings (code, message) for values outside [valid_min, valid_max], and for explicitly
    given parameters marked `validated: false`."""
    warns = []
    for p in card["parameters"]:
        n, v = p["name"], resolved.get(p["name"])
        lo, hi = p.get("valid_min"), p.get("valid_max")
        if _num(v) and ((lo is not None and v < lo) or (hi is not None and v > hi)):
            rng = f"{'' if lo is None else lo}–{'' if hi is None else hi}"
            warns.append(("outside_valid_range", f"{label}{n} = {v:g} is outside the validated range {rng}: indicative only"))
        elif p.get("validated") is False and n in given:
            warns.append(("outside_valid_range", f"{label}{n} is not validated against the reference model: indicative only"))
    return warns
