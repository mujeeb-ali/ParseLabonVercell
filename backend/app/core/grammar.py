"""Context-free grammar parsing, validation, FIRST/FOLLOW and diagnostics."""

from __future__ import annotations

import re
from collections import deque
from typing import Any, Iterable

EPS = "\u03b5"
EOF = "$"
_ARROWS = ("->", "::=", "\u2192", "\u27f6", ":=")
_EPS_NAMES = {"ε", "ϵ", "eps", "epsilon", "lambda", "empty", "\\e"}
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_'\u2032]*$")
_MAX_ROUNDS = 200


class GrammarError(Exception):
    def __init__(self, errors: list[dict[str, Any]]):
        super().__init__(errors[0]["message"] if errors else "Invalid grammar")
        self.errors = errors


def _strip_comment(line: str) -> str:
    cut = len(line)
    for marker in ("//", "#"):
        idx = line.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    return line[:cut]


def _clean_symbol(raw: str) -> str:
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def parse_grammar(text: str) -> dict[str, Any]:
    """Parse grammar source into productions and symbol tables.

    Raises :class:`GrammarError` when the source cannot be understood.  A
    returned grammar always has at least one production.
    """
    if not text or not text.strip():
        raise GrammarError([{"line": 0, "message": "Grammar is empty. Add a production such as E -> E + T | T."}])

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    raw_productions: list[dict[str, Any]] = []
    start_override: str | None = None
    last_lhs: str | None = None

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw_line).strip()
        if not line:
            continue
        # Textbook layout: an alternative on its own line, e.g.
        #   E -> E + T
        #      | T
        if line.startswith("|"):
            if last_lhs is None:
                errors.append({"line": line_no, "message": "A line starting with '|' must follow a production."})
                continue
            line = f"{last_lhs} -> {line[1:]}"
        if line.startswith("%start"):
            parts = line.split()
            if len(parts) != 2:
                errors.append({"line": line_no, "message": "The %start directive expects exactly one non-terminal, e.g. %start E."})
            else:
                start_override = parts[1]
            continue
        if line.startswith("%"):
            warnings.append({"line": line_no, "message": f"Unknown directive '{line.split()[0]}' ignored."})
            continue

        # Use the left-most arrow so that an arrow-like terminal later on the
        # right-hand side cannot be mistaken for the separator.
        found = [(line.find(a), -len(a), a) for a in _ARROWS if a in line]
        arrow = min(found)[2] if found else None
        if arrow is None:
            errors.append({"line": line_no, "message": "Missing production arrow. Use '->' between the left and right sides."})
            continue
        lhs_raw, rhs_raw = line.split(arrow, 1)
        lhs = lhs_raw.strip()
        if not lhs:
            errors.append({"line": line_no, "message": "Production has no left-hand non-terminal."})
            continue
        if " " in lhs or "\t" in lhs:
            errors.append({"line": line_no, "message": f"Left-hand side '{lhs}' must be a single non-terminal."})
            continue
        if not _NAME_RE.match(lhs):
            errors.append({"line": line_no, "message": f"Invalid non-terminal '{lhs}'. Use letters, digits, underscore or a trailing prime."})
            continue
        last_lhs = lhs

        alternatives = rhs_raw.split("|")
        if not alternatives:
            alternatives = [""]
        for alt in alternatives:
            alt = alt.strip()
            if not alt:
                rhs: list[str] = []
            else:
                symbols = [_clean_symbol(s) for s in alt.split()]
                if any(s in _EPS_NAMES for s in symbols):
                    if len(symbols) != 1:
                        errors.append({"line": line_no, "message": f"Epsilon must stand alone in an alternative: '{alt}'."})
                        continue
                    rhs = []
                else:
                    bad = [s for s in symbols if s in (EOF, "|")]
                    if bad:
                        errors.append({"line": line_no, "message": f"Reserved symbol '{bad[0]}' cannot be used in a production."})
                        continue
                    rhs = symbols
            raw_productions.append(
                {
                    "lhs": lhs,
                    "rhs": rhs,
                    "line": line_no,
                    "text": f"{lhs} → {' '.join(rhs) if rhs else EPS}",
                }
            )

    if not raw_productions:
        if not errors:
            errors.append({"line": 0, "message": "No valid productions were found."})
        raise GrammarError(errors)

    nonterminals: list[str] = []
    for p in raw_productions:
        if p["lhs"] not in nonterminals:
            nonterminals.append(p["lhs"])
    nt_set = set(nonterminals)
    terminals: list[str] = []
    for p in raw_productions:
        for sym in p["rhs"]:
            if sym not in nt_set and sym not in terminals:
                terminals.append(sym)

    start = start_override or nonterminals[0]
    if start not in nt_set:
        errors.append({"line": 0, "message": f"Start symbol '{start}' is not defined by any production."})

    seen: dict[tuple[str, tuple[str, ...]], int] = {}
    for p in raw_productions:
        key = (p["lhs"], tuple(p["rhs"]))
        if key in seen:
            warnings.append(
                {
                    "line": p["line"],
                    "message": f"Duplicate production {p['text']} (first defined on line {seen[key]}).",
                }
            )
        else:
            seen[key] = p["line"]

    if errors:
        raise GrammarError(errors)

    productions = []
    for i, p in enumerate(raw_productions):
        productions.append(
            {
                "index": i,
                "lhs": p["lhs"],
                "rhs": p["rhs"],
                "line": p["line"],
                "text": p["text"],
            }
        )

    grammar = {
        "productions": productions,
        "nonterminals": nonterminals,
        "terminals": terminals,
        "start": start,
        "startExplicit": start_override is not None,
        "warnings": warnings,
    }
    return grammar


# ---------------------------------------------------------------------------
# Reachability / productivity / nullable
# ---------------------------------------------------------------------------


def reachable_nonterminals(g: dict[str, Any]) -> set[str]:
    reachable = {g["start"]}
    changed = True
    while changed:
        changed = False
        for p in g["productions"]:
            if p["lhs"] in reachable:
                for sym in p["rhs"]:
                    if sym in g["nonterminals"] and sym not in reachable:
                        reachable.add(sym)
                        changed = True
    return reachable


def productive_nonterminals(g: dict[str, Any]) -> set[str]:
    productive: set[str] = set()
    changed = True
    while changed:
        changed = False
        for p in g["productions"]:
            if p["lhs"] in productive:
                continue
            if all(sym not in g["nonterminals"] or sym in productive for sym in p["rhs"]):
                productive.add(p["lhs"])
                changed = True
    return productive


def compute_nullable(g: dict[str, Any]) -> tuple[dict[str, bool], list[dict[str, Any]]]:
    nullable = {nt: False for nt in g["nonterminals"]}
    steps: list[dict[str, Any]] = []
    changed = True
    round_no = 0
    while changed and round_no < _MAX_ROUNDS:
        changed = False
        round_no += 1
        for p in g["productions"]:
            if nullable[p["lhs"]]:
                continue
            if all(sym in g["nonterminals"] and nullable[sym] for sym in p["rhs"]):
                nullable[p["lhs"]] = True
                steps.append(
                    {
                        "round": round_no,
                        "target": p["lhs"],
                        "production": p["index"],
                        "reason": (
                            f"{p['text']} is nullable because every symbol on its right side is nullable."
                            if p["rhs"]
                            else f"{p['text']} is an epsilon production, so {p['lhs']} is nullable."
                        ),
                    }
                )
                changed = True
    return nullable, steps


def first_of_sequence(
    symbols: Iterable[str],
    first: dict[str, set[str]],
    nullable: dict[str, bool],
) -> set[str]:
    result: set[str] = set()
    for sym in symbols:
        if sym in first:
            result |= first[sym]
            if EPS not in result:
                return result
            result.discard(EPS)
        else:
            result.add(sym)
            return result
    result.add(EPS)
    return result


def compute_first(
    g: dict[str, Any], nullable: dict[str, bool]
) -> tuple[dict[str, set[str]], list[dict[str, Any]]]:
    first: dict[str, set[str]] = {nt: set() for nt in g["nonterminals"]}
    steps: list[dict[str, Any]] = []
    changed = True
    round_no = 0
    while changed and round_no < _MAX_ROUNDS:
        changed = False
        round_no += 1
        for p in g["productions"]:
            addition = first_of_sequence(p["rhs"], first, nullable)
            new = addition - first[p["lhs"]]
            if new:
                first[p["lhs"]] |= new
                changed = True
                for sym in sorted(new):
                    steps.append(
                        {
                            "round": round_no,
                            "target": p["lhs"],
                            "symbol": sym,
                            "production": p["index"],
                            "reason": (
                                f"{p['text']} contributes {sym} to FIRST({p['lhs']})"
                                + (f" because {sym} begins the right side." if p["rhs"] and p["rhs"][0] == sym else " through a nullable prefix.")
                            ),
                        }
                    )
    return first, steps


def compute_follow(
    g: dict[str, Any], nullable: dict[str, bool], first: dict[str, set[str]]
) -> tuple[dict[str, set[str]], list[dict[str, Any]]]:
    follow: dict[str, set[str]] = {nt: set() for nt in g["nonterminals"]}
    follow[g["start"]].add(EOF)
    steps: list[dict[str, Any]] = [
        {
            "round": 0,
            "target": g["start"],
            "symbol": EOF,
            "production": -1,
            "reason": f"${' is placed in FOLLOW('}{g['start']}) because it is the start symbol.",
        }
    ]
    changed = True
    round_no = 0
    while changed and round_no < _MAX_ROUNDS:
        changed = False
        round_no += 1
        for p in g["productions"]:
            rhs = p["rhs"]
            for i, sym in enumerate(rhs):
                if sym not in follow:
                    continue
                suffix = rhs[i + 1 :]
                suffix_first = first_of_sequence(suffix, first, nullable)
                additions: set[str] = set(suffix_first)
                additions.discard(EPS)
                from_follow_lhs = EPS in suffix_first
                new = additions - follow[sym]
                if new:
                    follow[sym] |= new
                    changed = True
                    for t in sorted(new):
                        steps.append(
                            {
                                "round": round_no,
                                "target": sym,
                                "symbol": t,
                                "production": p["index"],
                                "reason": f"In {p['text']}, {t} is in FIRST({' '.join(suffix) if suffix else 'ε'}) and therefore follows {sym}.",
                            }
                        )
                if from_follow_lhs:
                    inherited = follow[p["lhs"]] - follow[sym]
                    if inherited:
                        follow[sym] |= inherited
                        changed = True
                        for t in sorted(inherited):
                            steps.append(
                                {
                                    "round": round_no,
                                    "target": sym,
                                    "symbol": t,
                                    "production": p["index"],
                                    "reason": f"In {p['text']}, everything that follows {p['lhs']} also follows {sym} because the suffix is nullable.",
                                }
                            )
    return follow, steps


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Return simple cycles in a directed graph (each cycle once)."""
    cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()
    color: dict[str, int] = {n: 0 for n in graph}
    stack: list[str] = []

    def dfs(node: str) -> None:
        color[node] = 1
        stack.append(node)
        for nxt in sorted(graph.get(node, ())):
            if color.get(nxt, 0) == 0:
                dfs(nxt)
            elif color.get(nxt) == 1:
                idx = stack.index(nxt)
                cycle = stack[idx:]
                key = tuple(cycle)
                rotations = [tuple(cycle[i:] + cycle[:i]) for i in range(len(cycle))]
                canonical = min(rotations)
                if canonical not in seen_cycles:
                    seen_cycles.add(canonical)
                    cycles.append(cycle)
        stack.pop()
        color[node] = 2

    for node in sorted(graph):
        if color[node] == 0:
            dfs(node)
    return cycles


def _left_corner_graph(g: dict[str, Any], nullable: dict[str, bool]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {nt: set() for nt in g["nonterminals"]}
    for p in g["productions"]:
        for sym in p["rhs"]:
            if sym in graph:
                graph[p["lhs"]].add(sym)
            if not (sym in g["nonterminals"] and nullable[sym]):
                break
    return graph


def _common_prefix(alternatives: list[list[str]]) -> list[str]:
    if not alternatives:
        return []
    prefix = list(alternatives[0])
    for alt in alternatives[1:]:
        limit = min(len(prefix), len(alt))
        i = 0
        while i < limit and prefix[i] == alt[i]:
            i += 1
        prefix = prefix[:i]
        if not prefix:
            break
    return prefix


def diagnose(g: dict[str, Any], nullable: dict[str, bool]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    nts = g["nonterminals"]
    reachable = reachable_nonterminals(g)
    productive = productive_nonterminals(g)

    direct = []
    for p in g["productions"]:
        if p["rhs"] and p["rhs"][0] == p["lhs"]:
            direct.append(p)
    if direct:
        issues.append(
            {
                "id": "direct-left-recursion",
                "severity": "warning",
                "affects": ["LL(1)"],
                "title": "Direct left recursion",
                "detail": "A non-terminal can expand to itself at the left edge. This is fine for bottom-up parsers "
                "(SLR, LALR, LR(1)), but a top-down LL(1) parser would loop forever. Use “Eliminate left recursion” to get an LL(1)-friendly version.",
                "symbols": sorted({p["lhs"] for p in direct}),
                "productions": [p["index"] for p in direct],
                "kind": "left-recursion",
            }
        )

    lc_graph = _left_corner_graph(g, nullable)
    direct_lhs = {p["lhs"] for p in direct}
    hidden = sorted(nt for nt in nts if nt in lc_graph[nt] and nt not in direct_lhs)
    if hidden:
        issues.append(
            {
                "id": "hidden-left-recursion",
                "severity": "warning",
                "affects": ["LL(1)"],
                "title": "Hidden left recursion",
                "detail": "A nullable prefix lets these non-terminals reach themselves at the left edge "
                "(e.g. A → B A with B ⇒* ε). It is easy to miss, and it still breaks LL(1).",
                "symbols": hidden,
                "kind": "left-recursion",
            }
        )

    cycles = _find_cycles(lc_graph)
    indirect = [c for c in cycles if len(c) > 1]
    if indirect:
        issues.append(
            {
                "id": "indirect-left-recursion",
                "severity": "warning",
                "affects": ["LL(1)"],
                "title": "Indirect left recursion",
                "detail": "A cycle in the left-corner graph means these non-terminals can reach themselves without consuming input.",
                "symbols": indirect[0],
                "cycles": indirect,
                "kind": "left-recursion",
            }
        )

    by_lhs: dict[str, list[list[str]]] = {}
    for p in g["productions"]:
        by_lhs.setdefault(p["lhs"], []).append(p["rhs"])
    opportunities = []
    for lhs, alts in by_lhs.items():
        groups: dict[str, list[list[str]]] = {}
        for alt in alts:
            if alt:
                groups.setdefault(alt[0], []).append(alt)
        for key, group in groups.items():
            if len(group) > 1:
                prefix = _common_prefix(group)
                if prefix:
                    opportunities.append(
                        {
                            "lhs": lhs,
                            "prefix": prefix,
                            "count": len(group),
                            "detail": f"{len(group)} alternatives of {lhs} begin with {' '.join(prefix)}.",
                        }
                    )
    if opportunities:
        issues.append(
            {
                "id": "left-factoring",
                "severity": "warning",
                "title": "Left-factoring opportunity",
                "detail": "Alternatives share a common prefix. Factoring delays the decision and can make the grammar LL(1).",
                "symbols": sorted({o["lhs"] for o in opportunities}),
                "opportunities": opportunities,
                "kind": "factoring",
            }
        )

    unreachable = [nt for nt in nts if nt not in reachable]
    if unreachable:
        issues.append(
            {
                "id": "unreachable",
                "severity": "warning",
                "title": "Unreachable non-terminals",
                "detail": "These non-terminals cannot be reached from the start symbol and have no effect on the language.",
                "symbols": unreachable,
                "kind": "reachability",
            }
        )

    unproductive = [nt for nt in nts if nt not in productive]
    if unproductive:
        issues.append(
            {
                "id": "non-productive",
                "severity": "error",
                "title": "Non-productive non-terminals",
                "detail": "These non-terminals can never derive a string of terminals.",
                "symbols": unproductive,
                "kind": "productivity",
            }
        )

    unit_graph: dict[str, set[str]] = {nt: set() for nt in nts}
    for p in g["productions"]:
        if len(p["rhs"]) == 1 and p["rhs"][0] in unit_graph:
            unit_graph[p["lhs"]].add(p["rhs"][0])
    unit_cycles = _find_cycles(unit_graph)
    if unit_cycles:
        issues.append(
            {
                "id": "unit-cycle",
                "severity": "warning",
                "title": "Unit-production cycle",
                "detail": "A cycle of A → B productions can cause an infinite expansion in naive top-down parsers.",
                "symbols": unit_cycles[0],
                "kind": "cycle",
            }
        )

    if not issues:
        issues.append(
            {
                "id": "clean",
                "severity": "ok",
                "title": "No structural defects detected",
                "detail": "No left recursion, factoring opportunity, unreachable symbol or unit cycle was found. "
                "LL(1) and SLR conflicts are reported in their own studios.",
                "symbols": [],
                "kind": "clean",
            }
        )
    return issues


def analyze_grammar(text: str) -> dict[str, Any]:
    try:
        g = parse_grammar(text)
    except GrammarError as exc:
        return {"valid": False, "errors": exc.errors, "text": text}

    nullable, nullable_steps = compute_nullable(g)
    first, first_steps = compute_first(g, nullable)
    follow, follow_steps = compute_follow(g, nullable, first)
    issues = diagnose(g, nullable)
    reachable = reachable_nonterminals(g)

    prod_first = []
    for p in g["productions"]:
        prod_first.append(
            {
                "production": p["index"],
                "first": sorted(first_of_sequence(p["rhs"], first, nullable)),
                "nullable": all(s in g["nonterminals"] and nullable[s] for s in p["rhs"]),
            }
        )

    return {
        "valid": True,
        "text": text,
        "grammar": {
            "productions": g["productions"],
            "nonterminals": g["nonterminals"],
            "terminals": g["terminals"],
            "start": g["start"],
            "startExplicit": g["startExplicit"],
        },
        "nullable": nullable,
        "first": {nt: sorted(v) for nt, v in first.items()},
        "follow": {nt: sorted(v) for nt, v in follow.items()},
        "firstOfProductions": prod_first,
        "firstSteps": first_steps,
        "followSteps": follow_steps,
        "nullableSteps": nullable_steps,
        "issues": issues,
        "warnings": g["warnings"],
        "reachable": sorted(reachable),
        "samples": sample_sentences(g),
        "stats": {
            "productions": len(g["productions"]),
            "nonterminals": len(g["nonterminals"]),
            "terminals": len(g["terminals"]),
            "nullable": sum(1 for v in nullable.values() if v),
            "leftRecursive": any(i["kind"] == "left-recursion" for i in issues),
        },
    }


# ---------------------------------------------------------------------------
# Left factoring
# ---------------------------------------------------------------------------


def left_factor(text: str) -> dict[str, Any]:
    """Apply left factoring until no common prefixes remain."""
    try:
        g = parse_grammar(text)
    except GrammarError as exc:
        return {"valid": False, "errors": exc.errors}

    prods: list[tuple[str, list[str]]] = [(p["lhs"], list(p["rhs"])) for p in g["productions"]]
    existing = set(g["nonterminals"])
    transformations: list[dict[str, Any]] = []

    for _ in range(60):
        by_lhs: dict[str, list[list[str]]] = {}
        order: list[str] = []
        for lhs, rhs in prods:
            if lhs not in by_lhs:
                by_lhs[lhs] = []
                order.append(lhs)
            by_lhs[lhs].append(rhs)

        changed = False
        rebuilt: list[tuple[str, list[str]]] = []
        for lhs in order:
            alts = by_lhs[lhs]
            groups: dict[str, list[list[str]]] = {}
            group_order: list[str] = []
            for alt in alts:
                if not alt:
                    continue
                key = alt[0]
                if key not in groups:
                    groups[key] = []
                    group_order.append(key)
                groups[key].append(alt)
            factored_keys = {
                key for key in group_order if len(groups[key]) > 1 and _common_prefix(groups[key])
            }
            if not factored_keys:
                for alt in alts:
                    rebuilt.append((lhs, alt))
                continue
            changed = True
            for alt in alts:
                if not alt:
                    rebuilt.append((lhs, alt))
            for key in group_order:
                group = groups[key]
                if key not in factored_keys:
                    for alt in group:
                        rebuilt.append((lhs, alt))
                    continue
                prefix = _common_prefix(group)
                base = lhs + "\u2032"
                new_nt = base
                counter = 2
                while new_nt in existing:
                    new_nt = f"{base}{counter}"
                    counter += 1
                existing.add(new_nt)
                rebuilt.append((lhs, prefix + [new_nt]))
                for alt in group:
                    rebuilt.append((new_nt, alt[len(prefix) :]))
                transformations.append(
                    {
                        "lhs": lhs,
                        "prefix": prefix,
                        "newNonterminal": new_nt,
                        "alternatives": len(group),
                    }
                )
        prods = rebuilt
        if not changed:
            break

    lines = []
    by_lhs_final: dict[str, list[list[str]]] = {}
    order_final: list[str] = []
    for lhs, rhs in prods:
        if lhs not in by_lhs_final:
            by_lhs_final[lhs] = []
            order_final.append(lhs)
        by_lhs_final[lhs].append(rhs)
    for lhs in order_final:
        alts = [" ".join(rhs) if rhs else EPS for rhs in by_lhs_final[lhs]]
        lines.append(f"{lhs} -> " + " | ".join(alts))

    result_text = "\n".join(lines)
    return {
        "valid": True,
        "text": result_text,
        "transformations": transformations,
        "changed": bool(transformations),
        "analysis": analyze_grammar(result_text),
    }


# ---------------------------------------------------------------------------
# Input tokenisation for parser studios
# ---------------------------------------------------------------------------


def tokenize_input(g: dict[str, Any], text: str) -> dict[str, Any]:
    """Turn a raw input string into grammar terminals.

    Whitespace-separated input is interpreted literally.  Without whitespace
    the tokenizer uses greedy longest-match over the grammar's terminals, which
    makes inputs like ``id+id*id`` convenient while still deterministic.
    """
    text = text.strip()
    if not text:
        return {"tokens": [], "error": None}
    terminals = sorted(g["terminals"], key=lambda s: (-len(s), s))
    terminal_set = set(g["terminals"])

    # Whitespace always separates tokens; a chunk that is not itself a terminal
    # is split by greedy longest match, so "id + id*id" works as expected.
    tokens: list[str] = []
    offset = 0
    for chunk in text.split():
        offset = text.index(chunk, offset)
        if chunk in terminal_set:
            tokens.append(chunk)
            offset += len(chunk)
            continue
        i = 0
        while i < len(chunk):
            match = next((t for t in terminals if chunk.startswith(t, i)), None)
            if match is None:
                return {
                    "tokens": tokens,
                    "error": (
                        f"Unexpected character '{chunk[i]}' at position {offset + i}. "
                        f"Terminals of this grammar: {', '.join(g['terminals']) or 'none'}."
                    ),
                }
            tokens.append(match)
            i += len(match)
        offset += len(chunk)
    return {"tokens": tokens, "error": None}


# ---------------------------------------------------------------------------
# Left-recursion elimination
# ---------------------------------------------------------------------------


def _fresh_name(base: str, existing: set[str]) -> str:
    name = base + "'"
    while name in existing:
        name += "'"
    existing.add(name)
    return name


def _format_grammar(order: list[str], rules: dict[str, list[list[str]]]) -> str:
    lines = []
    width = max((len(nt) for nt in order), default=1)
    for nt in order:
        alts = rules.get(nt) or []
        if not alts:
            continue
        rendered = " | ".join(" ".join(a) if a else EPS for a in alts)
        lines.append(f"{nt.ljust(width)} -> {rendered}")
    return "\n".join(lines)


def eliminate_left_recursion(text: str) -> dict[str, Any]:
    """Remove direct and indirect left recursion (Aho et al., Algorithm 4.19).

    Non-terminals are processed in order A1..An.  For each Ai we first
    substitute Aj (j < i) into productions Ai -> Aj γ - but only when Aj can
    actually left-derive Ai, so unrelated rules are not needlessly inlined -
    then remove the direct recursion with a fresh primed non-terminal:

        A -> A α | β      becomes      A -> β A'      A' -> α A' | ε
    """
    try:
        g = parse_grammar(text)
    except GrammarError as exc:
        return {"valid": False, "errors": exc.errors}

    order = list(g["nonterminals"])
    rules: dict[str, list[list[str]]] = {nt: [] for nt in order}
    for p in g["productions"]:
        if p["rhs"] not in rules[p["lhs"]]:
            rules[p["lhs"]].append(list(p["rhs"]))
    existing = set(order) | set(g["terminals"])
    steps: list[dict[str, Any]] = []
    warnings: list[str] = []

    nullable, _ = compute_nullable(g)
    if any(nullable[nt] and any(nt in alt[:1] for alts in rules.values() for alt in alts) for nt in order):
        warnings.append(
            "The grammar has nullable non-terminals in left position. The classic algorithm assumes no ε-productions, "
            "so hidden left recursion may remain; check the diagnostics of the result."
        )

    def left_reaches(src: str, target: str) -> bool:
        seen, stack = set(), [src]
        while stack:
            nt = stack.pop()
            if nt == target:
                return True
            if nt in seen:
                continue
            seen.add(nt)
            for alt in rules.get(nt, []):
                if alt and alt[0] in rules:
                    stack.append(alt[0])
        return False

    final_order: list[str] = []
    for i, ai in enumerate(order):
        for aj in order[:i]:
            if not any(alt and alt[0] == aj for alt in rules[ai]):
                continue
            if not left_reaches(aj, ai):
                continue
            new_alts: list[list[str]] = []
            for alt in rules[ai]:
                if alt and alt[0] == aj:
                    for delta in rules[aj]:
                        cand = delta + alt[1:]
                        if cand not in new_alts:
                            new_alts.append(cand)
                else:
                    if alt not in new_alts:
                        new_alts.append(alt)
            steps.append(
                {
                    "kind": "substitute",
                    "nonterminal": ai,
                    "into": aj,
                    "explanation": f"{ai} has alternatives starting with {aj}, and {aj} can left-derive {ai}. "
                    f"Substitute {aj}'s right-hand sides to expose the indirect recursion.",
                    "after": f"{ai} -> " + " | ".join(" ".join(a) if a else EPS for a in new_alts),
                }
            )
            rules[ai] = new_alts

        recursive = [alt[1:] for alt in rules[ai] if alt and alt[0] == ai]
        others = [alt for alt in rules[ai] if not (alt and alt[0] == ai)]
        final_order.append(ai)
        if not recursive:
            continue
        # A -> A (pure self-loop) contributes nothing to the language.
        recursive = [a for a in recursive if a]
        if not others:
            warnings.append(f"{ai} has no non-left-recursive alternative, so it derives no finite string.")
        prime = _fresh_name(ai, existing)
        rules[ai] = [beta + [prime] for beta in others] or [[prime]]
        rules[prime] = [alpha + [prime] for alpha in recursive] + [[]]
        final_order.append(prime)
        steps.append(
            {
                "kind": "direct",
                "nonterminal": ai,
                "newNonterminal": prime,
                "explanation": f"Remove direct left recursion on {ai}: the β alternatives "
                f"({' | '.join(' '.join(b) if b else EPS for b in others) or 'none'}) start {ai}, and the α tails "
                f"({' | '.join(' '.join(a) for a in recursive) or 'none'}) repeat through the new {prime}.",
                "after": f"{ai} -> " + " | ".join(" ".join(a) for a in rules[ai])
                + f"\n{prime} -> " + " | ".join(" ".join(a) if a else EPS for a in rules[prime]),
            }
        )

    result_text = _format_grammar(final_order, rules)
    return {
        "valid": True,
        "text": result_text,
        "steps": steps,
        "warnings": warnings,
        "changed": bool(steps),
        "analysis": analyze_grammar(result_text),
    }


# ---------------------------------------------------------------------------
# Example sentences
# ---------------------------------------------------------------------------


def _shortest_yields(g: dict[str, Any]) -> dict[str, list[str]]:
    """Shortest terminal string each productive non-terminal can derive (fixed point)."""
    best: dict[str, list[str]] = {}
    changed = True
    while changed:
        changed = False
        for p in g["productions"]:
            parts: list[str] = []
            ok = True
            for sym in p["rhs"]:
                if sym in g["nonterminals"]:
                    if sym not in best:
                        ok = False
                        break
                    parts.extend(best[sym])
                else:
                    parts.append(sym)
            if ok and (p["lhs"] not in best or len(parts) < len(best[p["lhs"]])):
                best[p["lhs"]] = parts
                changed = True
    return best


def sample_sentences(g: dict[str, Any], count: int = 4, seed: int = 0, max_len: int = 18) -> list[str]:
    """The shortest sentence plus a few random ones, all derivable from the start symbol."""
    import random

    best = _shortest_yields(g)
    if g["start"] not in best:
        return []
    by_lhs: dict[str, list[list[str]]] = {}
    for p in g["productions"]:
        if all(s not in g["nonterminals"] or s in best for s in p["rhs"]):
            by_lhs.setdefault(p["lhs"], []).append(p["rhs"])
    rng = random.Random(seed)

    def expand(sym: str, depth: int, budget: list[int]) -> list[str]:
        if sym not in g["nonterminals"]:
            budget[0] -= 1
            return [sym]
        if depth > 5 or budget[0] <= len(best[sym]):
            out = list(best[sym])  # head for termination
            budget[0] -= len(out)
            return out
        rhs = rng.choice(by_lhs[sym])
        out: list[str] = []
        for s in rhs:
            out.extend(expand(s, depth + 1, budget))
        return out

    results: list[str] = []
    shortest = " ".join(best[g["start"]])
    results.append(shortest)
    for _ in range(count * 6):
        if len(results) >= count:
            break
        sentence = " ".join(expand(g["start"], 0, [max_len]))
        if sentence not in results and len(sentence.split()) <= max_len + 4:
            results.append(sentence)
    return results
