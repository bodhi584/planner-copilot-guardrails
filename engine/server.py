"""MCP server (stdio). Usage: python -m engine.server --cases cases [--raw] [--off scope,validity,...]
Needs mcp >= 2: the server class is `MCPServer` (FastMCP of v1 was renamed)."""
import argparse
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .core import Engine
from .result import Capabilities, Lookup, RawRun, Result


def _out(d, model):
    """status == error -> MCP tool execution error (isError true) with message + hint; refusals are normal results."""
    if d["status"] == "error":
        e = d["error"]
        raise ToolError(f"{e['code']}: {e['message']}" + (f" Hint: {e['hint']}" if e.get("hint") else ""))
    return model.model_validate(d)


def build_server(cases_root, raw=False, off=()):
    eng = Engine(cases_root, checks={k: False for k in off})
    mcp = MCPServer("planner-copilot-engine", instructions="Simulation guardrail engine. Every number comes from the simulator; copy warnings from the result unchanged.")

    @mcp.tool()
    def capabilities(case_id: str) -> Capabilities:
        """Parameters (unit, default, valid range, allowed values), KPIs, what the case can and cannot answer. Call first."""
        return _out(eng.capabilities(case_id), Capabilities)

    @mcp.tool()
    def knowledge_lookup(query: str, case_id: str | None = None) -> Lookup:
        """Keyword search over method notes and the case card (meanings, notes, cannot_answer). Max 3 snippets."""
        return _out(eng.knowledge_lookup(query, case_id), Lookup)

    @mcp.tool()
    def estimate(case_id: str, kpi: str, params: dict[str, Any] | None = None, question: str | None = None, event_log: bool = False) -> Result:
        """Mean and 95% CI of one KPI for one scenario (replications are added automatically). Values may be plain numbers
        in the case-card unit or {"value": x, "unit": u}. Pass the user's question text in `question` for the scope check."""
        return _out(eng.estimate(case_id, kpi, params, question, event_log), Result)

    @mcp.tool()
    def compare(case_id: str, kpi: str, params_a: dict[str, Any] | None = None, params_b: dict[str, Any] | None = None, question: str | None = None) -> Result:
        """Paired comparison (common random numbers) of two scenarios on one KPI: difference B - A, CI and verdict."""
        return _out(eng.compare(case_id, kpi, params_a, params_b, question), Result)

    if raw:
        @mcp.tool()
        def raw_simulate(case_id: str, params: dict[str, Any] | None = None, replications: int = 1) -> RawRun:
            """UNGUARDED simulator access (evaluation setups A and B): per-replication KPI values, no checks."""
            return _out(eng.raw_simulate(case_id, params, replications), RawRun)
    return mcp


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cases", default="cases", help="folder with cases/<case_id>/case_card.yaml and adapter.py")
    ap.add_argument("--raw", action="store_true", help="also serve raw_simulate (no checks)")
    ap.add_argument("--off", default="", help="comma-separated checks to switch off: scope,units,validity,adaptive_reps,paired")
    a = ap.parse_args(argv)
    build_server(a.cases, a.raw, [x for x in a.off.split(",") if x]).run("stdio")


if __name__ == "__main__":
    main()
