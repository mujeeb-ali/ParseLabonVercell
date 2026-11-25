"""Canonical LR(1), LALR(1) and the parser-class comparison."""

from fastapi.testclient import TestClient

from app.core.lr1 import analyze_lr, classify_grammar
from app.core.slr import analyze_slr
from app.examples import LR1_NOT_LALR, POINTER_ASSIGN
from app.main import app

EXPR = "E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id"


def ok_map(text):
    return {c["id"]: c["ok"] for c in classify_grammar(text)["classes"]}


def test_expression_grammar_state_counts():
    # Dragon Book: 12 LR(0)/LALR states, 22 canonical LR(1) states.
    assert analyze_slr(EXPR)["stats"]["states"] == 12
    assert analyze_lr(EXPR, method="lalr")["stats"]["states"] == 12
    assert analyze_lr(EXPR, method="lr1")["stats"]["states"] == 22


def test_pointer_grammar_is_lalr_but_not_slr():
    assert not analyze_slr(POINTER_ASSIGN)["isSLR"]
    lalr = analyze_lr(POINTER_ASSIGN, "* id = id", "lalr")
    assert lalr["deterministic"]
    assert lalr["simulation"]["accepted"]
    assert ok_map(POINTER_ASSIGN) == {"ll1": False, "slr": False, "lalr": True, "lr1": True}


def test_lr1_but_not_lalr_grammar():
    lalr = analyze_lr(LR1_NOT_LALR, "a c d", "lalr")
    assert not lalr["deterministic"]
    assert lalr["conflicts"][0]["type"] == "reduce/reduce"
    assert "merging" in lalr["conflicts"][0]["reason"]
    lr1 = analyze_lr(LR1_NOT_LALR, "a c d", "lr1")
    assert lr1["deterministic"]
    for sentence in ["a c d", "b c d", "a c e", "b c e"]:
        assert analyze_lr(LR1_NOT_LALR, sentence, "lr1")["simulation"]["accepted"], sentence
    assert not analyze_lr(LR1_NOT_LALR, "a c c", "lr1")["simulation"]["accepted"]


def test_lr_parsers_agree_with_slr_on_expression_inputs():
    for sentence, expected in [("id + id * id", True), ("( id + id ) * id", True), ("id + * id", False), ("( id", False)]:
        for method in ("slr", "lalr", "lr1"):
            assert analyze_lr(EXPR, sentence, method)["simulation"]["accepted"] is expected, (method, sentence)


def test_lalr_tree_matches_slr_tree():
    a = analyze_lr(EXPR, "id + id * id", "slr")["simulation"]["derivations"]
    b = analyze_lr(EXPR, "id + id * id", "lalr")["simulation"]["derivations"]
    assert a["rightmost"]["forms"] == b["rightmost"]["forms"]


def test_ambiguous_grammar_is_not_lr1():
    verdict = classify_grammar("E -> E + E | E * E | id")
    assert not any(c["ok"] for c in verdict["classes"])
    assert "ambiguous" in verdict["verdict"]


def test_epsilon_grammar_under_lr1():
    g = "S -> ( S ) S | ε"
    for method in ("lalr", "lr1"):
        r = analyze_lr(g, "( ( ) ) ( )", method)
        assert r["deterministic"] and r["simulation"]["accepted"]


def test_api():
    client = TestClient(app)
    r = client.post("/api/lr/analyze", json={"grammar": POINTER_ASSIGN, "input": "id = id", "method": "lalr"})
    assert r.json()["simulation"]["accepted"]
    assert client.post("/api/lr/analyze", json={"grammar": EXPR, "method": "nope"}).json()["valid"] is False
    assert client.post("/api/grammar/classify", json={"grammar": EXPR}).json()["classes"][1]["ok"] is True
