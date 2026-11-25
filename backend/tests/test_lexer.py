from app.core.lexer import analyze_lexer

RULES = [
    {"name": "IF", "pattern": "if", "skip": False},
    {"name": "ID", "pattern": "[a-zA-Z_][a-zA-Z0-9_]*", "skip": False},
    {"name": "NUM", "pattern": "[0-9]+", "skip": False},
    {"name": "PLUS", "pattern": r"\+", "skip": False},
    {"name": "STAR", "pattern": r"\*", "skip": False},
    {"name": "WS", "pattern": "[ \\t\\n]+", "skip": True},
]


def test_maximal_munch_and_keyword_priority():
    r = analyze_lexer("if ifx 12+3", RULES)
    assert r["valid"] is True
    assert r["errors"] == []
    assert [(t["type"], t["lexeme"]) for t in r["tokens"]] == [
        ("IF", "if"),
        ("ID", "ifx"),
        ("NUM", "12"),
        ("PLUS", "+"),
        ("NUM", "3"),
    ]
    # `skipped` reports source characters consumed by skip rules.
    assert r["stats"]["skipped"] == 2


def test_positions_are_one_based_and_track_newlines():
    r = analyze_lexer("x\n  y + 1", RULES)
    assert [(t["type"], t["line"], t["column"]) for t in r["tokens"]] == [
        ("ID", 1, 1),
        ("ID", 2, 3),
        ("PLUS", 2, 5),
        ("NUM", 2, 7),
    ]
    assert r["tokens"][0]["start"] == 0
    assert r["tokens"][1]["start"] == 4


def test_unknown_character_is_an_error_but_scan_continues():
    r = analyze_lexer("x @ y", RULES)
    assert r["errors"]
    assert r["errors"][0]["char"] == "@"
    assert r["errors"][0]["column"] == 3
    assert [t["lexeme"] for t in r["tokens"]] == ["x", "y"]


def test_invalid_rule_does_not_crash():
    rules = [{"name": "A", "pattern": "("}, {"name": "WS", "pattern": " +", "skip": True}]
    r = analyze_lexer("abc", rules)
    assert r["valid"] is False
    assert r["ruleErrors"]
    assert r["tokens"] == []


def test_duplicate_names_are_rejected():
    rules = [{"name": "A", "pattern": "a"}, {"name": "A", "pattern": "b"}]
    r = analyze_lexer("a", rules)
    assert r["valid"] is False
    assert "Duplicate" in r["ruleErrors"][0]["message"]


def test_spans_cover_the_source():
    r = analyze_lexer("if x", RULES)
    covered = []
    for span in r["spans"]:
        covered.extend(range(span["start"], span["end"]))
    assert covered == list(range(len("if x")))


def test_token_explanation_and_candidates_are_real():
    r = analyze_lexer("ifx", RULES)
    tok = r["tokens"][0]
    assert tok["type"] == "ID"
    assert tok["path"][0].startswith("D")
    assert any(c["rule"] == "IF" and c["length"] == 2 for c in tok["candidates"])
    assert "longest match" in tok["explanation"].lower() or "only rule" in tok["explanation"].lower()
