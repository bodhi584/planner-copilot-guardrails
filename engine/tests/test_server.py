"""Server tests through the SDK's in-memory client (mcp.Client connected to the MCPServer object)."""
import asyncio
import json

import jsonschema
from mcp import Client

from engine.result import Result
from engine.server import build_server
from conftest import FIXTURES, KPI

SCHEMA = json.loads((FIXTURES.parents[1] / "result.schema.json").read_text())


def run(coro):
    return asyncio.run(coro)


async def _tools(**kw):
    async with Client(build_server(FIXTURES, **kw)) as c:
        return sorted(t.name for t in (await c.list_tools()).tools)


def test_four_tools_or_five_with_raw():
    assert run(_tools()) == ["capabilities", "compare", "estimate", "knowledge_lookup"]
    assert run(_tools(raw=True)) == ["capabilities", "compare", "estimate", "knowledge_lookup", "raw_simulate"]


def test_estimate_returns_structured_result():
    async def go():
        async with Client(build_server(FIXTURES)) as c:
            tool = next(t for t in (await c.list_tools()).tools if t.name == "estimate")
            r = await c.call_tool("estimate", {"case_id": "FAKE_case", "kpi": KPI, "params": {"portfolio": "busy week", "workers": 4}})
            return tool, r
    tool, r = run(go())
    assert tool.output_schema is not None and not r.is_error
    jsonschema.validate(r.structured_content, SCHEMA)
    assert r.structured_content["status"] == "ok" and r.structured_content["params"]["portfolio"] == "over20"


def test_compare_and_refusal_are_normal_results():
    async def go():
        async with Client(build_server(FIXTURES)) as c:
            a = await c.call_tool("compare", {"case_id": "FAKE_case", "kpi": KPI, "params_a": {"portfolio": "norm"}, "params_b": {"portfolio": "over20"}})
            b = await c.call_tool("estimate", {"case_id": "FAKE_case", "kpi": KPI, "params": {"portfolio": "norm"}, "question": "cost in euro?"})
            return a, b
    a, b = run(go())
    assert not a.is_error and a.structured_content["verdict"] == "b_higher"
    assert not b.is_error and b.structured_content["status"] == "refused"


def test_error_status_becomes_is_error_with_hint():
    async def go():
        async with Client(build_server(FIXTURES)) as c:
            return await c.call_tool("estimate", {"case_id": "FAKE_case", "kpi": KPI, "params": {"portfolio": "norm", "shift_length": 8}})
    r = run(go())
    assert r.is_error and "implausible_value" in r.content[0].text and "8 h = 480" in r.content[0].text


def test_lookup_capabilities_raw_and_off_flag():
    async def go():
        async with Client(build_server(FIXTURES, raw=True, off=["scope"])) as c:
            cap = await c.call_tool("capabilities", {"case_id": "FAKE_case"})
            kb = await c.call_tool("knowledge_lookup", {"query": "replications"})
            raw = await c.call_tool("raw_simulate", {"case_id": "FAKE_case", "params": {"portfolio": "norm"}, "replications": 2})
            est = await c.call_tool("estimate", {"case_id": "FAKE_case", "kpi": KPI, "params": {"portfolio": "norm", "zzz": 1}})
            return cap, kb, raw, est
    cap, kb, raw, est = run(go())
    assert cap.structured_content["status"] == "ok" and kb.structured_content["results"]
    assert len(raw.structured_content["runs"]) == 2
    assert est.structured_content["status"] == "ok" and est.structured_content["checks"]["scope"] is False
    Result.model_validate(est.structured_content)
