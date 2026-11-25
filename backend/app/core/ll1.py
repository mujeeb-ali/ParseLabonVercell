"""LL(1) parsing-table construction and predictive parsing simulation."""

from __future__ import annotations

from typing import Any

from .grammar import EOF, EPS, first_of_sequence, tokenize_input
from .trees import TreeBuilder, derivations

_MAX_STEPS = 1200


def build_table(analysis: dict[str, Any]) -> dict[str, Any]:
    g = analysis["grammar"]
    first = {nt: set(v) for nt, v in analysis["first"].items()}
    follow = {nt: set(v) for nt, v in analysis["follow"].items()}
    nullable = analysis["nullable"]
    columns = list(g["terminals"]) + [EOF]

    cells: dict[str, dict[str, dict[str, Any]]] = {
        nt: {} for nt in g["nonterminals"]
    }
    conflicts: list[dict[str, Any]] = []

    for p in g["productions"]:
        first_alpha = first_of_sequence(p["rhs"], first, nullable)
        targets: list[tuple[str, str]] = []
        for sym in sorted(first_alpha):
            if sym != EPS:
                targets.append((sym, f"FIRST({p['text'].split('→', 1)[1].strip() if '→' in p['text'] else ' '.join(p['rhs'])}) contains {sym}."))
        if EPS in first_alpha:
            for sym in sorted(follow[p["lhs"]]):
                targets.append(
                    (
                        sym,
                        f"The right side of {p['text']} is nullable, and {sym} is in FOLLOW({p['lhs']}).",
                    )
                )
        for sym, reason in targets:
            cell = cells[p["lhs"]].get(sym)
            if cell is None:
                cells[p["lhs"]][sym] = {
                    "production": p["index"],
                    "productions": [p["index"]],
                    "reason": reason,
                }
            elif p["index"] not in cell["productions"]:
                cell["productions"].append(p["index"])
                cell["conflicts"] = cell.get("conflicts", []) + [p["index"]]
                conflicts.append(
                    {
                        "nonterminal": p["lhs"],
                        "terminal": sym,
                        "productions": list(cell["productions"]),
                        "reason": (
                            f"Both {g['productions'][cell['productions'][0]]['text']} and {p['text']} can be selected "
                            f"when {p['lhs']} sees {sym}."
                        ),
                    }
                )

    rows = []
    for nt in g["nonterminals"]:
        row_cells = []
        for col in columns:
            cell = cells[nt].get(col)
            if cell is None:
                row_cells.append({"column": col, "production": None, "productions": [], "reason": None})
            else:
                row_cells.append(
                    {
                        "column": col,
                        "production": cell["production"],
                        "productions": cell["productions"],
                        "reason": cell["reason"],
                        "conflict": len(cell["productions"]) > 1,
                    }
                )
        rows.append({"nonterminal": nt, "cells": row_cells})

    return {
        "columns": columns,
        "rows": rows,
        "conflicts": conflicts,
        "isLL1": len(conflicts) == 0,
    }


def _row_for(table: dict[str, Any], nt: str) -> dict[str, Any] | None:
    return next((row for row in table["rows"] if row["nonterminal"] == nt), None)


def _cell_for(table: dict[str, Any], nt: str, terminal: str) -> dict[str, Any] | None:
    for row in table["rows"]:
        if row["nonterminal"] == nt:
            for cell in row["cells"]:
                if cell["column"] == terminal:
                    return cell
    return None


def simulate(
    analysis: dict[str, Any],
    table: dict[str, Any],
    tokens: list[str],
    input_text: str = "",
) -> dict[str, Any]:
    g = analysis["grammar"]
    productions = {p["index"]: p for p in g["productions"]}
    is_terminal = lambda sym: sym not in g["nonterminals"] and sym != EOF
    tokens = list(tokens)
    stream = tokens + [EOF]

    if table["conflicts"]:
        return {
            "canParse": False,
            "reason": "The table contains LL(1) conflicts, so a deterministic predictive parser cannot be built. Resolve the conflicts or use the SLR studio.",
            "accepted": False,
            "tokens": tokens,
            "steps": [],
            "tree": None,
            "derivations": {"leftmost": {"forms": [], "rules": []}, "rightmost": {"forms": [], "rules": []}},
            "nodeCreatedAt": {},
        }

    builder = TreeBuilder()
    root = builder.create(g["start"], False, 0)
    stack: list[dict[str, Any]] = [{"symbol": EOF, "node": None}, {"symbol": g["start"], "node": root}]
    i = 0
    steps: list[dict[str, Any]] = []
    accepted = False
    error: str | None = None
    node_created_at = {0: 0}

    def snapshot() -> list[dict[str, Any]]:
        return [{"symbol": s["symbol"], "node": s["node"]} for s in reversed(stack)]

    while len(steps) < _MAX_STEPS:
        lookahead = stream[i] if i < len(stream) else EOF
        if not stack:
            error = "The parse stack is empty before the input was consumed."
            steps.append(
                {
                    "index": len(steps),
                    "stack": [],
                    "input": stream[i:],
                    "lookahead": lookahead,
                    "action": "error",
                    "production": None,
                    "nodeId": None,
                    "created": [],
                    "explanation": error,
                    "tableCell": None,
                }
            )
            break
        top = stack[-1]
        symbol = top["symbol"]

        if symbol == EOF and lookahead == EOF:
            accepted = True
            steps.append(
                {
                    "index": len(steps),
                    "stack": snapshot(),
                    "input": stream[i:],
                    "lookahead": EOF,
                    "action": "accept",
                    "production": None,
                    "nodeId": None,
                    "created": [],
                    "consumed": i,
                    "explanation": "The stack and the remaining input both contain $. The token stream is a sentence of the grammar.",
                    "tableCell": None,
                }
            )
            break

        if is_terminal(symbol):
            if symbol == lookahead:
                if top["node"] is not None:
                    builder.nodes[top["node"]]["matchedStep"] = len(steps)
                steps.append(
                    {
                        "index": len(steps),
                        "stack": snapshot(),
                        "input": stream[i:],
                        "lookahead": lookahead,
                        "action": "match",
                        "production": None,
                        "nodeId": top["node"],
                        "created": [],
                        "consumed": i,
                        "explanation": f"Match terminal '{symbol}' against the lookahead and consume it.",
                        "tableCell": None,
                    }
                )
                stack.pop()
                i += 1
                continue
            error = f"Expected '{symbol}' on top of the stack but the lookahead is '{lookahead}'."
            steps.append(
                {
                    "index": len(steps),
                    "stack": snapshot(),
                    "input": stream[i:],
                    "lookahead": lookahead,
                    "action": "error",
                    "production": None,
                    "nodeId": top["node"],
                    "created": [],
                    "consumed": i,
                    "explanation": error,
                    "tableCell": None,
                }
            )
            break

        if symbol == EOF:
            error = (
                f"The stack is down to $ but input remains, starting at '{lookahead}'. "
                f"The start symbol derived a complete sentence too early; the extra tokens are not part of it."
            )
            steps.append(
                {
                    "index": len(steps),
                    "stack": snapshot(),
                    "input": stream[i:],
                    "lookahead": lookahead,
                    "action": "error",
                    "production": None,
                    "nodeId": None,
                    "created": [],
                    "consumed": i,
                    "explanation": error,
                    "tableCell": None,
                }
            )
            break

        cell = _cell_for(table, symbol, lookahead)
        if cell is None or cell["production"] is None:
            expected = [c["column"] for c in (_row_for(table, symbol) or {}).get("cells", []) if c["production"] is not None]
            error = (
                f"No LL(1) table entry for [{symbol}, {lookahead}]. "
                f"The parser cannot decide how to expand {symbol} when it sees {lookahead}."
                + (f" Expected one of: {', '.join(expected)}." if expected else "")
            )
            steps.append(
                {
                    "index": len(steps),
                    "stack": snapshot(),
                    "input": stream[i:],
                    "lookahead": lookahead,
                    "action": "error",
                    "production": None,
                    "nodeId": top["node"],
                    "created": [],
                    "consumed": i,
                    "explanation": error,
                    "tableCell": {"nonterminal": symbol, "terminal": lookahead},
                }
            )
            break

        prod = productions[cell["production"]]
        stack.pop()
        created = builder.expand(top["node"], prod, len(steps), is_terminal)
        for cid in created:
            node_created_at[cid] = len(steps)
        for child in reversed(created):
            stack.append({"symbol": builder.nodes[child]["symbol"], "node": child})
        rhs = " ".join(prod["rhs"]) if prod["rhs"] else EPS
        steps.append(
            {
                "index": len(steps),
                "stack": snapshot(),
                "input": stream[i:],
                "lookahead": lookahead,
                "action": "expand",
                "production": prod,
                "nodeId": top["node"],
                "created": created,
                "consumed": i,
                "explanation": (
                    f"Table[{symbol}, {lookahead}] selects {prod['text']}. "
                    f"Replace {symbol} with {rhs} on the stack"
                    + (f" and create {len(created)} child node{'s' if len(created) != 1 else ''}." if created else ".")
                ),
                "tableCell": {"nonterminal": symbol, "terminal": lookahead},
            }
        )

    if len(steps) >= _MAX_STEPS and not accepted:
        error = "Step limit reached; the grammar may contain a cycle that never consumes input."
    tree = builder.nested(root)
    return {
        "canParse": True,
        "accepted": accepted,
        "error": error,
        "tokens": tokens,
        "input": input_text,
        "steps": steps,
        "tree": tree,
        "derivations": derivations(tree),
        "nodeCreatedAt": node_created_at,
        "stackFinal": snapshot(),
    }


def analyze_ll1(grammar_text: str, input_text: str = "") -> dict[str, Any]:
    from .grammar import analyze_grammar

    analysis = analyze_grammar(grammar_text)
    if not analysis["valid"]:
        return {"valid": False, "errors": analysis["errors"], "stage": "grammar"}
    table = build_table(analysis)
    result: dict[str, Any] = {
        "valid": True,
        "grammar": analysis["grammar"],
        "first": analysis["first"],
        "follow": analysis["follow"],
        "nullable": analysis["nullable"],
        "firstSteps": analysis["firstSteps"],
        "followSteps": analysis["followSteps"],
        "issues": analysis["issues"],
        "table": table,
        "isLL1": table["isLL1"],
        "conflicts": table["conflicts"],
    }
    if input_text is not None and input_text.strip():
        tok = tokenize_input(analysis["grammar"], input_text)
        result["tokenError"] = tok["error"]
        if tok["error"] is None:
            result["simulation"] = simulate(analysis, table, tok["tokens"], input_text)
        else:
            result["simulation"] = None
    else:
        result["simulation"] = None
    return result
