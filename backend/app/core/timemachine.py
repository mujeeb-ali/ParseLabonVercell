"""Compiler Time Machine: one real, synchronised trace across every stage."""

from __future__ import annotations

from typing import Any

from .grammar import EPS, analyze_grammar, tokenize_input
from .lexer import analyze_lexer
from .ll1 import build_table as build_ll1_table, simulate as simulate_ll1
from .slr import build_automaton, build_slr_table, simulate as simulate_slr


def _map_lex_tokens(
    tokens: list[dict[str, Any]],
    terminals: list[str],
    token_map: dict[str, str] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    token_map = token_map or {}
    mapped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    terminal_set = set(terminals)
    for tok in tokens:
        typ = tok["type"]
        symbol = token_map.get(typ)
        if symbol is None:
            if typ in terminal_set:
                symbol = typ
            elif typ.lower() in terminal_set:
                symbol = typ.lower()
            else:
                symbol = None
        if symbol is None or symbol not in terminal_set:
            errors.append(
                {
                    "tokenId": tok["id"],
                    "lexeme": tok["lexeme"],
                    "type": typ,
                    "message": (
                        f"Lexer token {typ} ('{tok['lexeme']}') has no matching grammar terminal. "
                        f"Available terminals: {', '.join(terminals)}. Add a token mapping."
                    ),
                }
            )
            continue
        mapped.append(
            {
                "symbol": symbol,
                "lexeme": tok["lexeme"],
                "tokenId": tok["id"],
                "type": typ,
                "start": tok["start"],
                "end": tok["end"],
                "line": tok["line"],
                "column": tok["column"],
            }
        )
    return mapped, errors


def run_time_machine(payload: dict[str, Any]) -> dict[str, Any]:
    grammar_text = payload.get("grammar") or ""
    source = payload.get("source") or ""
    rules = payload.get("rules") or []
    input_text = payload.get("input") or ""
    mode = (payload.get("mode") or "ll").lower()
    token_map = payload.get("tokenMap") or {}

    analysis = analyze_grammar(grammar_text)
    if not analysis["valid"]:
        return {
            "valid": False,
            "stage": "grammar",
            "errors": analysis["errors"],
            "stages": [],
            "steps": [],
            "accepted": False,
        }

    g = analysis["grammar"]
    steps: list[dict[str, Any]] = []
    stages = [
        {"id": "source", "label": "Source", "detail": "Raw characters enter the front end."},
        {"id": "lex", "label": "Tokens", "detail": "Regular expressions partition the source."},
        {"id": "grammar", "label": "Grammar", "detail": "Productions, FIRST and FOLLOW are prepared."},
        {"id": "parse", "label": "Parse", "detail": "The parser makes one decision at a time."},
        {"id": "tree", "label": "Tree", "detail": "Nodes are linked into a derivation tree."},
        {"id": "result", "label": "Result", "detail": "Accept or reject, with the reason."},
    ]

    def add_step(
        stage: str,
        title: str,
        detail: str,
        why: str,
        next_text: str,
        **extra: Any,
    ) -> None:
        steps.append(
            {
                "index": len(steps),
                "stage": stage,
                "title": title,
                "detail": detail,
                "why": why,
                "next": next_text,
                "sourceRange": extra.pop("sourceRange", None),
                "tokenId": extra.pop("tokenId", None),
                "tokenIndex": extra.pop("tokenIndex", None),
                "production": extra.pop("production", None),
                "stack": extra.pop("stack", None),
                "input": extra.pop("input", None),
                "lookahead": extra.pop("lookahead", None),
                "tableCell": extra.pop("tableCell", None),
                "stateStack": extra.pop("stateStack", None),
                "nodeId": extra.pop("nodeId", None),
                "created": extra.pop("created", None),
                "parseStep": extra.pop("parseStep", None),
                "accepted": extra.pop("accepted", None),
                "severity": extra.pop("severity", "info"),
                **extra,
            }
        )

    lex_result = None
    input_tokens: list[dict[str, Any]] = []
    source_spans: list[dict[str, Any]] = []
    lex_errors: list[dict[str, Any]] = []
    token_error: str | None = None

    if source:
        if not rules:
            token_error = "A source program was supplied without lexer rules."
        else:
            lex_result = analyze_lexer(source, rules)
            source_spans = lex_result["spans"]
            lex_errors = lex_result["errors"]
            mapped, mapping_errors = _map_lex_tokens(lex_result["tokens"], g["terminals"], token_map)
            input_tokens = mapped
            if lex_result.get("ruleErrors"):
                bad = lex_result["ruleErrors"][0]
                token_error = f"Lexer rule {bad.get('name') or '#' + str(bad['rule'] + 1)} is invalid: {bad['message']}"
            elif lex_errors:
                # A program with characters no rule can match is not a valid
                # program, even if the remaining tokens happen to parse.
                first = lex_errors[0]
                token_error = (
                    f"Lexical error at line {first['line']}, column {first['column']}: {first['message']} "
                    f"Syntax analysis is skipped because the token stream is incomplete."
                )
            elif mapping_errors:
                token_error = mapping_errors[0]["message"]
            add_step(
                "source",
                "Source program enters the front end",
                f"{len(source)} characters, {source.count(chr(10)) + 1} line(s).",
                "A compiler never starts with tokens; it starts with a stream of characters and source positions.",
                "The lexer applies the longest-match rule to this text.",
                sourceRange={"start": 0, "end": len(source)},
            )
            for idx, tok in enumerate(lex_result["tokens"]):
                add_step(
                    "lex",
                    f"Token {idx + 1}: {tok['type']}",
                    f"'{tok['lexeme']}' at line {tok['line']}, column {tok['column']}. {tok['explanation']}",
                    f"The regular expression for {tok['type']} accepts this lexeme and no longer rule wins the maximal-munch contest.",
                    "The next characters are examined at the new position.",
                    sourceRange={"start": tok["start"], "end": tok["end"]},
                    tokenId=tok["id"],
                    tokenIndex=idx,
                )
            for err in lex_errors:
                add_step(
                    "lex",
                    "Lexical error",
                    err["message"],
                    "No token rule can consume this character, so the front end cannot form a token.",
                    "The machine records the error and continues scanning to report the full picture.",
                    sourceRange={"start": err["start"], "end": err["end"]},
                    severity="error",
                )
            if mapping_errors:
                for merr in mapping_errors:
                    add_step(
                        "lex",
                        "Token has no grammar terminal",
                        merr["message"],
                        "The lexer and the grammar use different alphabets; a mapping is needed between token types and grammar terminals.",
                        "Provide a token mapping to continue to syntax analysis.",
                        severity="error",
                    )
    else:
        tok = tokenize_input(g, input_text)
        token_error = tok["error"]
        input_tokens = [{"symbol": t, "lexeme": t, "tokenId": None} for t in tok["tokens"]]
        add_step(
            "source",
            "Terminal stream enters the parser",
            f"{len(tok['tokens'])} token(s): {' '.join(tok['tokens']) or EPS}",
            "The input is supplied directly as grammar terminals, so lexical analysis is bypassed.",
            "The parser reads the terminal stream from left to right.",
            input=input_tokens,
        )

    add_step(
        "grammar",
        f"Grammar loaded: {g['start']}",
        f"{len(g['productions'])} productions, {len(g['nonterminals'])} non-terminals, {len(g['terminals'])} terminals. "
        f"Nullable: {', '.join(k for k, v in analysis['nullable'].items() if v) or 'none'}.",
        "FIRST and FOLLOW sets were computed by fixed-point iteration over the productions.",
        f"The {'LL(1) predictive' if mode == 'll' else 'SLR'} parser is constructed from this grammar.",
        input=input_tokens,
    )
    add_step(
        "grammar",
        "Input recognised as a terminal sequence",
        " ".join(t["symbol"] for t in input_tokens) + " $",
        "The parser's alphabet is the grammar's terminal set, not raw characters.",
        "Syntax analysis starts with the start symbol on the stack.",
        input=input_tokens,
    )

    simulation = None
    if token_error is None:
        symbols = [t["symbol"] for t in input_tokens]
        if mode == "slr":
            try:
                automaton = build_automaton(analysis)
                table = build_slr_table(analysis, automaton)
            except ValueError as exc:
                token_error = str(exc)
                automaton = None
                table = None
            if table is not None:
                simulation = simulate_slr(analysis, automaton, table, symbols, input_text)
                table_cells = table
            else:
                table_cells = None
        else:
            table = build_ll1_table(analysis)
            simulation = simulate_ll1(analysis, table, symbols, input_text)
            table_cells = table

        if simulation is not None and not simulation.get("canParse", False):
            token_error = simulation.get("reason", "The parser could not be simulated.")
            simulation = None

    if simulation is None:
        add_step(
            "result",
            "Journey stopped",
            token_error or "The parser could not run.",
            "The engine refuses to invent a parse; this is the precise reason the pipeline halted.",
            "Fix the input or grammar and run the experiment again.",
            accepted=False,
            severity="error",
        )
        return {
            "valid": False,
            "stage": "parse",
            "error": token_error,
            "grammar": g,
            "analysis": {
                "first": analysis["first"],
                "follow": analysis["follow"],
                "nullable": analysis["nullable"],
            },
            "lexer": lex_result,
            "source": source,
            "sourceSpans": source_spans,
            "tokens": input_tokens,
            "stages": stages,
            "steps": steps,
            "accepted": False,
            "mode": mode,
        }

    all_symbols = [t["symbol"] for t in input_tokens]
    stream_len = len(all_symbols) + 1

    for pstep in simulation["steps"]:
        raw_action = pstep.get("action")
        if isinstance(raw_action, str):
            action = {}
            atype = raw_action
        else:
            action = raw_action or {}
            atype = action.get("type")
        if mode == "ll":
            token_index = pstep.get("consumed", 0)
        else:
            remaining = pstep.get("input") or []
            token_index = max(0, stream_len - len(remaining))
        source_range = None
        token_id = None
        if 0 <= token_index < len(input_tokens):
            tok = input_tokens[token_index]
            token_id = tok.get("tokenId")
            if tok.get("start") is not None:
                source_range = {"start": tok["start"], "end": tok["end"]}
        if atype == "expand":
            title = f"Expand {action.get('nonterminal') or (pstep.get('production') or {}).get('lhs', '')}"
            detail = pstep.get("explanation", "")
            why = f"FIRST/FOLLOW make the choice deterministic: table[{(pstep.get('tableCell') or {}).get('nonterminal')}, {pstep.get('lookahead')}] selects this production."
        elif atype == "match":
            title = f"Match '{pstep.get('lookahead')}'"
            detail = pstep.get("explanation", "")
            why = "The top of the stack is a terminal and it agrees with the lookahead, so the token is consumed."
        elif atype == "shift":
            title = f"Shift '{pstep.get('lookahead')}' → state {action.get('target')}"
            detail = pstep.get("explanation", "")
            why = "ACTION[state, lookahead] is a shift, so the token and the target state are pushed."
        elif atype == "reduce":
            prod = pstep.get("production") or {}
            title = f"Reduce by {prod.get('text', 'production')}"
            detail = pstep.get("explanation", "")
            why = f"The completed LR(0) item is reduced because the lookahead is in FOLLOW({prod.get('lhs', '')})."
        elif atype == "accept":
            title = "Accept"
            detail = pstep.get("explanation", "")
            why = "The start symbol covers the whole input, so the grammar derives the token stream."
        else:
            title = "Parse error"
            detail = pstep.get("explanation", "")
            why = "No table entry exists for the current state and lookahead."

        add_step(
            "parse",
            title,
            detail,
            why,
            "The next decision follows from the new stack and lookahead.",
            sourceRange=source_range,
            tokenId=token_id,
            tokenIndex=token_index,
            production=pstep.get("production"),
            stack=pstep.get("stack"),
            input=pstep.get("input"),
            lookahead=pstep.get("lookahead"),
            tableCell=pstep.get("tableCell"),
            stateStack=pstep.get("stateStack"),
            parseStep=pstep.get("index"),
            severity="error" if atype == "error" else "info",
        )

        if pstep.get("created"):
            node_label = (
                (pstep.get("production") or {}).get("lhs")
                if atype == "reduce"
                else pstep.get("lookahead")
            )
            add_step(
                "tree",
                f"Link node {node_label}",
                f"{len(pstep['created'])} node(s) created at parse step {pstep.get('index')}.",
                "Parse-tree nodes mirror the derivation: terminals are leaves and reductions create interior nodes.",
                "The tree keeps growing as the parser consumes the input.",
                sourceRange=source_range,
                tokenId=token_id,
                tokenIndex=token_index,
                production=pstep.get("production"),
                nodeId=pstep.get("nodeId"),
                created=pstep.get("created"),
                parseStep=pstep.get("index"),
            )

    final = simulation
    add_step(
        "result",
        "Accepted" if final["accepted"] else "Rejected",
        (
            "The parser consumed the full input and reduced it to the start symbol."
            if final["accepted"]
            else final.get("error") or "The parser stopped before accepting the input."
        ),
        (
            "Acceptance is a proof: every step followed a table entry derived from the grammar."
            if final["accepted"]
            else "The table had no legal move for the current state and lookahead."
        ),
        "Run another string or inspect the trace backwards with the time machine.",
        accepted=final["accepted"],
        severity="ok" if final["accepted"] else "error",
    )

    stage_counts = {s["id"]: 0 for s in stages}
    for s in steps:
        stage_counts[s["stage"]] = stage_counts.get(s["stage"], 0) + 1

    return {
        "valid": True,
        "mode": mode,
        "grammar": g,
        "analysis": {
            "first": analysis["first"],
            "follow": analysis["follow"],
            "nullable": analysis["nullable"],
            "issues": analysis["issues"],
        },
        "lexer": lex_result,
        "source": source,
        "sourceSpans": source_spans,
        "tokens": input_tokens,
        "stages": [dict(s, count=stage_counts.get(s["id"], 0)) for s in stages],
        "steps": steps,
        "accepted": final["accepted"],
        "error": final.get("error"),
        "tree": final["tree"],
        "nodeCreatedAt": final.get("nodeCreatedAt", {}),
        "derivations": final.get("derivations"),
        "conflicts": (table_cells or {}).get("conflicts", []),
    }
