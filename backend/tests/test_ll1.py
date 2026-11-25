from app.core.ll1 import analyze_ll1

EXPR = """E  -> T E'
E' -> + T E' | - T E' | ε
T  -> F T'
T' -> * F T' | / F T' | ε
F  -> ( E ) | id | num"""


def test_ll1_table_is_conflict_free():
    r = analyze_ll1(EXPR, "id + id * id")
    assert r["valid"] and r["isLL1"]
    assert r["conflicts"] == []
    table = r["table"]
    assert "$" in table["columns"]
    row_e = next(row for row in table["rows"] if row["nonterminal"] == "E")
    cell = next(c for c in row_e["cells"] if c["column"] == "id")
    assert cell["production"] == 0
    row_ep = next(row for row in table["rows"] if row["nonterminal"] == "E'")
    follow_cell = next(c for c in row_ep["cells"] if c["column"] == "$")
    assert follow_cell["production"] == 3


def test_ll1_parse_accepts_and_builds_tree():
    r = analyze_ll1(EXPR, "id + id * id")
    sim = r["simulation"]
    assert sim["accepted"] is True
    assert sim["steps"][-1]["action"] == "accept"
    assert sim["tree"]["symbol"] == "E"
    leaves = []

    def walk(n):
        if n["terminal"] and not n["children"]:
            leaves.append(n["symbol"])
        for c in n["children"]:
            walk(c)

    walk(sim["tree"])
    assert leaves == ["id", "+", "id", "*", "id"]
    leftmost = sim["derivations"]["leftmost"]["forms"]
    assert leftmost[0] == "E"
    assert leftmost[-1] == "id + id * id"
    assert len(sim["nodeCreatedAt"]) > 0


def test_ll1_rejects_invalid_input():
    r = analyze_ll1(EXPR, "id +")
    sim = r["simulation"]
    assert sim["accepted"] is False
    assert sim["error"]
    assert any(s["action"] == "error" for s in sim["steps"])


def test_ll1_conflict_detection_dangling_else():
    grammar = """S -> if E then S | if E then S else S | other
E -> cond"""
    r = analyze_ll1(grammar, "other")
    assert r["valid"]
    assert r["isLL1"] is False
    assert r["conflicts"]
    assert r["simulation"]["canParse"] is False


def test_ll1_epsilon_parse():
    r = analyze_ll1("S -> ( S ) S | ε", "( ) ( )")
    assert r["isLL1"] is True
    assert r["simulation"]["accepted"] is True
    leaves = []

    def walk(n):
        if n["terminal"] and not n["children"]:
            leaves.append(n["symbol"])
        for c in n["children"]:
            walk(c)

    walk(r["simulation"]["tree"])
    assert leaves == ["(", ")", "(", ")"]


def test_token_error_is_reported():
    r = analyze_ll1(EXPR, "id @ id")
    assert r["tokenError"]
    assert r["simulation"] is None
