"""Regression tests for bugs found during review and for the newer features."""

from fastapi.testclient import TestClient

from app.core.grammar import analyze_grammar, eliminate_left_recursion, parse_grammar, tokenize_input
from app.core.lexer import analyze_lexer
from app.core.ll1 import analyze_ll1
from app.core.regex_engine import analyze_regex, dfa_accepts
from app.core.slr import analyze_slr
from app.core.timemachine import run_time_machine
from app.examples import EXAMPLES, get_example
from app.main import app


def accepts(pattern: str, text: str) -> bool:
    result = analyze_regex(pattern)
    assert result["valid"], result
    return dfa_accepts(result["dfa"], text)


# --- Regex / automata -------------------------------------------------------


def test_wildcard_is_followed_on_concrete_symbols_in_subset_construction():
    # Before the fix, move(D0, 'a') ignored the '.' branch, so "ac" was rejected.
    assert accepts("ab|.c", "ac")
    assert accepts("ab|.c", "ab")
    assert accepts("ab|.c", "zc")
    assert not accepts("ab|.c", "az")


def test_wildcard_does_not_match_newline():
    assert accepts("a.b", "a-b")
    assert not accepts("a.b", "a\nb")


def test_negated_class_spans_tabs_and_newlines():
    assert accepts('"[^"]*"', '"a\tb"')
    assert accepts('"[^"]*"', '"line1\nline2"')
    assert not accepts('"[^"]*"', '"a"b"')


def test_minimized_dfa_for_textbook_pattern():
    result = analyze_regex("(a|b)*abb")
    assert result["stats"]["dfaStates"] == 5
    assert result["stats"]["minDfaStates"] == 4
    minimal = result["minDfa"]
    assert minimal["start"] == "M0"
    assert minimal["steps"][-1]["explanation"].startswith("Round")
    for text, expected in [("abb", True), ("aabb", True), ("babb", True), ("ab", False), ("abba", False)]:
        assert dfa_accepts(minimal, text) is expected


def test_minimization_preserves_language_on_random_strings():
    import random

    rng = random.Random(7)
    for pattern in ["(a|b)*abb", "a*b*", "(ab|ba)*", "a(b|c)*d?", "(0|1(01*0)*1)*"]:
        r = analyze_regex(pattern)
        alphabet = [s for s in r["dfa"]["alphabet"]]
        for _ in range(200):
            word = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))
            assert dfa_accepts(r["dfa"], word) == dfa_accepts(r["minDfa"], word), (pattern, word)


def test_binary_multiples_of_three_minimal_dfa_has_three_states():
    r = analyze_regex("(0|1(01*0)*1)*")
    assert r["stats"]["minDfaStates"] == 3


# --- Lexer ------------------------------------------------------------------


def test_line_comment_stops_at_newline():
    rules = [
        {"name": "ID", "pattern": "[a-z]+"},
        {"name": "COMMENT", "pattern": "//.*", "skip": True},
        {"name": "WS", "pattern": "[ \\n]+", "skip": True},
    ]
    result = analyze_lexer("x // note\ny", rules)
    assert [t["lexeme"] for t in result["tokens"]] == ["x", "y"]
    assert result["tokens"][1]["line"] == 2


# --- Grammar ----------------------------------------------------------------


def test_continuation_lines_with_bar():
    g = parse_grammar("E -> E + T\n   | T\nT -> id")
    assert [p["text"] for p in g["productions"]] == ["E → E + T", "E → T", "T → id"]


def test_bar_line_without_production_is_an_error():
    result = analyze_grammar("| a")
    assert not result["valid"]


def test_leftmost_arrow_is_used():
    g = parse_grammar("S := a -> b")
    assert g["productions"][0]["rhs"] == ["a", "->", "b"]


def test_hidden_left_recursion_is_reported():
    result = analyze_grammar("A -> B A x | y\nB -> b | ε")
    ids = [i["id"] for i in result["issues"]]
    assert "hidden-left-recursion" in ids


def test_mixed_spacing_input_tokenizes():
    g = parse_grammar("E -> E + T | T\nT -> T * F | F\nF -> id")
    assert tokenize_input(g, "id + id*id") == {"tokens": ["id", "+", "id", "*", "id"], "error": None}
    assert tokenize_input(g, "id + id ? id")["error"] is not None


def test_eliminate_direct_left_recursion_gives_ll1_grammar():
    result = eliminate_left_recursion("E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id")
    assert result["changed"]
    ll = analyze_ll1(result["text"], "id + id * id")
    assert ll["isLL1"]
    assert ll["simulation"]["accepted"]


def test_eliminate_indirect_left_recursion_dragon_book_example():
    result = eliminate_left_recursion("S -> A a | b\nA -> A c | S d | e")
    assert result["text"].splitlines() == [
        "S  -> A a | b",
        "A  -> b d A' | e A'",
        "A' -> c A' | a d A' | ε",
    ]
    assert not result["analysis"]["stats"]["leftRecursive"]


def test_eliminate_preserves_language_on_samples():
    original = "E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id"
    transformed = eliminate_left_recursion(original)["text"]
    for sentence, ok in [("id", True), ("id + id", True), ("( id + id ) * id", True), ("id +", False), ("( id", False)]:
        assert analyze_slr(original, sentence)["simulation"]["accepted"] is ok
        assert analyze_ll1(transformed, sentence)["simulation"]["accepted"] is ok


# --- Parsers ----------------------------------------------------------------


def test_ll1_reports_trailing_input_clearly():
    sim = analyze_ll1("S -> a", "a a")["simulation"]
    assert not sim["accepted"]
    assert "input remains" in sim["error"]


def test_ll1_error_lists_expected_terminals():
    sim = analyze_ll1("S -> a b | c", "b")["simulation"]
    assert "Expected one of: a, c" in sim["error"]


# --- Time machine -----------------------------------------------------------


def test_time_machine_rejects_source_with_lexical_errors():
    payload = dict(get_example("time-assignment-ll")["payload"])
    assert run_time_machine(payload)["accepted"]
    payload["source"] = "total = @ price * 12 + tax;"
    result = run_time_machine(payload)
    assert not result["accepted"]
    assert "Lexical error" in result["error"]


def test_every_example_runs_without_crashing():
    for ex in EXAMPLES:
        payload = ex["payload"]
        kind = ex["kind"]
        if kind == "timemachine":
            run_time_machine(payload)
        elif kind == "lexer":
            analyze_lexer(payload["source"], payload["rules"])
        elif kind == "regex":
            analyze_regex(payload["pattern"])
        elif kind == "ll1":
            analyze_ll1(payload["grammar"], payload.get("input", ""))
        elif kind == "slr":
            analyze_slr(payload["grammar"], payload.get("input", ""))
        else:
            analyze_grammar(payload["grammar"])


# --- HTTP API ---------------------------------------------------------------


def test_api_endpoints():
    client = TestClient(app)
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/examples").json()["count"] == len(EXAMPLES)
    r = client.post("/api/grammar/left-recursion", json={"grammar": "E -> E + T | T\nT -> id"})
    assert r.status_code == 200 and r.json()["changed"]
    r = client.post("/api/regex/analyze", json={"pattern": "(a|b)*abb"})
    assert r.json()["stats"]["minDfaStates"] == 4
    assert client.post("/api/regex/analyze", json={"pattern": 3}).status_code == 422


def test_left_recursion_is_a_warning_not_an_error():
    # The classic expression grammar is valid (SLR/LALR/LR(1) handle it); it only blocks LL(1).
    issues = analyze_grammar("E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id")["issues"]
    lr = [i for i in issues if i["kind"] == "left-recursion"]
    assert lr and all(i["severity"] == "warning" and i["affects"] == ["LL(1)"] for i in lr)
    assert not any(i["severity"] == "error" for i in issues)
    # A genuinely broken grammar is still an error.
    assert any(i["severity"] == "error" for i in analyze_grammar("A -> B\nB -> A")["issues"])


def test_sample_sentences_are_derivable():
    from app.core.grammar import sample_sentences
    from app.core.lr1 import analyze_lr

    for text in ["E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id", "S -> ( S ) S | ε", "S -> L = R | R\nL -> * R | id\nR -> L"]:
        g = parse_grammar(text)
        samples = sample_sentences(g, seed=3)
        assert samples and len(set(samples)) == len(samples)
        for s in samples:
            if s:
                assert analyze_lr(text, s, "lr1")["simulation"]["accepted"], (text, s)
    assert sample_sentences(parse_grammar("A -> B\nB -> A")) == []
    client = TestClient(app)
    assert client.post("/api/grammar/samples", json={"grammar": "S -> a S | b", "seed": 5}).json()["samples"][0] == "b"
