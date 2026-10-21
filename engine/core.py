"""Engine: capabilities, knowledge_lookup, estimate, compare, raw_simulate (DESIGN.md sections 1-4)."""
import importlib.util
import inspect
import json
import re
from pathlib import Path

from . import checks as C, kb, stats as S
from .casecard import load_card
from .result import Capabilities, ErrorInfo, Lookup, RawRun, Refusal, Result, Warn

FLAGS = ("scope", "units", "validity", "adaptive_reps", "paired")
# paired off: scenario B uses replication indices cap+1 .. instead of 1.. (no overlap with A, at most cap extra runs)
_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def _sig(x):
    return float(f"{x:.6g}")  # 6 significant digits


def _mean_extras(runs):
    """Mean over replications of numeric `_extras` values (nested dicts per key); other values from replication 1."""
    def avg(vals):
        if all(isinstance(v, dict) for v in vals):
            return {k: avg([v[k] for v in vals if k in v]) for k in vals[0]}
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
            return _sig(sum(vals) / len(vals))
        return vals[0]
    ex = [r.get("_extras") or {} for r in runs]
    out = {k: avg([e[k] for e in ex if k in e]) for k in ex[0]} if ex else {}
    util = out.get("utilisation")
    if isinstance(util, dict) and util and all(isinstance(v, (int, float)) for v in util.values()):
        out["bottleneck"] = max(util, key=util.get)
    return out or None


class Engine:
    def __init__(self, cases_root, adapters=None, checks=None, rel_precision=0.01, batch=10, replications_when_off=1):
        unknown = set(checks or {}) - set(FLAGS)
        if unknown:
            raise ValueError(f"unknown check flag(s) {sorted(unknown)}; valid: {FLAGS}")
        self.root, self.adapters = Path(cases_root), dict(adapters or {})
        self.flags = {f: True for f in FLAGS} | dict(checks or {})
        self.rel, self.batch, self.n_off = rel_precision, batch, replications_when_off
        self._cards, self._cache = {}, {}

    # ---- loading --------------------------------------------------------------------------
    def _card(self, case_id):
        if case_id not in self._cards:
            path = self.root / str(case_id) / "case_card.yaml"
            if not _ID.match(str(case_id)) or not path.is_file():
                raise C.Fail("unknown_case", f"unknown case '{case_id}'", "cases: " + ", ".join(sorted(p.parent.name for p in self.root.glob("*/case_card.yaml"))))
            self._cards[case_id] = load_card(path)
        return self._cards[case_id]

    def _adapter(self, case_id):
        if case_id not in self.adapters:
            path = self.root / case_id / "adapter.py"
            if not path.is_file():
                raise C.Fail("simulator_failed", f"case '{case_id}' has no adapter.py", "add cases/<case_id>/adapter.py (DESIGN.md section 4)")
            try:
                spec = importlib.util.spec_from_file_location(f"_adapter_{case_id}", path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                self.adapters[case_id] = mod.Adapter()
            except Exception as e:
                raise C.Fail("simulator_failed", f"adapter of '{case_id}' could not be loaded: {type(e).__name__}: {e}") from e
        return self.adapters[case_id]

    # ---- running (cached per case + frozen params + start index) ---------------------------------
    def _getter(self, case_id, adapter, params, start=1):
        key = (case_id, json.dumps(params, sort_keys=True, default=str), start)

        has_start = "start" in inspect.signature(adapter.run).parameters

        def get(n):
            have = self._cache.get(key, [])
            if len(have) < n:
                try:
                    if has_start:  # run only the missing replications start+len(have) ..
                        runs = have + list(adapter.run(dict(params), n - len(have), start=start + len(have)))
                    elif start == 1:
                        runs = adapter.run(dict(params), n)
                    else:  # slow fallback: run the first start-1+n replications and drop the first start-1
                        runs = adapter.run(dict(params), start - 1 + n)[start - 1:]
                except Exception as e:
                    msg = f"{type(e).__name__}: {e}"
                    hint = "this scenario is not part of the simulation model" if isinstance(e, NotImplementedError) else "the simulator adapter failed; check the adapter log"
                    raise C.Fail("simulator_failed", msg, hint) from e
                if len(runs) < n:
                    raise C.Fail("simulator_failed", f"adapter returned {len(runs)} of {n} replications", None)
                self._cache[key] = runs
            return self._cache[key][:n]
        return get

    def _safe(self, model, tool, case_id, fn, **base):
        """Run fn(); turn Refused / Fail into a result dict. Always returns a plain dict valid for `model`."""
        try:
            res = fn()
        except C.Refused as r:
            res = Result(status="refused", tool=tool, case_id=case_id, refusal=Refusal(reason=r.reason, cannot_answer=r.cannot_answer), **base)
        except C.Fail as f:
            res = model(status="error", tool=tool, case_id=case_id, error=ErrorInfo(code=f.code, message=f.message, hint=f.hint), **base)
        return res.model_dump(mode="json")

    def _prepare(self, case_id, kpi, scenarios, question, labels):
        """Checks 1-3 for one or two scenarios. Returns (card, resolved params list, warnings)."""
        card = self._card(case_id)
        scenarios = [dict(s or {}) for s in scenarios]
        if self.flags["scope"]:
            C.check_scope(card, kpi, scenarios, question)
        resolved, warns = [], []
        for given, label in zip(scenarios, labels):
            r = C.resolve_params(card, given, self.flags["units"])
            resolved.append(r)
            if self.flags["validity"]:
                warns += C.check_validity(card, given, r, label)
        return card, resolved, warns

    def _precision(self, card, kpi):
        out = next((o for o in card["outputs"] if o["name"] == kpi), {})
        rep = card["replications"]
        return out.get("unit"), out.get("abs_precision"), rep["ours_min"], rep.get("max", 100)

    # ---- tools ---------------------------------------------------------------------------------
    def capabilities(self, case_id):
        def go():
            c = self._card(case_id)
            keep = lambda d, ks: {k: d[k] for k in ks if k in d}
            return Capabilities(
                status="ok", tool="capabilities", case_id=case_id,
                parameters=[keep(p, ("name", "unit", "default", "valid_min", "valid_max", "hard_min", "hard_max", "allowed", "validated", "meaning", "hint")) for p in c["parameters"]],
                outputs=[keep(o, ("name", "unit", "meaning", "abs_precision")) for o in c["outputs"]],
                can_answer=c.get("can_answer") or [], cannot_answer=c.get("cannot_answer") or [],
                published_scenarios=c.get("published_scenarios") or [], replications=c["replications"])
        return self._safe(Capabilities, "capabilities", case_id, go)

    def knowledge_lookup(self, query, case_id=None):
        def go():
            card = self._card(case_id) if case_id else None
            return Lookup(status="ok", tool="knowledge_lookup", case_id=case_id, query=query, results=kb.lookup(query, card))
        return self._safe(Lookup, "knowledge_lookup", case_id, go, query=query)

    def estimate(self, case_id, kpi, params=None, question=None, event_log=False):
        def go():
            card, (p,), warns = self._prepare(case_id, kpi, [params], question, [""])
            unit, abs_prec, n_min, cap = self._precision(card, kpi)
            adapter = self._adapter(case_id)
            get = self._getter(case_id, adapter, p)
            try:
                if self.flags["adaptive_reps"]:
                    vals, m, h, ok = S.adaptive(get, kpi, n_min, cap, self.rel, abs_prec, self.batch)
                    if not ok:
                        warns.append(("precision_not_reached", f"95% CI half-width {h:.3g} is still above {self.rel:.1%} of the mean after {len(vals)} replications (cap {cap}): treat the mean as rough"))
                    ci_ = [_sig(m - h), _sig(m + h)]
                else:
                    vals = [r[kpi] for r in get(self.n_off)]
                    m, h, ok, ci_ = sum(vals) / len(vals), None, None, None
            except KeyError as e:
                raise C.Fail("simulator_failed", f"adapter result has no KPI {e}", "check the KPI name in the case card against the adapter") from e
            path = None
            if event_log and getattr(adapter, "supports_event_log", False):
                path = (adapter.run(dict(p), 1, event_log=True)[0]).get("_event_log")
            return Result(status="ok", tool="estimate", case_id=case_id, kpi=kpi, unit=unit, params=p, mean=_sig(m), ci95=ci_,
                          ci95_half_width=None if h is None else _sig(h), replications=len(vals), precision_reached=ok,
                          warnings=[Warn(code=c, message=t) for c, t in warns], extras=_mean_extras(get(len(vals))),
                          event_log=path, checks=self.flags)
        return self._safe(Result, "estimate", case_id, go, kpi=kpi, params=params, checks=self.flags)

    def compare(self, case_id, kpi, params_a=None, params_b=None, question=None):
        def go():
            card, (pa, pb), warns = self._prepare(case_id, kpi, [params_a, params_b], question, ["A: ", "B: "])
            unit, abs_prec, n_min, cap = self._precision(card, kpi)
            adapter = self._adapter(case_id)
            get_a = self._getter(case_id, adapter, pa)
            get_b = self._getter(case_id, adapter, pb, 1 if self.flags["paired"] else 1 + cap)
            try:
                if self.flags["adaptive_reps"]:
                    d, m, h, sep = S.paired(get_a, get_b, kpi, n_min, cap, self.batch)
                    ci_, hw = [_sig(m - h), _sig(m + h)], _sig(h)
                else:  # no CI: naive sign of the difference of the means
                    d = [b[kpi] - a[kpi] for a, b in zip(get_a(self.n_off), get_b(self.n_off))]
                    m, ci_, hw = sum(d) / len(d), None, None
                    sep = m != 0
            except KeyError as e:
                raise C.Fail("simulator_failed", f"adapter result has no KPI {e}", "check the KPI name in the case card against the adapter") from e
            verdict = ("b_higher" if m > 0 else "b_lower") if sep else "not_distinguishable"
            if not sep:
                warns.append(("not_distinguishable", f"the difference B - A is not distinguishable from 0 after {len(d)} replications: do not name a winner"))
            return Result(status="ok", tool="compare", case_id=case_id, kpi=kpi, unit=unit, params_a=pa, params_b=pb, mean=None,
                          difference_b_minus_a=_sig(m), ci95=ci_, ci95_half_width=hw, verdict=verdict, replications=len(d),
                          precision_reached=sep if self.flags["adaptive_reps"] else None,
                          warnings=[Warn(code=c, message=t) for c, t in warns], checks=self.flags)
        return self._safe(Result, "compare", case_id, go, kpi=kpi, params_a=params_a, params_b=params_b, checks=self.flags)

    def raw_simulate(self, case_id, params=None, replications=1):
        """No checks at all: card defaults fill missing parameters, everything else goes to the adapter as given.
        Returns the per-replication KPI values (1 <= replications <= 1000)."""
        def go():
            card = self._card(case_id)
            p = {q["name"]: q["default"] for q in card["parameters"] if q.get("default") is not None}
            p.update({k: C.raw(v) for k, v in (params or {}).items()})
            n, adapter = max(1, min(int(replications), 1000)), self._adapter(case_id)
            try:
                runs = adapter.run(dict(p), n)
            except Exception as e:
                raise C.Fail("simulator_failed", f"{type(e).__name__}: {e}") from e
            return RawRun(status="ok", tool="raw_simulate", case_id=case_id, params=p,
                          runs=[{k: v for k, v in r.items() if not k.startswith("_")} for r in runs])
        return self._safe(RawRun, "raw_simulate", case_id, go)
