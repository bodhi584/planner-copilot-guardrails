"""Planner Copilot web demo (Gradio).

Two tabs:
  * Scenario: pick a factory and its inputs, the guardrail engine runs the checked simulation. No language model needed.
  * Ask: type a planning question in plain language; a local model (any OpenAI-compatible endpoint, e.g. Ollama)
    drives the engine through the guarded workflow.

    python -m app.demo                      # http://127.0.0.1:7860
    LLM_MODEL=qwen2.5:7b-instruct LLM_BASE_URL=http://localhost:11434/v1 python -m app.demo
"""
import json
import os
from pathlib import Path

import gradio as gr

from engine import Engine

ROOT = Path(__file__).resolve().parents[1]
CASES = Path(os.environ.get("PC_CASES", ROOT / "cases"))
os.environ.setdefault("A1_CACHE_ONLY", "1")  # the fab simulator takes 30-45 min per run; answer from stored runs

ENGINE = Engine(str(CASES))
CASE_IDS = sorted(p.parent.name for p in CASES.glob("*/case_card.yaml"))


def _card(case_id):
    return ENGINE._card(case_id)


def _label(case_id):
    return f"{case_id} · {_card(case_id).get('industry', '')}"


WARN_TEXT = {
    "outside_valid_range": "Outside the validated range of the model: indicative only.",
    "precision_not_reached": "The replication cap was reached before the required precision.",
    "not_distinguishable": "The two scenarios cannot be told apart at this sample size.",
    "value_not_from_tool": "The number in the answer was not returned by the simulation.",
}


def _fmt(x):
    return "–" if x is None else f"{x:,.0f}" if abs(x) >= 1000 else f"{x:.3g}"


def render_result(r):
    if r.get("status") == "refused":
        ref = r.get("refusal") or {}
        lines = [f"### Refused\n{ref.get('reason', '')}"]
        if ref.get("cannot_answer"):
            lines.append("This model cannot answer: " + "; ".join(ref["cannot_answer"]))
        return "\n\n".join(lines)
    if r.get("status") == "error":
        e = r.get("error") or {}
        head = "Simulator not available" if e.get("code") == "simulator_failed" else "Input not accepted"
        return f"### {head}\n{e.get('message', '')}\n\n*Hint:* {e.get('hint', '')}"
    unit = r.get("unit") or ""
    if r.get("difference_b_minus_a") is not None:
        lo, hi = r.get("ci95") or (None, None)
        head = (f"### Difference B − A: {_fmt(r['difference_b_minus_a'])} {unit}\n"
                f"95 % CI [{_fmt(lo)}, {_fmt(hi)}] · verdict **{r.get('verdict')}** · {r.get('replications')} paired replications")
    else:
        lo, hi = r.get("ci95") or (None, None)
        head = (f"### {r.get('kpi')}: {_fmt(r.get('mean'))} {unit}\n"
                f"95 % CI [{_fmt(lo)}, {_fmt(hi)}] · {r.get('replications')} replications")
    warns = [f"⚠ **{w['code']}**: {w.get('message') or WARN_TEXT.get(w['code'], '')}" for w in r.get("warnings") or []]
    return "\n\n".join([head] + warns)


def scenario_inputs(case_id):
    c = _card(case_id)
    rows = []
    for p in c["parameters"]:
        rng = ""
        if p.get("allowed"):
            rng = "options: " + ", ".join(map(str, p["allowed"]))
        elif p.get("valid_min") is not None:
            rng = f"validated {p['valid_min']}–{p['valid_max']}"
        rows.append([p["name"], str(p.get("default")), p.get("unit") or "-", rng])
    kpis = [o["name"] for o in c["outputs"]]
    cannot = "**This model cannot answer:**\n" + "\n".join(f"- {x}" for x in c.get("cannot_answer", []))
    return gr.update(value=rows), gr.update(choices=kpis, value=kpis[0]), cannot


def _params(table):
    out = {}
    for row in table.values.tolist() if hasattr(table, "values") else table:
        name, val = row[0], row[1]
        if name in (None, "") or val in (None, ""):
            continue
        try:
            out[name] = float(val) if "." in str(val) else int(val)
        except ValueError:
            out[name] = str(val)
    return out


PRESETS = {  # one example per case that shows a warning (input outside the validated range)
    "A2_sme": ("Busy week (+20 % orders) with only 2 workers", "overtime_after_shift", {"workers": 2, "portfolio": "over20"}),
    "A3_warehouse": ("15 reach trucks (validated: 6-12)", "pallets_per_day", {"reach_trucks": 15}),
    "A5_operator_line": ("5 operators (validated: 2-4)", "units_per_shift", {"operators": 5}),
}


def run_preset(case_id):
    if case_id not in PRESETS:
        return "No example for this factory.", "", gr.update(), gr.update()
    _, kpi, params = PRESETS[case_id]
    table, _, _ = scenario_inputs(case_id)
    rows = [[r[0], str(params.get(r[0], r[1])), r[2], r[3]] for r in table["value"]]
    r = ENGINE.estimate(case_id, kpi, params)
    return render_result(r), json.dumps(r, indent=1, default=str), gr.update(value=rows), gr.update(value=kpi)


def run_scenario(case_id, kpi, table):
    r = ENGINE.estimate(case_id, kpi, _params(table))
    return render_result(r), json.dumps(r, indent=1, default=str)


def ask(case_id, question):
    from agent.flow import answer
    from agent.llm import LLM
    model = os.environ.get("LLM_MODEL", "qwen2.5:7b-instruct")
    base = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
    try:
        out = answer(question, case_id, "C", LLM(model, base_url=base), cases_root=str(CASES))
    except Exception as e:  # no model server running, wrong model name, ...
        return (f"### No language model reachable\nStart one, e.g. `ollama serve` and `ollama pull {model}`, "
                f"or set LLM_BASE_URL / LLM_MODEL.\n\n`{type(e).__name__}: {e}`"), ""
    if out["refused"]:
        md = f"### Refused\n{out['text']}"
    else:
        v = out["value"] if out["value"] is not None else out["choice"]
        md = f"### {v}\n{out['text']}"
    md += "".join(f"\n\n⚠ **{c}**: {WARN_TEXT.get(c, '')}" for c in out["flags"])
    trace = "\n".join(f"{i + 1}. `{t['tool']}` {json.dumps(t['args'])} → {t['status']}" for i, t in enumerate(out["tools"]))
    return md, trace or "(no tool calls)"


def build():
    with gr.Blocks(title="Planner Copilot") as demo:
        gr.Markdown("## Planner Copilot\nChecked answers from validated simulation models: an answer with a 95 % "
                    "confidence interval, an answer with a warning, or a refusal.")
        case = gr.Dropdown([(_label(c), c) for c in CASE_IDS], value="A2_sme" if "A2_sme" in CASE_IDS else CASE_IDS[0],
                           label="Factory")
        with gr.Tab("Scenario (no model needed)"):
            with gr.Row():
                with gr.Column(scale=3):
                    table = gr.Dataframe(headers=["parameter", "value", "unit", "range"], interactive=True, label="Inputs")
                    kpi = gr.Dropdown(label="Output")
                    go = gr.Button("Run checked simulation", variant="primary")
                    ex = gr.Button("Example: input outside the validated range")
                    cannot = gr.Markdown()
                with gr.Column(scale=4):
                    res = gr.Markdown()
                    raw = gr.Code(label="Engine result (JSON)", language="json")
            go.click(run_scenario, [case, kpi, table], [res, raw])
            ex.click(run_preset, case, [res, raw, table, kpi])
        with gr.Tab("Ask in plain language (local model)"):
            q = gr.Textbox(label="Question", lines=3,
                           value="Busy week with 20 % more orders and only 2 workers: how many hours after the Friday shift?")
            b = gr.Button("Ask", variant="primary")
            a = gr.Markdown()
            tr = gr.Markdown(label="Tool calls")
            b.click(ask, [case, q], [a, tr])
        case.change(scenario_inputs, case, [table, kpi, cannot])
        demo.load(scenario_inputs, case, [table, kpi, cannot])
    return demo


if __name__ == "__main__":
    build().launch(server_name=os.environ.get("HOST", "127.0.0.1"), server_port=int(os.environ.get("PORT", 7860)))
