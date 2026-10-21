# Workflow

A fixed LangGraph loop (`flow.py`): the model answers every turn with one JSON object, either a tool call or the final answer. Code runs the tool, feeds the result back and stops at the final answer, after at most 6 tool calls, or after 2 invalid replies.

| File | What |
|---|---|
| `flow.py` | `answer(question, case_id, setup, llm)` → `{value, choice, refused, flags, text, tools, seconds}` |
| `tools.py` | tool sets per setup: **A** `raw_simulate` · **B** `raw_simulate` + rules in the prompt · **C** `capabilities`, `knowledge_lookup`, `estimate`, `compare` |
| `make_prompt_rules.py` → `prompt_rules.md` | setup B: the rules the engine checks, generated from the case cards as plain text |
| `llm.py` | any OpenAI-compatible endpoint (Ollama, llama.cpp server, vLLM); temperature 0 |
| `tests/test_flow.py` | workflow tests with a scripted model |

What code does in setup C, not the model:
- the planner has chosen the factory, so the case is fixed; the user's question is passed to the engine for the scope check;
- the answer's warning codes are copied from the engine results (the model cannot add or drop them);
- an engine refusal without a number marks the answer refused;
- the number in the answer must be one the tools returned (allowing rounding and h/min or fraction/percent conversion); otherwise the answer gets the code `value_not_from_tool`.

The last check was added after the experiments in `eval/results/` and is switched on by default (`check_value=True`).
