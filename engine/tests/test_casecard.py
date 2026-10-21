import pytest

from engine.casecard import load_card, validate
from conftest import FIXTURES


def test_fixture_card_loads():
    c = load_card(FIXTURES / "FAKE_case" / "case_card.yaml")
    assert c["case_id"] == "FAKE_case" and c["synonyms"]["busy week"] == {"portfolio": "over20"}


def test_validation_lists_problems(tmp_path):
    assert "missing top-level field 'outputs'" in validate({"case_id": "x", "parameters": [], "replications": {"ours_min": 3}, "cannot_answer": []})
    (tmp_path / "c.yaml").write_text("case_id: x\nparameters: [{unit: h}]\n")
    with pytest.raises(ValueError, match="parameter without name"):
        load_card(tmp_path / "c.yaml")
