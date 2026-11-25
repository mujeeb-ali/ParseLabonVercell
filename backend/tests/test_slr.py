from app.core.slr import analyze_slr

EXPR = """E -> E + T | E - T | T
T -> T * F | T / F | F
F -> ( E ) | id | num"""


def test_slr_expression_automaton_and_table():
    r = analyze_slr(EXPR, "id + id * id")
    assert r["valid"] and r["isSLR"]
    # This grammar includes both +/- and */ plus id and num, producing 17 LR(0) states.
    assert r["stats"]["states"] == 17
    assert r["conflicts"] == []
    assert r["automaton"]["states"][0]["start"] is True
    assert any(
        item["production"] == r["automaton"]["augmented"]["index"] and item["dot"] == 0
        for item in r["automaton"]["states"][0]["items"]
    )
    assert r["automaton"]["augmented"]["lhs"].endswith("′")


def test_slr_parse_accepts():
    r = analyze_slr(EXPR, "id + id * id")
    sim = r["simulation"]
    assert sim["accepted"] is True
    assert sim["steps"][-1]["action"]["type"] == "accept"
    leaves = []

    def walk(n):
        if n["terminal"] and not n["children"]:
            leaves.append(n["symbol"])
        for c in n["children"]:
            walk(c)

    walk(sim["tree"])
    assert leaves == ["id", "+", "id", "*", "id"]
    assert sim["derivations"]["rightmost"]["forms"][-1] == "id + id * id"
    actions = [s["action"]["type"] for s in sim["steps"]]
    assert "shift" in actions and "reduce" in actions


def test_slr_rejects_invalid_input():
    r = analyze_slr(EXPR, "id + * id")
    sim = r["simulation"]
    assert sim["accepted"] is False
    assert sim["error"]


def test_shift_reduce_conflict_ambiguous_grammar():
    r = analyze_slr("E -> E + E | E * E | id", "id + id * id")
    assert r["valid"]
    assert r["isSLR"] is False
    assert r["conflicts"]
    assert any(c["type"] == "shift/reduce" for c in r["conflicts"])
    assert r["simulation"]["canParse"] is False


def test_shift_reduce_conflict_dangling_else():
    grammar = """S -> if E then S | if E then S else S | other
E -> cond"""
    r = analyze_slr(grammar, "other")
    assert r["isSLR"] is False
    assert any(c["type"] == "shift/reduce" for c in r["conflicts"])


def test_reduce_reduce_conflict():
    grammar = "S -> A | B\nA -> c\nB -> c"
    r = analyze_slr(grammar, "c")
    assert r["isSLR"] is False
    assert any(c["type"] == "reduce/reduce" for c in r["conflicts"])


def test_lr0_closure_contains_expansions():
    r = analyze_slr(EXPR)
    texts = [item["text"] for item in r["automaton"]["states"][0]["items"]]
    assert any(t.startswith("E′ → · E") for t in texts)
    assert any(t.startswith("E → · E + T") for t in texts)
    assert any(t.startswith("F → · id") for t in texts)
