"""LR(0) item construction and SLR(1) parsing tables / simulation."""

from __future__ import annotations

from collections import deque
from typing import Any

from .grammar import EOF, EPS, analyze_grammar, tokenize_input
from .trees import TreeBuilder, derivations

_MAX_STATES = 260
_MAX_STEPS = 1500
_DOT = "\u00b7"


def _augment(g: dict[str, Any]) -> dict[str, Any]:
    base = g["start"] + "\u2032"
    name = base
    n = 2
    while name in g["nonterminals"]:
        name = f"{base}{n}"
        n += 1
    aug = {
        "index": len(g["productions"]),
        "lhs": name,
        "rhs": [g["start"]],
        "line": 0,
        "text": f"{name} \u2192 {g['start']}",
        "augmented": True,
    }
    return {"name": name, "production": aug, "productions": g["productions"] + [aug]}


def item_text(production: dict[str, Any], dot: int) -> str:
    rhs = list(production["rhs"])
    rhs.insert(dot, _DOT)
    return f"{production['lhs']} \u2192 {' '.join(rhs)}"


def _closure(
    seed: set[tuple[int, int]],
    prods: list[dict[str, Any]],
    by_lhs: dict[str, list[int]],
    nts: set[str],
) -> set[tuple[int, int]]:
    result = set(seed)
    queue = deque(seed)
    while queue:
        pi, dot = queue.popleft()
        rhs = prods[pi]["rhs"]
        if dot < len(rhs):
            sym = rhs[dot]
            if sym in nts:
                for q in by_lhs.get(sym, []):
                    item = (q, 0)
                    if item not in result:
                        result.add(item)
                        queue.append(item)
    return result


def _goto(
    items: set[tuple[int, int]],
    symbol: str,
    prods: list[dict[str, Any]],
    by_lhs: dict[str, list[int]],
    nts: set[str],
) -> set[tuple[int, int]]:
    moved = {(pi, dot + 1) for (pi, dot) in items if dot < len(prods[pi]["rhs"]) and prods[pi]["rhs"][dot] == symbol}
    if not moved:
        return set()
    return _closure(moved, prods, by_lhs, nts)


def build_automaton(analysis: dict[str, Any]) -> dict[str, Any]:
    g = analysis["grammar"]
    aug = _augment(g)
    prods = aug["productions"]
    aug_index = aug["production"]["index"]
    nts = set(g["nonterminals"]) | {aug["name"]}
    by_lhs: dict[str, list[int]] = {}
    for p in prods:
        by_lhs.setdefault(p["lhs"], []).append(p["index"])

    start_items = _closure({(aug_index, 0)}, prods, by_lhs, nts)
    states: list[set[tuple[int, int]]] = [start_items]
    index: dict[frozenset[tuple[int, int]], int] = {frozenset(start_items): 0}
    transitions: list[dict[str, Any]] = []
    queue: deque[int] = deque([0])
    symbols = list(g["terminals"]) + list(g["nonterminals"]) + [aug["name"]]

    while queue:
        si = queue.popleft()
        items = states[si]
        present: set[str] = set()
        for pi, dot in items:
            rhs = prods[pi]["rhs"]
            if dot < len(rhs):
                present.add(rhs[dot])
        for sym in symbols:
            if sym not in present:
                continue
            target = _goto(items, sym, prods, by_lhs, nts)
            if not target:
                continue
            key = frozenset(target)
            if key not in index:
                if len(states) >= _MAX_STATES:
                    raise ValueError("LR(0) automaton exceeded the state limit. Simplify the grammar.")
                index[key] = len(states)
                states.append(target)
                queue.append(len(states) - 1)
            transitions.append({"from": si, "symbol": sym, "to": index[key]})

    state_json = []
    for si, items in enumerate(states):
        rendered = []
        for pi, dot in sorted(items, key=lambda x: (prods[x[0]]["index"], x[1])):
            p = prods[pi]
            rendered.append(
                {
                    "production": pi,
                    "dot": dot,
                    "lhs": p["lhs"],
                    "rhs": p["rhs"],
                    "text": item_text(p, dot),
                    "complete": dot == len(p["rhs"]),
                }
            )
        state_json.append({"id": si, "items": rendered, "start": si == 0})
    return {
        "augmented": aug["production"],
        "augmentedName": aug["name"],
        "states": state_json,
        "transitions": transitions,
        "start": 0,
        "productions": prods,
    }


def build_slr_table(analysis: dict[str, Any], automaton: dict[str, Any]) -> dict[str, Any]:
    g = analysis["grammar"]
    prods = automaton["productions"]
    aug = automaton["augmented"]
    follow = {nt: set(v) for nt, v in analysis["follow"].items()}
    terminals = list(g["terminals"]) + [EOF]
    trans = {(t["from"], t["symbol"]): t["to"] for t in automaton["transitions"]}

    raw: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for state in automaton["states"]:
        si = state["id"]
        for item in state["items"]:
            pi = item["production"]
            p = prods[pi]
            dot = item["dot"]
            if dot < len(p["rhs"]):
                sym = p["rhs"][dot]
                if sym in terminals and sym != EOF:
                    target = trans.get((si, sym))
                    if target is not None:
                        action = {
                            "type": "shift",
                            "target": target,
                            "production": None,
                            "item": item["text"],
                            "reason": f"In state {si}, item {item['text']} calls for shifting {sym} and moving to state {target}.",
                        }
                        raw.setdefault((si, sym), []).append(action)
            else:
                if pi == aug["index"]:
                    action = {
                        "type": "accept",
                        "target": None,
                        "production": None,
                        "item": item["text"],
                        "reason": "The augmented start item is complete on $, so the input is accepted.",
                    }
                    raw.setdefault((si, EOF), []).append(action)
                else:
                    for a in sorted(follow[p["lhs"]]):
                        action = {
                            "type": "reduce",
                            "target": None,
                            "production": pi,
                            "item": item["text"],
                            "reason": f"In state {si}, {item['text']} is complete and {a} \u2208 FOLLOW({p['lhs']}), so reduce by {p['text']}.",
                        }
                        raw.setdefault((si, a), []).append(action)

    conflicts: list[dict[str, Any]] = []
    rows = []
    for state in automaton["states"]:
        si = state["id"]
        cells = []
        for t in terminals:
            actions = raw.get((si, t), [])
            deduped: list[dict[str, Any]] = []
            seen = set()
            for a in actions:
                key = (a["type"], a["target"], a["production"])
                if key not in seen:
                    seen.add(key)
                    deduped.append(a)
            if len(deduped) > 1:
                kinds = {a["type"] for a in deduped}
                if kinds == {"shift", "reduce"}:
                    ctype = "shift/reduce"
                elif kinds == {"reduce"}:
                    ctype = "reduce/reduce"
                else:
                    ctype = "conflict"
                conflicts.append(
                    {
                        "state": si,
                        "terminal": t,
                        "type": ctype,
                        "actions": deduped,
                        "items": [a["item"] for a in deduped],
                        "reason": (
                            f"State {si} has {len(deduped)} competing actions on '{t}' "
                            f"({', '.join(sorted(kinds))}). SLR(1) cannot choose deterministically."
                        ),
                    }
                )
            cells.append(
                {
                    "column": t,
                    "action": deduped[0] if deduped else None,
                    "actions": deduped,
                    "conflict": len(deduped) > 1,
                }
            )
        gotos = []
        for nt in g["nonterminals"]:
            target = trans.get((si, nt))
            gotos.append({"column": nt, "target": target})
        rows.append({"state": si, "cells": cells, "gotos": gotos})

    return {
        "terminals": terminals,
        "rows": rows,
        "conflicts": conflicts,
        "isSLR": len(conflicts) == 0,
    }


def _table_action(table: dict[str, Any], state: int, terminal: str) -> dict[str, Any] | None:
    for row in table["rows"]:
        if row["state"] == state:
            for cell in row["cells"]:
                if cell["column"] == terminal:
                    return cell["action"]
    return None


def _goto_target(table: dict[str, Any], state: int, nt: str) -> int | None:
    for row in table["rows"]:
        if row["state"] == state:
            for cell in row["gotos"]:
                if cell["column"] == nt:
                    return cell["target"]
    return None


def _expected(table: dict[str, Any], state: int) -> list[str]:
    for row in table["rows"]:
        if row["state"] == state:
            return [c["column"] for c in row["cells"] if c["action"] is not None]
    return []


def simulate(
    analysis: dict[str, Any],
    automaton: dict[str, Any],
    table: dict[str, Any],
    tokens: list[str],
    input_text: str = "",
) -> dict[str, Any]:
    prods = {p["index"]: p for p in automaton["productions"]}
    stream = list(tokens) + [EOF]
    if table["conflicts"]:
        return {
            "canParse": False,
            "reason": "The SLR table contains conflicts, so deterministic simulation is disabled. Inspect the conflicting states to see why.",
            "accepted": False,
            "tokens": list(tokens),
            "steps": [],
            "tree": None,
            "derivations": {"leftmost": {"forms": [], "rules": []}, "rightmost": {"forms": [], "rules": []}},
            "nodeCreatedAt": {},
        }

    builder = TreeBuilder()
    state_stack = [0]
    symbol_stack: list[str] = []
    node_stack: list[int] = []
    i = 0
    steps: list[dict[str, Any]] = []
    accepted = False
    error: str | None = None
    node_created_at: dict[int, int] = {}

    while len(steps) < _MAX_STEPS:
        state = state_stack[-1]
        lookahead = stream[i] if i < len(stream) else EOF
        action = _table_action(table, state, lookahead)
        snapshot_states = list(state_stack)
        snapshot_symbols = list(symbol_stack)

        if action is None:
            expected = _expected(table, state)
            error = (
                f"In state {state}, lookahead '{lookahead}' has no ACTION entry. "
                + (f"Expected one of: {', '.join(expected)}." if expected else "The state expects no terminals.")
            )
            steps.append(
                {
                    "index": len(steps),
                    "stateStack": snapshot_states,
                    "symbolStack": snapshot_symbols,
                    "input": stream[i:],
                    "lookahead": lookahead,
                    "state": state,
                    "action": {"type": "error"},
                    "production": None,
                    "created": [],
                    "nodeId": None,
                    "explanation": error,
                    "tableCell": {"state": state, "terminal": lookahead},
                }
            )
            break

        if action["type"] == "shift":
            nid = builder.create(lookahead, True, len(steps))
            node_created_at[nid] = len(steps)
            node_stack.append(nid)
            state_stack.append(action["target"])
            symbol_stack.append(lookahead)
            steps.append(
                {
                    "index": len(steps),
                    "stateStack": snapshot_states,
                    "symbolStack": snapshot_symbols,
                    "input": stream[i:],
                    "lookahead": lookahead,
                    "state": state,
                    "action": action,
                    "production": None,
                    "created": [nid],
                    "nodeId": nid,
                    "explanation": f"Shift '{lookahead}' and enter state {action['target']}.",
                    "tableCell": {"state": state, "terminal": lookahead},
                }
            )
            i += 1
            continue

        if action["type"] == "reduce":
            prod = prods[action["production"]]
            count = len(prod["rhs"])
            if count > len(state_stack) - 1:
                error = f"Reduce by {prod['text']} would pop more states than the stack contains."
                break
            if count:
                children = node_stack[-count:]
                node_stack = node_stack[:-count]
                state_stack = state_stack[:-count]
                symbol_stack = symbol_stack[:-count]
            else:
                children = []
            new_node = builder.reduce_node(prod["lhs"], children, prod, len(steps))
            node_created_at[new_node] = len(steps)
            node_stack.append(new_node)
            goto_state = _goto_target(table, state_stack[-1], prod["lhs"])
            if goto_state is None:
                error = f"No GOTO entry for [{state_stack[-1]}, {prod['lhs']}] after reducing by {prod['text']}."
                steps.append(
                    {
                        "index": len(steps),
                        "stateStack": snapshot_states,
                        "symbolStack": snapshot_symbols,
                        "input": stream[i:],
                        "lookahead": lookahead,
                        "state": state,
                        "action": action,
                        "production": prod,
                        "created": [new_node],
                        "nodeId": new_node,
                        "explanation": error,
                        "tableCell": {"state": state, "terminal": lookahead},
                    }
                )
                break
            state_stack.append(goto_state)
            symbol_stack.append(prod["lhs"])
            steps.append(
                {
                    "index": len(steps),
                    "stateStack": snapshot_states,
                    "symbolStack": snapshot_symbols,
                    "input": stream[i:],
                    "lookahead": lookahead,
                    "state": state,
                    "action": {**action, "goto": goto_state},
                    "production": prod,
                    "created": [new_node],
                    "nodeId": new_node,
                    "explanation": (
                        f"Reduce by {prod['text']}: pop {count} state{'s' if count != 1 else ''}, "
                        f"create a {prod['lhs']} node, then GOTO[{state_stack[-2] if len(state_stack) > 1 else 0}, {prod['lhs']}] = {goto_state}."
                    ),
                    "tableCell": {"state": state, "terminal": lookahead},
                }
            )
            continue

        if action["type"] == "accept":
            accepted = True
            steps.append(
                {
                    "index": len(steps),
                    "stateStack": snapshot_states,
                    "symbolStack": snapshot_symbols,
                    "input": stream[i:],
                    "lookahead": lookahead,
                    "state": state,
                    "action": action,
                    "production": None,
                    "created": [],
                    "nodeId": None,
                    "explanation": "ACTION[state, $] = accept. The LR(0) automaton has reduced the entire input to the start symbol.",
                    "tableCell": {"state": state, "terminal": lookahead},
                }
            )
            break

    if len(steps) >= _MAX_STEPS and not accepted:
        error = "Step limit reached; the parse did not terminate."

    root_id = node_stack[-1] if node_stack else None
    tree = builder.nested(root_id) if root_id is not None else None
    return {
        "canParse": True,
        "accepted": accepted,
        "error": error,
        "tokens": list(tokens),
        "input": input_text,
        "steps": steps,
        "tree": tree,
        "derivations": derivations(tree),
        "nodeCreatedAt": node_created_at,
        "stateStackFinal": state_stack,
    }


def analyze_slr(grammar_text: str, input_text: str = "") -> dict[str, Any]:
    analysis = analyze_grammar(grammar_text)
    if not analysis["valid"]:
        return {"valid": False, "errors": analysis["errors"], "stage": "grammar"}
    try:
        automaton = build_automaton(analysis)
    except ValueError as exc:
        return {"valid": False, "errors": [{"line": 0, "message": str(exc)}], "stage": "automaton"}
    table = build_slr_table(analysis, automaton)
    result: dict[str, Any] = {
        "valid": True,
        "grammar": analysis["grammar"],
        "first": analysis["first"],
        "follow": analysis["follow"],
        "nullable": analysis["nullable"],
        "issues": analysis["issues"],
        "automaton": automaton,
        "table": table,
        "isSLR": table["isSLR"],
        "deterministic": table["isSLR"],
        "method": "slr",
        "conflicts": table["conflicts"],
        "stats": {
            "states": len(automaton["states"]),
            "transitions": len(automaton["transitions"]),
            "items": sum(len(s["items"]) for s in automaton["states"]),
            "conflicts": len(table["conflicts"]),
        },
    }
    if input_text is not None and input_text.strip():
        tok = tokenize_input(analysis["grammar"], input_text)
        result["tokenError"] = tok["error"]
        if tok["error"] is None:
            result["simulation"] = simulate(analysis, automaton, table, tok["tokens"], input_text)
        else:
            result["simulation"] = None
    else:
        result["simulation"] = None
    return result
