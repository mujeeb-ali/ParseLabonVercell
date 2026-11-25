"""Lexical analysis driven by user-supplied regular expressions."""

from __future__ import annotations

import bisect
import time
from typing import Any

from .regex_engine import analyze_regex, compile_dfa, longest_dfa_match


def _line_starts(source: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(source):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _position(starts: list[int], offset: int) -> tuple[int, int]:
    line = bisect.bisect_right(starts, offset)
    return line, offset - starts[line - 1] + 1


def analyze_lexer(source: str, rules: list[dict[str, Any]]) -> dict[str, Any]:
    started = time.perf_counter()
    if not isinstance(rules, list) or not rules:
        return {
            "valid": False,
            "source": source,
            "rules": [],
            "tokens": [],
            "errors": [{"message": "Define at least one token rule before running the lexer.", "line": 1, "column": 1, "start": 0, "end": 0}],
            "spans": [],
            "stats": {"tokens": 0, "errors": 1, "skipped": 0, "rules": 0},
        }

    compiled: list[dict[str, Any]] = []
    rule_errors: list[dict[str, Any]] = []
    names: set[str] = set()
    for idx, rule in enumerate(rules):
        name = str(rule.get("name", "")).strip()
        pattern = str(rule.get("pattern", ""))
        skip = bool(rule.get("skip", False))
        entry: dict[str, Any] = {
            "index": idx,
            "name": name,
            "pattern": pattern,
            "skip": skip,
            "valid": True,
            "error": None,
            "dfa": None,
            "stats": None,
            "matchesEmpty": False,
        }
        if not name:
            entry["valid"] = False
            entry["error"] = "Token name is required."
            rule_errors.append({"rule": idx, "name": name, "message": "Token name is required."})
        elif not name.replace("_", "").isalnum() or name[0].isdigit():
            entry["valid"] = False
            entry["error"] = "Token names must start with a letter or underscore and contain only letters, digits and underscores."
            rule_errors.append({"rule": idx, "name": name, "message": entry["error"]})
        elif name in names:
            entry["valid"] = False
            entry["error"] = f"Duplicate token name '{name}'."
            rule_errors.append({"rule": idx, "name": name, "message": entry["error"]})
        else:
            names.add(name)
        if entry["valid"]:
            result = analyze_regex(pattern)
            if not result["valid"]:
                entry["valid"] = False
                entry["error"] = f"{result['error']['message']} (at pattern position {result['error']['position']})."
                rule_errors.append({"rule": idx, "name": name, "message": entry["error"]})
            else:
                entry["dfa"] = result["dfa"]
                entry["stats"] = result["stats"]
                entry["matchesEmpty"] = result["dfa"]["start"] in result["dfa"]["accepting"]
                if entry["matchesEmpty"]:
                    entry["warning"] = "This pattern can match the empty string, so it can never produce a zero-length token."
        compiled.append(entry)

    valid_rules = [r for r in compiled if r["valid"] and r["dfa"] is not None]
    machines = {r["index"]: compile_dfa(r["dfa"]) for r in valid_rules}
    starts = _line_starts(source)
    tokens: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    skipped = 0
    counts: dict[str, int] = {r["name"]: 0 for r in valid_rules}
    pos = 0
    token_id = 0

    while pos < len(source):
        candidates: list[dict[str, Any]] = []
        best: dict[str, Any] | None = None
        for rule in valid_rules:
            end, path = longest_dfa_match(machines[rule["index"]], source, pos)
            length = max(0, end - pos)
            candidates.append(
                {
                    "rule": rule["name"],
                    "ruleIndex": rule["index"],
                    "length": length,
                    "end": end,
                    "selected": False,
                }
            )
            if length > 0 and (best is None or length > best["length"]):
                best = {
                    "rule": rule,
                    "end": end,
                    "length": length,
                    "path": path,
                    "candidates": candidates,
                }
        if best is None:
            line, col = _position(starts, pos)
            ch = source[pos]
            shown = ch if ch != "\n" else "\\n"
            errors.append(
                {
                    "message": f"Unexpected character '{shown}'. No token rule matches at this position.",
                    "line": line,
                    "column": col,
                    "start": pos,
                    "end": pos + 1,
                    "char": ch,
                }
            )
            pos += 1
            continue

        end = best["end"]
        lexeme = source[pos:end]
        line, col = _position(starts, pos)
        rule = best["rule"]
        for cand in best["candidates"]:
            if cand["ruleIndex"] == rule["index"]:
                cand["selected"] = True
        if rule["skip"]:
            skipped += len(lexeme)
            pos = end
            continue

        counts[rule["name"]] = counts.get(rule["name"], 0) + 1
        alternatives = sorted(best["candidates"], key=lambda c: (-c["length"], c["ruleIndex"]))
        matched = [c for c in alternatives if c["length"] > 0]
        explanation = (
            f"Rule {rule['name']} consumed {len(lexeme)} character{'s' if len(lexeme) != 1 else ''} "
            f"via DFA states {' → '.join(best['path'])}. "
        )
        if len(matched) > 1:
            runner_up = next((c for c in matched if c["ruleIndex"] != rule["index"]), None)
            explanation += (
                f"Maximal munch chose the longest match"
                + (f"; {runner_up['rule']} matched only {runner_up['length']} character{'s' if runner_up['length'] != 1 else ''}." if runner_up else ".")
            )
        else:
            explanation += "It was the only rule that matched at this position."
        tokens.append(
            {
                "id": token_id,
                "type": rule["name"],
                "lexeme": lexeme,
                "start": pos,
                "end": end,
                "line": line,
                "column": col,
                "ruleIndex": rule["index"],
                "path": best["path"],
                "candidates": alternatives,
                "explanation": explanation,
                "skip": False,
            }
        )
        token_id += 1
        pos = end

    spans: list[dict[str, Any]] = []
    pieces = [
        {"start": tok["start"], "end": tok["end"], "kind": "token", "tokenId": tok["id"]}
        for tok in tokens
    ] + [{"start": err["start"], "end": err["end"], "kind": "error"} for err in errors]
    pieces.sort(key=lambda p: p["start"])
    cursor = 0
    for piece in pieces:
        if piece["start"] > cursor:
            spans.append({"start": cursor, "end": piece["start"], "kind": "plain"})
        spans.append(piece)
        cursor = max(cursor, piece["end"])
    if cursor < len(source):
        spans.append({"start": cursor, "end": len(source), "kind": "plain"})

    elapsed = (time.perf_counter() - started) * 1000
    return {
        "valid": len(rule_errors) == 0,
        "source": source,
        "rules": [
            {
                "index": r["index"],
                "name": r["name"],
                "pattern": r["pattern"],
                "skip": r["skip"],
                "valid": r["valid"],
                "error": r["error"],
                "warning": r.get("warning"),
                "dfa": r["dfa"],
                "stats": r["stats"],
                "matchesEmpty": r["matchesEmpty"],
                "count": counts.get(r["name"], 0),
            }
            for r in compiled
        ],
        "ruleErrors": rule_errors,
        "tokens": tokens,
        "errors": errors,
        "spans": spans,
        "stats": {
            "tokens": len(tokens),
            "errors": len(errors),
            "skipped": skipped,
            "rules": len(valid_rules),
            "durationMs": round(elapsed, 2),
            "counts": counts,
        },
    }
