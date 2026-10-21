from engine.kb import METHOD_NOTES, search


def test_method_notes_without_case(eng):
    r = eng.knowledge_lookup("how many replications and confidence interval")
    assert r["status"] == "ok" and r["results"][0]["source"] == "method:replications"
    assert eng.knowledge_lookup("how to compare two alternatives")["results"][0]["source"] == "method:comparison"
    assert eng.knowledge_lookup("unit minutes hours")["results"][0]["source"] == "method:units"


def test_case_card_is_indexed(eng):
    r = eng.knowledge_lookup("what does rush_share mean", "FAKE_case")
    assert r["results"][0]["source"] == "case_card:FAKE_case:parameter:rush_share"
    assert any("cannot_answer" in x["source"] for x in eng.knowledge_lookup("what can the model not answer, costs", "FAKE_case")["results"])
    assert "over20" in eng.knowledge_lookup("busy week", "FAKE_case")["results"][0]["text"]


def test_max_three_and_no_match(eng):
    assert len(eng.knowledge_lookup("simulation replications comparison units validity scope", "FAKE_case")["results"]) <= 3
    assert eng.knowledge_lookup("zzzz qqqq")["results"] == []
    assert search("anything", []) == [] and len(METHOD_NOTES) >= 3


def test_unknown_case(eng):
    assert eng.knowledge_lookup("x", "NOPE")["error"]["code"] == "unknown_case"
