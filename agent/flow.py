"""Orchestration: a fixed LangGraph loop  llm -> (tool -> llm)* -> finish.

The model answers every turn with ONE JSON object: a tool call or the final answer. Small open models follow this
more reliably than native tool calling, and the same prompt works for every OpenAI-compatible backend.
What code does, not the model (condition C): passes the case and the user's question to the engine, copies the
engine's warning codes into the answer, and marks the answer refused when the engine refused and no number was given.

    from agent.flow import answer
    out = answer("Only 4 reach trucks tomorrow: waiting time?", case_id="A3_warehouse", arm="C", llm=LLM("qwen2.5:7b"), cases_root="cases")
    out -> {"value": 104.8, "choice": "", "refused": False, "flags": ["outside_valid_range"], "text": "...", "tools": [...], "seconds": 12.3}
"""
import json
import re
import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .tools import TOOL_DOCS, Toolbox, compact

MAX_TOOL_CALLS = 6
MAX_BAD_REPLIES = 2


class State(TypedDict, total=False):
    messages: list
    tool_calls: int
    bad: int
    pending: dict
    final: dict
    tools: list
    engine_codes: list
    refused_by_engine: bool
    tool_numbers: list
    llm_seconds: float


def system_prompt(box: Toolbox, rules: str | None):
    c = box.card()
    params = "\n".join(f"- {p['name']} [{p.get('unit') or '-'}], default {p.get('default')}"
                       + (f", allowed {', '.join(map(str, p['allowed']))}" if p.get("allowed") else "")
                       + (f": {p['meaning']}" if p.get("meaning") else "") for p in c["parameters"])
    kpis = "\n".join(f"- {o['name']} [{o.get('unit') or '-'}]: {o.get('meaning', '')}" for o in c["outputs"])
    tools = "\n".join(f"- {TOOL_DOCS[n]}" for n in box.names)
    s = f"""You are Planner Copilot. A production planner asks about their factory, which has a validated simulation model.
Case: {c['case_id']} ({c.get('industry', '')}).
Every number you report must come from a tool result in this conversation. Never guess a number.

Model parameters:
{params}

KPIs the model reports:
{kpis}

Tools:
{tools}

Reply in EVERY turn with exactly one JSON object and nothing else:
  {{"action": "tool", "tool": "<tool name>", "args": {{...}}}}
or, when you are done:
  {{"action": "final", "value": <number or null>, "choice": "<option or empty>", "refused": <true|false>, "warnings": [<warning codes>], "text": "<short answer for the planner>"}}
Final answer rules: value = the one number that answers the question, in the unit the question asks for (null if none).
choice = only when the question says to put an option in choice. refused = true when the question cannot be answered with this model (then value null).
warnings = the warning codes that apply to your answer."""
    if box.arm == "C":
        s += "\nCopy warning codes from the tool results into warnings unchanged; if a tool refuses, set refused to true."
    if rules:
        s += "\n\nRules you must follow:\n" + rules
    return s


def _parse(text):
    """First JSON object in the reply (models sometimes wrap it in prose or code fences)."""
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            depth += text[i] == "{"
            depth -= text[i] == "}"
            if depth == 0:
                try:
                    obj = json.loads(text[start:i + 1])
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    pass
                break
        start = text.find("{", start + 1)
    return None


def _normalise(obj, tool_names):
    """Accept common near-misses of small models: {"action": "<tool name>", ...} or a tool call / final answer
    without "action". Only the shape is repaired, never the content."""
    if not isinstance(obj, dict):
        return None
    a = obj.get("action")
    if a in ("tool", "final"):
        return obj
    if a in tool_names or obj.get("tool") in tool_names:
        return {"action": "tool", "tool": obj.get("tool") or a, "args": obj.get("args") or obj.get("arguments") or {}}
    if any(k in obj for k in ("value", "refused", "text", "choice")):
        return dict(obj, action="final")
    return obj


def _num(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(str(v).replace(",", "").strip().rstrip("%"))
    except ValueError:
        return None


def _numbers(obj, out, depth=0):
    """Every number in a tool result (means, CI bounds, differences, per-run values, extras)."""
    if depth > 6 or len(out) > 2000:
        return out
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numbers(v, out, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numbers(v, out, depth + 1)
    return out


def value_from_tool(value, numbers, rel=0.01, abs_tol=0.05):
    """True if the answer's number matches a number the tools returned: same value after rounding,
    or the same value converted between h/min or fraction/percent."""
    for x in numbers:
        for y in (x, x * 60, x / 60, x * 100, x / 100):
            if abs(value - y) <= max(rel * abs(y), abs_tol):
                return True
    return False


def build(box: Toolbox, llm, rules=None):
    def llm_node(st: State):
        reply, sec = llm(st["messages"])
        msgs = st["messages"] + [{"role": "assistant", "content": reply}]
        obj = _normalise(_parse(reply), box.names)
        upd = {"messages": msgs, "llm_seconds": st.get("llm_seconds", 0.0) + sec, "pending": None}
        if not obj or obj.get("action") not in ("tool", "final"):
            bad = st.get("bad", 0) + 1
            upd["bad"] = bad
            if bad > MAX_BAD_REPLIES:
                upd["final"] = {"value": None, "choice": "", "refused": True, "warnings": [], "text": "(no valid reply)"}
            else:
                upd["messages"] = msgs + [{"role": "user", "content": 'Invalid reply. Answer with exactly one JSON object: '
                                           '{"action": "tool", ...} or {"action": "final", ...}.'}]
            return upd
        if obj["action"] == "final" or st.get("tool_calls", 0) >= MAX_TOOL_CALLS:
            upd["final"] = obj if obj["action"] == "final" else {"value": None, "refused": True, "text": "(tool-call limit reached)"}
        else:
            upd["pending"] = obj
        return upd

    def tool_node(st: State):
        call = st["pending"]
        name, args = str(call.get("tool", "")), call.get("args") or {}
        res, codes, refused = box.call(name, args)
        name = getattr(box, "last_tool", name)
        log = st.get("tools", []) + [{"tool": name, "args": args, "status": res.get("status"), "warnings": codes}]
        return {"messages": st["messages"] + [{"role": "user", "content": f"Tool result ({name}): {compact(res)}"}],
                "tool_calls": st.get("tool_calls", 0) + 1, "tools": log,
                "engine_codes": sorted(set(st.get("engine_codes", [])) | set(codes)),
                "refused_by_engine": st.get("refused_by_engine", False) or refused, "pending": None,
                "tool_numbers": _numbers(res, list(st.get("tool_numbers", [])))}

    g = StateGraph(State)
    g.add_node("llm", llm_node)
    g.add_node("tool", tool_node)
    g.set_entry_point("llm")
    g.add_conditional_edges("llm", lambda st: "end" if st.get("final") else ("tool" if st.get("pending") else "llm"),
                            {"end": END, "tool": "tool", "llm": "llm"})
    g.add_edge("tool", "llm")
    return g.compile()


def answer(question, case_id, arm, llm, cases_root="cases", rules_path=None, check_value=True) -> dict[str, Any]:
    t0 = time.time()
    box = Toolbox(cases_root, arm, case_id, question)
    rules = None
    if arm == "B":
        from .make_prompt_rules import section
        rules = section(case_id, rules_path)
    graph = build(box, llm, rules)
    st = graph.invoke({"messages": [{"role": "system", "content": system_prompt(box, rules)}, {"role": "user", "content": question}],
                       "tool_calls": 0, "bad": 0, "tools": [], "engine_codes": [], "refused_by_engine": False, "llm_seconds": 0.0, "tool_numbers": []},
                      {"recursion_limit": 4 * MAX_TOOL_CALLS + 8})
    f = st.get("final") or {}
    value = _num(f.get("value"))
    # an answer with a number is not a refusal, whatever the model writes in "refused"
    refused = value is None and (bool(f.get("refused")) or (arm == "C" and bool(st.get("refused_by_engine"))))
    flags = st.get("engine_codes", []) if arm == "C" else [str(w) for w in (f.get("warnings") or []) if w]
    # value check (setup C): the number in the answer must be one the tools returned, not one the model made up
    if arm == "C" and value is not None and check_value and not value_from_tool(value, st.get("tool_numbers", [])):
        flags = sorted(set(flags) | {"value_not_from_tool"})
    return {"value": value, "choice": str(f.get("choice") or "").strip(), "refused": refused, "flags": flags,
            "text": str(f.get("text") or ""), "tools": st.get("tools", []), "llm_seconds": round(st.get("llm_seconds", 0.0), 2),
            "seconds": round(time.time() - t0, 2)}
