from app.core.regex_engine import analyze_regex, dfa_accepts


def test_abb_subset_construction():
    r = analyze_regex("(a|b)*abb")
    assert r["valid"] is True
    assert r["stats"]["dfaStates"] >= 4
    assert r["stats"]["epsilonEdges"] > 0
    assert dfa_accepts(r["dfa"], "abb")
    assert dfa_accepts(r["dfa"], "aababb")
    assert dfa_accepts(r["dfa"], "babb")
    assert not dfa_accepts(r["dfa"], "ab")
    assert not dfa_accepts(r["dfa"], "abba")


def test_epsilon_and_optional():
    r = analyze_regex("a?")
    assert r["valid"]
    assert dfa_accepts(r["dfa"], "")
    assert dfa_accepts(r["dfa"], "a")
    assert not dfa_accepts(r["dfa"], "aa")
    r2 = analyze_regex("(ab)*")
    assert dfa_accepts(r2["dfa"], "")
    assert dfa_accepts(r2["dfa"], "abab")
    assert not dfa_accepts(r2["dfa"], "aba")


def test_character_classes_and_wildcard():
    num = analyze_regex("[0-9]+(\\.[0-9]+)?")
    assert dfa_accepts(num["dfa"], "42")
    assert dfa_accepts(num["dfa"], "3.14")
    assert not dfa_accepts(num["dfa"], "3.")
    ident = analyze_regex("[a-zA-Z_][a-zA-Z0-9_]*")
    assert dfa_accepts(ident["dfa"], "parse_lab2")
    assert not dfa_accepts(ident["dfa"], "2parse")
    wild = analyze_regex("a.c")
    assert dfa_accepts(wild["dfa"], "abc")
    assert not dfa_accepts(wild["dfa"], "ac")
    negated = analyze_regex("[^0-9]")
    assert dfa_accepts(negated["dfa"], "a")
    assert not dfa_accepts(negated["dfa"], "5")


def test_invalid_patterns_are_reported():
    for pattern in ["(a", "a|", "[a-", "*a", "a)", "[]"]:
        r = analyze_regex(pattern)
        assert r["valid"] is False, pattern
        assert r["error"]["message"]


def test_construction_trace_is_populated():
    r = analyze_regex("(a|b)*")
    kinds = {s["kind"] for s in r["constructionSteps"]}
    assert {"state", "epsilon", "symbol"} <= kinds
    assert r["subsetSteps"][0]["type"] == "start"
    assert r["subsetSteps"][-1]["type"] == "done"
    assert all("explanation" in s for s in r["subsetSteps"])
