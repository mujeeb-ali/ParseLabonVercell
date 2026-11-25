from app.core.grammar import analyze_grammar, left_factor, parse_grammar, tokenize_input

EXPR_LL = """E  -> T E'
E' -> + T E' | - T E' | ε
T  -> F T'
T' -> * F T' | / F T' | ε
F  -> ( E ) | id | num"""


def test_first_and_follow_known_expression_grammar():
    a = analyze_grammar(EXPR_LL)
    assert a["valid"] is True
    assert a["first"]["E"] == ["(", "id", "num"]
    assert a["first"]["E'"] == ["+", "-", "ε"]
    assert a["first"]["T"] == ["(", "id", "num"]
    assert a["first"]["F"] == ["(", "id", "num"]
    assert a["follow"]["E"] == ["$", ")"]
    assert a["follow"]["E'"] == ["$", ")"]
    assert a["follow"]["T"] == ["$", ")", "+", "-"]
    assert a["follow"]["T'"] == ["$", ")", "+", "-"]
    assert a["follow"]["F"] == ["$", ")", "*", "+", "-", "/"]


def test_nullable_and_epsilon():
    a = analyze_grammar("S -> ( S ) S | ε")
    assert a["nullable"]["S"] is True
    assert a["first"]["S"] == ["(", "ε"]
    assert a["follow"]["S"] == ["$", ")"]


def test_left_recursion_diagnostics():
    direct = analyze_grammar("E -> E + T | T\nT -> id")
    assert any(i["kind"] == "left-recursion" for i in direct["issues"])
    indirect = analyze_grammar("A -> B a | c\nB -> A b | d")
    issue = next(i for i in indirect["issues"] if i["id"] == "indirect-left-recursion")
    assert set(issue["symbols"]) == {"A", "B"}
    assert issue["cycles"] == [["A", "B"]]


def test_left_factoring_transforms_grammar():
    source = "S -> i E t S | i E t S e S | a\nE -> b"
    result = left_factor(source)
    assert result["valid"]
    assert result["changed"]
    assert len(result["transformations"]) == 1
    assert "S′ -> ε | e S" in result["text"]
    again = left_factor(result["text"])
    assert again["valid"]
    assert again["changed"] is False


def test_unreachable_and_non_productive():
    unreachable = analyze_grammar("S -> a\nA -> b")
    assert any(i["id"] == "unreachable" and "A" in i["symbols"] for i in unreachable["issues"])
    unproductive = analyze_grammar("S -> A\nA -> b A")
    assert any(i["id"] == "non-productive" for i in unproductive["issues"])


def test_grammar_validation_errors():
    bad = analyze_grammar("E T")
    assert bad["valid"] is False
    assert "arrow" in bad["errors"][0]["message"].lower()
    empty = analyze_grammar("")
    assert empty["valid"] is False
    mixed = analyze_grammar("S -> a ε b")
    assert mixed["valid"] is False


def test_start_directive():
    g = parse_grammar("%start B\nA -> a\nB -> b")
    assert g["start"] == "B"


def test_tokenize_input_greedy_and_whitespace():
    g = parse_grammar(EXPR_LL)
    assert tokenize_input(g, "id+id*num")["tokens"] == ["id", "+", "id", "*", "num"]
    assert tokenize_input(g, "id + id")["tokens"] == ["id", "+", "id"]
    bad = tokenize_input(g, "id @ id")
    assert bad["error"]
