"""Pydantic result models. The JSON schema engine/result.schema.json is exported from `Result`
(run `python -m engine.result` to regenerate it)."""
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from . import ENGINE_VERSION

WARNING_CODES = ("outside_valid_range", "precision_not_reached", "not_distinguishable", "assumption_default_used")


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Warn(_M):
    code: Literal["outside_valid_range", "precision_not_reached", "not_distinguishable", "assumption_default_used"]
    message: str


class Refusal(_M):
    reason: str
    cannot_answer: list[str]


class ErrorInfo(_M):
    code: str  # unknown_case | wrong_type | implausible_value | missing_parameter | simulator_failed | ...
    message: str
    hint: str | None = None


class Base(_M):
    status: Literal["ok", "refused", "error"]
    tool: str
    case_id: str | None = None
    engine_version: str = ENGINE_VERSION
    error: ErrorInfo | None = None


class Result(Base):
    """Output of `estimate` and `compare` (DESIGN.md section 3)."""
    kpi: str | None = None
    unit: str | None = None
    params: dict[str, Any] | None = None          # estimate
    params_a: dict[str, Any] | None = None        # compare
    params_b: dict[str, Any] | None = None
    mean: float | None = None
    ci95: list[float] | None = None
    ci95_half_width: float | None = None
    difference_b_minus_a: float | None = None     # compare
    verdict: Literal["b_higher", "b_lower", "not_distinguishable"] | None = None
    replications: int | None = None
    precision_reached: bool | None = None
    warnings: list[Warn] = []
    extras: dict[str, Any] | None = None
    event_log: str | None = None
    checks: dict[str, bool] = {}
    refusal: Refusal | None = None


class Capabilities(Base):
    parameters: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    can_answer: list[str] = []
    cannot_answer: list[str] = []
    published_scenarios: list[dict[str, Any]] = []
    replications: dict[str, Any] = {}


class Snippet(_M):
    source: str
    text: str


class Lookup(Base):
    query: str
    results: list[Snippet] = []


class RawRun(Base):
    params: dict[str, Any] | None = None
    runs: list[dict[str, float]] = []


def export_schema(path=None):
    path = Path(path or Path(__file__).with_name("result.schema.json"))
    path.write_text(json.dumps(Result.model_json_schema(), indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print("wrote", export_schema())
