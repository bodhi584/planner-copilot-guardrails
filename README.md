# Planner Copilot

[![CI](https://github.com/bodhi584/planner-copilot-guardrails/actions/workflows/ci.yml/badge.svg)](https://github.com/bodhi584/planner-copilot-guardrails/actions/workflows/ci.yml)

**Checked answers to production-planning questions, from validated simulation models, driven by a small local language model.**

A planner asks in plain language: *“Busy week with 20 % more orders and only 2 workers: how many hours after the Friday shift?”* A language model on the company’s own computer turns the question into a simulation scenario. A guardrail engine written in code decides whether the answer can be trusted: it checks the inputs against what the published model was validated for, runs enough replications for a 95 % confidence interval, and returns one of three outcomes:

| Outcome | When | Example (sheet-metal job shop) |
|---|---|---|
| **Answer** | inside the validated range | normal week: 3.37 h overtime, 95 % CI [3.24, 3.50] (published model: 3.31 h) |
| **Answer + warning** | the model has the mechanism, but the input is outside the validated range | 2 workers, +20 % orders: ≈ 38 h, `outside_valid_range`, indicative only |
| **Refusal** | the question is outside the model | “What will the overtime cost in euros?” → refused: the model has no cost data |

![Demo](docs/img/demo.png)

## Why

A simulation model answers *what if* questions about a factory, but running it correctly takes an expert: valid inputs, enough replications, a confidence interval, a fair comparison. A language model alone produces plausible text, not calculated results, and cannot reliably check its own steps. Planner Copilot keeps the language model for what it is good at (understanding the question, choosing a tool) and moves everything that decides correctness into code. This is the *LLM-Modulo* principle: the model proposes, external code verifies (Kambhampati et al. 2024).

## Architecture

![Architecture](docs/img/architecture.png)

| Part | What it is | Where |
|---|---|---|
| **Case card** | One YAML file per simulation model: parameters with units, hard bounds and validated ranges; outputs with required precision; what the model cannot answer. The simulation expert’s knowledge, written down. | `cases/*/case_card.yaml` |
| **Check engine** | The same code for every model. Five checks on every simulation call, adaptive replications, confidence intervals, paired comparisons, fixed warning and refusal codes. | [`engine/`](engine/) · [design](engine/DESIGN.md) |
| **Workflow** | A fixed LangGraph loop. The model answers each turn with one JSON action (tool call or final answer); code runs the tool, copies warning codes into the answer, and stops after at most 6 tool calls. | [`agent/`](agent/) |

The five checks, in order:

| # | Check | If it fails |
|---|---|---|
| 1 | **Scope**: output and parameter names exist; no refusal keyword from the case card in the question | refused |
| 2 | **Units and plausibility**: numeric, converted (min ↔ h, % ↔ fraction), within hard physical bounds | error with a hint, the model may correct itself |
| 3 | **Validated range** of the published model | runs, warning `outside_valid_range` |
| 4 | **Adaptive replications**: add 10 at a time until the 95 % CI half-width ≤ 1 % of the mean (or the output’s absolute precision), cap 100 | warning `precision_not_reached` |
| 5 | **Paired comparison** with common random numbers, until the CI of the difference excludes 0 | verdict `not_distinguishable` |

In addition, the workflow checks that the number in the final answer is one the simulation returned (`value_not_from_tool` otherwise). The engine is also available as an MCP server, so any MCP-capable application can use the checked tools.

## Results

### Held-out test (40 sealed questions, rules frozen)

The rules were frozen and the [protocol](eval/PROTOCOL.md) written before 40 new questions (10 per case, other KPIs, scenarios or wordings than in development) were generated and hashed. Three local models, three setups, temperature 0, one RTX 3060:

![Test results](docs/img/results_test.png)

| Model | A · no checks | B · rules in the prompt | C · guardrail engine |
|---|---|---|---|
| Qwen 2.5 7B | 16 / 9 / 15 | 22 / 11 / 7 | **37 / 0 / 3** |
| Gemma 2 9B | 14 / 9 / 17 | 15 / 13 / 12 | **30 / 2 / 8** |
| Llama 3.1 8B | 13 / 6 / 21 | 14 / 12 / 14 | **27 / 2 / 11** |

*correct / cautious / confidently wrong, of 40. Answers, graded files and statistics: [`eval/results/test/`](eval/results/test/summary.md).*

- **More correct answers with code checks than with the same rules in the prompt, for every model** (paired exact McNemar test, Holm-adjusted p = 0.0004 / 0.0007 / 0.0022). Qwen reaches 92 % correct, the proposal's ≥ 90 % target.
- **Fewer confidently wrong answers for every model (7→3, 12→8, 14→11), but not significant with 40 questions** (p = 0.17–0.27). The ≤ 2 % target is not met (Qwen: 8 %).
- The gain sits where a rule is a computation: validity warnings 2/21 → 20/21, numeric answers 27/48 → 43/48 (summed over models). Out-of-scope questions do not improve (18/27 → 16/27): the keyword-based scope check misses rephrased questions.
- Stable under sampling: Qwen at temperature 0.7, three seeds, setup C: 35, 37, 35 correct.

### Development runs (80 questions)

| Model | A · no checks | B · rules in the prompt | C · guardrail engine |
|---|---|---|---|
| Qwen 2.5 7B | 43 / 9 / 28 | 63 / 7 / 10 | **76 / 2 / 2** |
| Gemma 2 9B | 25 / 19 / 36 | 33 / 30 / 17 | **71 / 5 / 4** |
| Llama 3.1 8B | 27 / 13 / 40 | 42 / 24 / 14 | **63 / 10 / 7** |

Two rules were adjusted on these questions ([`eval/rule_changes.md`](eval/rule_changes.md)), so they are not a test; they show where the rules came from. Rerunning Llama on them with the frozen rules gives 64 / 8 / 8 in C.

Paper: [`paper/planner_copilot.pdf`](paper/planner_copilot.pdf) (IEEE conference format).

## Simulation models

Each model is published by its authors with results; each is reproduced here before any question is asked, so later differences cannot be a setup mistake.

| Case | Industry | Model | Reproduction |
|---|---|---|---|
| [A1](cases/A1_smt2020/) | semiconductor fab (SMT2020) | Python simulator, Tassel et al. 2023 | 28 of 28 published values within tolerance |
| [A2](cases/A2_sme/) | sheet-metal job shop (SME, 69 real orders) | JaamSim, Jurczyk-Bunkowska 2026 | identical to the 30 published replications |
| [A3](cases/A3_warehouse/) | pallet warehouse with reach trucks | SimPy, Saengphueng 2026 | 360 of 360 published KPI means identical |
| [A5](cases/A5_operator_line/) | operator-paced assembly line | SimPy rebuild of Seppanen 2005 | inside the published 95 % CIs with 100 replications; 3 and 4 operators at the upper edge |

The reproductions of A1, A2 and A3 run in CI on every push.

## Quick start

```bash
git clone https://github.com/bodhi584/planner-copilot-guardrails
cd planner-copilot-guardrails
pip install ".[all]"
python -m pytest -q                         # engine and workflow tests

bash cases/A2_sme/setup.sh                  # builds JaamSim (Java 17+, about 30 s)
python -m app.demo                          # web demo at http://127.0.0.1:7860
```

The **Scenario** tab needs no language model. For the **Ask** tab, run any OpenAI-compatible model server, for example:

```bash
ollama pull qwen2.5:7b-instruct
LLM_MODEL=qwen2.5:7b-instruct LLM_BASE_URL=http://localhost:11434/v1 python -m app.demo
```

Python API without a language model:

```python
from engine import Engine
e = Engine("cases")
e.estimate("A2_sme", "overtime_after_shift", {"workers": 2, "portfolio": "busy week"})
e.compare("A3_warehouse", "pallets_per_day", {"reach_trucks": 9}, {"reach_trucks": 12})
```

Run the evaluation: see [`eval/`](eval/).

## Design decisions

- **Existing, validated models instead of generated ones.** Validation is the expensive expert work; the system reuses it and only lets the model operate within it.
- **Local open-source models.** Production data stays in-house, and a fixed model version behaves the same tomorrow. Any OpenAI-compatible server works (Ollama, llama.cpp, vLLM).
- **One JSON action per turn instead of native tool calling.** Small models follow it more reliably, and the same prompt works on every backend.
- **Common random numbers.** Replication *i* always uses random stream *i*, so two scenarios differ only by their inputs and a comparison needs far fewer replications.
- **Fixed warning codes, copied by code.** The model cannot add or drop a warning; graders and interfaces read the same codes.
- **Every check can be switched off.** The ablation measures what each check contributes (`--off scope,validity,...`).

## Limitations

- Scope refusal is keyword-based: an out-of-scope question phrased without a listed keyword can pass. In the test this is the largest source of confidently wrong answers in setup C.
- The value check confirms that a number came from the simulator, not that its unit matches the question (units per hour answered with units per shift).
- The guardrail is only as good as the case card; where a validated range is an assumption (A2: the fourth worker), the card says so.
- A1 answers come from stored runs of the four published scenarios; other A1 scenarios would need the 30–45 min simulator runs.
- 40 test questions are too few to show a significant drop in confidently wrong answers; the test questions were written by the system's author (after the freeze, by script, hashed).

## Repository

```
engine/      check engine, MCP server, tests
agent/       LangGraph workflow, model client, prompt rules for setup B, tests
cases/       one folder per simulation model: case card, adapter, reproduction, questions
eval/        experiment runner, grader, test protocol, rule-change log, development runs 1–6 and test runs
paper/       IEEE-format report (LaTeX source, figures, PDF)
app/         Gradio web demo
```

## References

- Kambhampati, S. et al. (2024). Position: LLMs can’t plan, but can help planning in LLM-Modulo frameworks. *Proc. ICML*, PMLR 235.
- Sargent, R. G. (2015). An introductory tutorial on verification and validation of simulation models. *Proc. Winter Simulation Conference*, 1729–1740.
- Model sources: see each case folder and [THIRD_PARTY.md](THIRD_PARTY.md).

## License

Code: MIT, © 2026 Yu Han. Third-party models and data keep their own licences, listed in [THIRD_PARTY.md](THIRD_PARTY.md).
