"""Canonical LR(1) and LALR(1) automata, tables, and a parser-class comparison.

Both methods produce the same table shape as the SLR studio, so the shift /
reduce simulator in :mod:`slr` drives all three bottom-up parsers.

* Canonical LR(1): items carry one lookahead terminal, [A → α·β, a].  The
  closure adds [B → ·γ, b] for every b in FIRST(β a).  A completed item reduces
  only on its own lookahead, which is more precise than SLR's FOLLOW(A).
* LALR(1): LR(1) states with the same core (the same LR(0) items) are merged
  and their lookaheads united.  This gives the LR(0) state count with almost
  all of LR(1)'s precision; merging can only introduce reduce/reduce conflicts.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from .grammar import EOF, EPS, analyze_grammar, first_of_sequence, tokenize_input
from .ll1 import build_table as build_ll1_table
from .slr import _augment, build_automaton, build_slr_table, item_text, simulate

_MAX_STATES = 700

Item = tuple[int, int, str]  # (production index, dot position, lookahead)


def _closure(
    seed: set[Item],
    prods: list[dict[str, Any]],
    by_lhs: dict[str, list[int]],
    nts: set[str],
    first: dict[str, set[str]],
    nullable: dict[str, bool],
) -> frozenset[Item]:
    result = set(seed)
    queue = deque(seed)
    while queue:
        pi, dot, la = queue.popleft()
        rhs = prods[pi]["rhs"]
        if dot >= len(rhs) or rhs[dot] not in nts:
            continue
        lookaheads = first_of_sequence(list(rhs[dot + 1 :]) + [la], first, nullable)
        lookaheads.discard(EPS)
        for q in by_lhs.get(rhs[dot], []):
            for b in lookaheads:
                item = (q, 0, b)
                if item not in result:
                    result.add(item)
                    queue.append(item)
    return frozenset(result)


def _core(items: frozenset[Item]) -> frozenset[tuple[int, int]]:
    return frozenset((pi, dot) for pi, dot, _ in items)


def build_lr1_automaton(analysis: dict[str, Any], method: str = "lr1") -> dict[str, Any]:
    g = analysis["grammar"]
    aug = _augment(g)
    prods = aug["productions"]
    aug_index = aug["production"]["index"]
    nts = set(g["nonterminals"]) | {aug["name"]}
    by_lhs: dict[str, list[int]] = {}
    for p in prods:
        by_lhs.setdefault(p["lhs"], []).append(p["index"])
    first = {nt: set(v) for nt, v in analysis["first"].items()}
    nullable = analysis["nullable"]
    symbols = list(g["terminals"]) + list(g["nonterminals"])

    start = _closure({(aug_index, 0, EOF)}, prods, by_lhs, nts, first, nullable)
    states: list[frozenset[Item]] = [start]
    index: dict[frozenset[Item], int] = {start: 0}
    transitions: list[dict[str, Any]] = []
    queue: deque[int] = deque([0])
    while queue:
        si = queue.popleft()
        items = states[si]
        for sym in symbols:
            moved = {
                (pi, dot + 1, la)
                for pi, dot, la in items
                if dot < len(prods[pi]["rhs"]) and prods[pi]["rhs"][dot] == sym
            }
            if not moved:
                continue
            target = _closure(moved, prods, by_lhs, nts, first, nullable)
            if target not in index:
                if len(states) >= _MAX_STATES:
                    raise ValueError(
                        f"The canonical LR(1) automaton exceeded {_MAX_STATES} states. Try LALR(1) or simplify the grammar."
                    )
                index[target] = len(states)
                states.append(target)
                queue.append(len(states) - 1)
            transitions.append({"from": si, "symbol": sym, "to": index[target]})

    lr1_count = len(states)
    merged_from: list[list[int]] = [[i] for i in range(len(states))]
    if method == "lalr":
        core_index: dict[frozenset[tuple[int, int]], int] = {}
        mapping: dict[int, int] = {}
        merged: list[set[Item]] = []
        merged_from = []
        for si, items in enumerate(states):
            core = _core(items)
            if core not in core_index:
                core_index[core] = len(merged)
                merged.append(set())
                merged_from.append([])
            mi = core_index[core]
            mapping[si] = mi
            merged[mi] |= items
            merged_from[mi].append(si)
        states = [frozenset(m) for m in merged]
        seen: set[tuple[int, str]] = set()
        new_transitions = []
        for t in transitions:
            key = (mapping[t["from"]], t["symbol"])
            if key not in seen:
                seen.add(key)
                new_transitions.append({"from": key[0], "symbol": t["symbol"], "to": mapping[t["to"]]})
        transitions = new_transitions

    state_json = []
    for si, items in enumerate(states):
        grouped: dict[tuple[int, int], set[str]] = {}
        for pi, dot, la in items:
            grouped.setdefault((pi, dot), set()).add(la)
        rendered = []
        for (pi, dot), las in sorted(grouped.items()):
            p = prods[pi]
            ordered = sorted(las, key=lambda a: (a == EOF, a))
            rendered.append(
                {
                    "production": pi,
                    "dot": dot,
                    "lhs": p["lhs"],
                    "rhs": p["rhs"],
                    "lookaheads": ordered,
                    "text": f"{item_text(p, dot)} , {' / '.join(ordered)}",
                    "complete": dot == len(p["rhs"]),
                }
            )
        state_json.append(
            {
                "id": si,
                "items": rendered,
                "start": si == 0,
                "mergedFrom": merged_from[si] if method == "lalr" else None,
            }
        )
    return {
        "method": method,
        "augmented": aug["production"],
        "augmentedName": aug["name"],
        "states": state_json,
        "transitions": transitions,
        "start": 0,
        "productions": prods,
        "lr1States": lr1_count,
    }


def build_lr1_table(analysis: dict[str, Any], automaton: dict[str, Any]) -> dict[str, Any]:
    g = analysis["grammar"]
    prods = automaton["productions"]
    aug = automaton["augmented"]
    terminals = list(g["terminals"]) + [EOF]
    terminal_set = set(g["terminals"])
    trans = {(t["from"], t["symbol"]): t["to"] for t in automaton["transitions"]}
    label = "LALR(1)" if automaton["method"] == "lalr" else "LR(1)"

    raw: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for state in automaton["states"]:
        si = state["id"]
        for item in state["items"]:
            p = prods[item["production"]]
            dot = item["dot"]
            if dot < len(p["rhs"]):
                sym = p["rhs"][dot]
                target = trans.get((si, sym))
                if sym in terminal_set and target is not None:
                    raw.setdefault((si, sym), []).append(
                        {
                            "type": "shift",
                            "target": target,
                            "production": None,
                            "item": item["text"],
                            "reason": f"In state {si}, item [{item['text']}] calls for shifting {sym} and moving to state {target}.",
                        }
                    )
            elif item["production"] == aug["index"]:
                raw.setdefault((si, EOF), []).append(
                    {
                        "type": "accept",
                        "target": None,
                        "production": None,
                        "item": item["text"],
                        "reason": "The augmented start item is complete with lookahead $, so the input is accepted.",
                    }
                )
            else:
                for a in item["lookaheads"]:
                    raw.setdefault((si, a), []).append(
                        {
                            "type": "reduce",
                            "target": None,
                            "production": item["production"],
                            "item": item["text"],
                            "reason": (
                                f"In state {si}, [{item['text']}] is complete and {a} is one of its {label} lookaheads, "
                                f"so reduce by {p['text']}. (SLR would use all of FOLLOW({p['lhs']}).)"
                            ),
                        }
                    )

    conflicts: list[dict[str, Any]] = []
    rows = []
    for state in automaton["states"]:
        si = state["id"]
        cells = []
        for t in terminals:
            deduped: list[dict[str, Any]] = []
            seen = set()
            for a in raw.get((si, t), []):
                key = (a["type"], a["target"], a["production"])
                if key not in seen:
                    seen.add(key)
                    deduped.append(a)
            if len(deduped) > 1:
                kinds = {a["type"] for a in deduped}
                ctype = "shift/reduce" if kinds == {"shift", "reduce"} else "reduce/reduce" if kinds == {"reduce"} else "conflict"
                merged = state.get("mergedFrom") or []
                conflicts.append(
                    {
                        "state": si,
                        "terminal": t,
                        "type": ctype,
                        "actions": deduped,
                        "items": [a["item"] for a in deduped],
                        "reason": (
                            f"State {si} has {len(deduped)} competing actions on '{t}' ({', '.join(sorted(kinds))}). "
                            + (
                                f"It was formed by merging LR(1) states {', '.join(map(str, merged))}, whose lookaheads collided."
                                if len(merged) > 1 and ctype == "reduce/reduce"
                                else f"{label} cannot choose deterministically."
                            )
                        ),
                    }
                )
            cells.append({"column": t, "action": deduped[0] if deduped else None, "actions": deduped, "conflict": len(deduped) > 1})
        gotos = [{"column": nt, "target": trans.get((si, nt))} for nt in g["nonterminals"]]
        rows.append({"state": si, "cells": cells, "gotos": gotos})
    return {"terminals": terminals, "rows": rows, "conflicts": conflicts, "isSLR": not conflicts, "deterministic": not conflicts}


def analyze_lr(grammar_text: str, input_text: str = "", method: str = "lalr") -> dict[str, Any]:
    method = (method or "lalr").lower()
    if method == "slr":
        from .slr import analyze_slr

        return analyze_slr(grammar_text, input_text)
    if method not in ("lalr", "lr1"):
        return {"valid": False, "errors": [{"line": 0, "message": f"Unknown LR method '{method}'. Use slr, lalr or lr1."}], "stage": "method"}
    analysis = analyze_grammar(grammar_text)
    if not analysis["valid"]:
        return {"valid": False, "errors": analysis["errors"], "stage": "grammar"}
    try:
        automaton = build_lr1_automaton(analysis, method)
    except ValueError as exc:
        return {"valid": False, "errors": [{"line": 0, "message": str(exc)}], "stage": "automaton"}
    table = build_lr1_table(analysis, automaton)
    label = "LALR(1)" if method == "lalr" else "LR(1)"
    result: dict[str, Any] = {
        "valid": True,
        "method": method,
        "grammar": analysis["grammar"],
        "first": analysis["first"],
        "follow": analysis["follow"],
        "nullable": analysis["nullable"],
        "issues": analysis["issues"],
        "automaton": automaton,
        "table": table,
        "isSLR": table["deterministic"],
        "deterministic": table["deterministic"],
        "conflicts": table["conflicts"],
        "stats": {
            "states": len(automaton["states"]),
            "lr1States": automaton["lr1States"],
            "transitions": len(automaton["transitions"]),
            "items": sum(len(s["items"]) for s in automaton["states"]),
            "conflicts": len(table["conflicts"]),
        },
        "simulation": None,
    }
    if input_text and input_text.strip():
        tok = tokenize_input(analysis["grammar"], input_text)
        result["tokenError"] = tok["error"]
        if tok["error"] is None:
            sim = simulate(analysis, automaton, table, tok["tokens"], input_text)
            if not sim.get("canParse", True):
                sim["reason"] = f"The {label} table contains conflicts, so deterministic simulation is disabled. Inspect the conflicting states to see why."
            result["simulation"] = sim
    return result


def classify_grammar(grammar_text: str) -> dict[str, Any]:
    """Check one grammar against LL(1), SLR(1), LALR(1) and LR(1) side by side."""
    analysis = analyze_grammar(grammar_text)
    if not analysis["valid"]:
        return {"valid": False, "errors": analysis["errors"]}
    classes: list[dict[str, Any]] = []
    ll = build_ll1_table(analysis)
    classes.append({"id": "ll1", "label": "LL(1)", "ok": ll["isLL1"], "conflicts": len(ll["conflicts"]), "states": None})
    try:
        lr0 = build_automaton(analysis)
        slr = build_slr_table(analysis, lr0)
        classes.append({"id": "slr", "label": "SLR(1)", "ok": slr["isSLR"], "conflicts": len(slr["conflicts"]), "states": len(lr0["states"])})
    except ValueError:
        classes.append({"id": "slr", "label": "SLR(1)", "ok": None, "conflicts": None, "states": None})
    for method, label in (("lalr", "LALR(1)"), ("lr1", "LR(1)")):
        try:
            auto = build_lr1_automaton(analysis, method)
            table = build_lr1_table(analysis, auto)
            classes.append({"id": method, "label": label, "ok": table["deterministic"], "conflicts": len(table["conflicts"]), "states": len(auto["states"])})
        except ValueError:
            classes.append({"id": method, "label": label, "ok": None, "conflicts": None, "states": None})

    ok = {c["id"]: c["ok"] for c in classes}
    if ok.get("ll1"):
        verdict = "LL(1), and therefore also SLR-friendly in practice: every parser here works."
        if not ok.get("slr"):
            verdict = "LL(1) but not SLR(1). Rare but possible: FOLLOW sets are too coarse for SLR even though one lookahead suffices top-down."
    elif ok.get("slr"):
        verdict = "Not LL(1), but SLR(1): bottom-up parsing handles it (e.g. left recursion) with the smallest LR table."
    elif ok.get("lalr"):
        verdict = "LALR(1) but not SLR(1): SLR's FOLLOW-based lookaheads cause a conflict that the precise LR(1) lookaheads avoid. This is why tools like yacc and bison use LALR."
    elif ok.get("lr1"):
        verdict = "LR(1) but not LALR(1): merging LR(1) states with equal cores creates a reduce/reduce conflict. Only the full canonical LR(1) parser works."
    else:
        verdict = "Not LR(1). The grammar is probably ambiguous; no deterministic one-token-lookahead parser exists for it as written."
    return {"valid": True, "classes": classes, "verdict": verdict}
