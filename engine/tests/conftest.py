import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # so cases/<id>/adapter.py can `import engine...`
FIXTURES = Path(__file__).parent / "fixtures"

from engine import Engine  # noqa: E402

KPI = "overtime_after_shift"
NORM = {"portfolio": "norm"}  # portfolio has no default in the fixture card


@pytest.fixture
def eng():
    return Engine(FIXTURES)


def make(**kw):
    return Engine(FIXTURES, **kw)


def codes(res):
    return [w["code"] for w in res["warnings"]]
