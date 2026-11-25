"""Regular expressions -> Thompson NFA -> DFA by subset construction.

Everything in this module is computed from the supplied pattern.  The public
entry point is :func:`analyze_regex`, which returns a JSON-serialisable record
including the construction trace used by the Automata Studio.
"""

from __future__ import annotations

from collections import deque
from typing import Any

ANY = "\u03a3"  # wildcard symbol (rendered as a sigma in the interface)
EPS = "\u03b5"
_WORD = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
_DIGIT = "0123456789"
_SPACE = " \t\n\r\f\v"
_PRINTABLE = "".join(chr(i) for i in range(32, 127))
# Universe used for negated classes ([^...], \D, \W, \S): printable ASCII plus
# the common whitespace controls, so e.g. "[^\"]*" also spans tabs and newlines.
_UNIVERSE = _PRINTABLE + "\t\n\r"
# The wildcard "." follows the usual convention and does not match a newline,
# so a rule such as "//.*" stops at the end of the line.
NEWLINE = "\n"
_MAX_STATES = 900


class RegexError(Exception):
    """A regular expression could not be parsed."""

    def __init__(self, message: str, position: int = 0):
        super().__init__(message)
        self.message = message
        self.position = position

    def as_dict(self) -> dict[str, Any]:
        return {"message": self.message, "position": self.position}


# ---------------------------------------------------------------------------
# Lexer / parser
# ---------------------------------------------------------------------------

_LITERAL, _CLASS, _ANY, _EPSILON = "lit", "class", "any", "epsilon"
_META = set("|*+?()[]\\.")


def _class_chars(body: str, pos: int) -> set[str]:
    """Expand a character-class body, supporting ranges and escapes."""
    chars: set[str] = set()
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\":
            i += 1
            if i >= len(body):
                raise RegexError("Dangling escape inside character class", pos + i)
            esc = body[i]
            if esc in _CONTROL_ESCAPES:
                chars.add(_CONTROL_ESCAPES[esc])
            else:
                expanded = _escape_class(esc)
                if expanded is None:
                    chars.add(esc)
                else:
                    chars |= expanded
            i += 1
            continue
        if i + 2 < len(body) and body[i + 1] == "-":
            lo, hi = ch, body[i + 2]
            if ord(lo) > ord(hi):
                raise RegexError(f"Invalid character range '{lo}-{hi}'", pos + i)
            chars.update(chr(c) for c in range(ord(lo), ord(hi) + 1))
            i += 3
            continue
        chars.add(ch)
        i += 1
    if not chars:
        raise RegexError("Empty character class", pos)
    return chars


def _escape_class(ch: str) -> set[str] | None:
    if ch == "d":
        return set(_DIGIT)
    if ch == "w":
        return set(_WORD)
    if ch == "s":
        return set(_SPACE)
    if ch == "D":
        return set(_UNIVERSE) - set(_DIGIT)
    if ch == "W":
        return set(_UNIVERSE) - set(_WORD)
    if ch == "S":
        return set(_PRINTABLE) - set(_SPACE)
    return None


_CONTROL_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "f": "\f", "v": "\v"}


def _tokenize(pattern: str) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "(":
            tokens.append({"kind": "(", "pos": i})
            i += 1
        elif ch == ")":
            tokens.append({"kind": ")", "pos": i})
            i += 1
        elif ch == "|":
            tokens.append({"kind": "|", "pos": i})
            i += 1
        elif ch == "*":
            tokens.append({"kind": "*", "pos": i})
            i += 1
        elif ch == "+":
            tokens.append({"kind": "+", "pos": i})
            i += 1
        elif ch == "?":
            tokens.append({"kind": "?", "pos": i})
            i += 1
        elif ch == ".":
            tokens.append({"kind": _ANY, "pos": i})
            i += 1
        elif ch == "[":
            start = i
            i += 1
            negate = False
            if i < len(pattern) and pattern[i] == "^":
                negate = True
                i += 1
            body_chars: list[str] = []
            closed = False
            while i < len(pattern):
                if pattern[i] == "]" and body_chars:
                    closed = True
                    break
                if pattern[i] == "\\" and i + 1 < len(pattern):
                    body_chars.append(pattern[i])
                    body_chars.append(pattern[i + 1])
                    i += 2
                    continue
                body_chars.append(pattern[i])
                i += 1
            if not closed:
                raise RegexError("Unterminated character class", start)
            body = "".join(body_chars)
            chars = _class_chars(body, start + 1)
            if negate:
                chars = set(_UNIVERSE) - chars
            tokens.append({"kind": _CLASS, "chars": sorted(chars), "pos": start})
            i += 1
        elif ch == "\\":
            if i + 1 >= len(pattern):
                raise RegexError("Dangling escape at end of pattern", i)
            esc = pattern[i + 1]
            expanded = _escape_class(esc)
            if expanded is not None:
                tokens.append({"kind": _CLASS, "chars": sorted(expanded), "pos": i})
            elif esc == "n":
                tokens.append({"kind": _LITERAL, "ch": "\n", "pos": i})
            elif esc == "t":
                tokens.append({"kind": _LITERAL, "ch": "\t", "pos": i})
            elif esc == "r":
                tokens.append({"kind": _LITERAL, "ch": "\r", "pos": i})
            else:
                tokens.append({"kind": _LITERAL, "ch": esc, "pos": i})
            i += 2
        elif ch in "εϵ":
            tokens.append({"kind": _EPSILON, "pos": i})
            i += 1
        elif ch in _META:
            raise RegexError(f"Unexpected metacharacter '{ch}'", i)
        else:
            tokens.append({"kind": _LITERAL, "ch": ch, "pos": i})
            i += 1
    return tokens


class _Parser:
    def __init__(self, tokens: list[dict[str, Any]], source: str):
        self.tokens = tokens
        self.source = source
        self.i = 0

    def peek(self) -> dict[str, Any] | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self) -> dict[str, Any]:
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def parse(self) -> dict[str, Any]:
        if not self.tokens:
            raise RegexError("Regular expression is empty", 0)
        node = self.alternation()
        if self.peek() is not None:
            tok = self.peek()
            raise RegexError("Unexpected token; check parentheses", tok["pos"])
        return node

    def alternation(self) -> dict[str, Any]:
        branches = [self.concat()]
        while self.peek() and self.peek()["kind"] == "|":
            self.take()
            if self.peek() is None or self.peek()["kind"] in ("|", ")"):
                raise RegexError("Empty alternative in regular expression", self.peek()["pos"] if self.peek() else len(self.source))
            branches.append(self.concat())
        if len(branches) == 1:
            return branches[0]
        return {"type": "alt", "branches": branches}

    def concat(self) -> dict[str, Any]:
        parts: list[dict[str, Any]] = []
        while self.peek() and self.peek()["kind"] not in ("|", ")"):
            parts.append(self.repeat())
        if not parts:
            return {"type": "epsilon"}
        if len(parts) == 1:
            return parts[0]
        return {"type": "concat", "parts": parts}

    def repeat(self) -> dict[str, Any]:
        node = self.atom()
        while self.peek() and self.peek()["kind"] in ("*", "+", "?"):
            op = self.take()["kind"]
            node = {"type": {"*": "star", "+": "plus", "?": "opt"}[op], "child": node}
        return node

    def atom(self) -> dict[str, Any]:
        tok = self.peek()
        if tok is None:
            raise RegexError("Unexpected end of regular expression", len(self.source))
        kind = tok["kind"]
        if kind == "(":
            self.take()
            if self.peek() and self.peek()["kind"] == ")":
                self.take()
                return {"type": "epsilon"}
            node = self.alternation()
            if not self.peek() or self.peek()["kind"] != ")":
                raise RegexError("Missing closing parenthesis", tok["pos"])
            self.take()
            return node
        if kind == ")":
            raise RegexError("Unmatched closing parenthesis", tok["pos"])
        self.take()
        if kind == _LITERAL:
            return {"type": "lit", "ch": tok["ch"]}
        if kind == _CLASS:
            return {"type": "class", "chars": tok["chars"]}
        if kind == _ANY:
            return {"type": "any"}
        if kind == _EPSILON:
            return {"type": "epsilon"}
        if kind in ("*", "+", "?"):
            raise RegexError(f"Quantifier '{kind}' has nothing to repeat", tok["pos"])
        if kind == "|":
            raise RegexError("Empty alternative in regular expression", tok["pos"])
        raise RegexError(f"Unexpected token '{kind}'", tok["pos"])


def parse_regex(pattern: str) -> dict[str, Any]:
    if len(pattern) > 2000:
        raise RegexError("Pattern is too long (limit 2000 characters)", 0)
    tokens = _tokenize(pattern)
    return _Parser(tokens, pattern).parse()


def render_ast(node: dict[str, Any]) -> str:
    """Return a readable, fully parenthesised form of the AST."""
    kind = node["type"]
    if kind == "lit":
        ch = node["ch"]
        return "\\" + ch if ch in _META or ch.isspace() else ch
    if kind == "class":
        chars = node["chars"]
        if len(chars) > 8:
            return "[" + "".join(chars[:5]) + "…" + "]"
        return "[" + "".join("\\" + c if c in "\\]" else c for c in chars) + "]"
    if kind == "any":
        return "."
    if kind == "epsilon":
        return EPS
    if kind in ("star", "plus", "opt"):
        sym = {"star": "*", "plus": "+", "opt": "?"}[kind]
        return f"({render_ast(node['child'])}){sym}"
    if kind == "concat":
        return "".join(render_ast(p) for p in node["parts"])
    if kind == "alt":
        return "(" + " | ".join(render_ast(b) for b in node["branches"]) + ")"
    return "?"


# ---------------------------------------------------------------------------
# Thompson construction
# ---------------------------------------------------------------------------


class _NfaBuilder:
    def __init__(self) -> None:
        self.states: list[dict[str, Any]] = []
        self.steps: list[dict[str, Any]] = []

    def new_state(self, note: str) -> int:
        if len(self.states) >= _MAX_STATES:
            raise RegexError("Pattern is too complex (state limit reached)", 0)
        sid = len(self.states)
        self.states.append({"id": sid, "accepting": False, "transitions": [], "epsilon": []})
        self.steps.append({"kind": "state", "state": sid, "detail": note})
        return sid

    def edge(self, frm: int, symbol: str, to: int) -> None:
        if symbol == EPS:
            self.states[frm]["epsilon"].append(to)
        else:
            self.states[frm]["transitions"].append({"symbol": symbol, "to": to})
        self.steps.append(
            {
                "kind": "epsilon" if symbol == EPS else "symbol",
                "from": frm,
                "to": to,
                "symbol": symbol,
                "detail": f"q{frm} → q{to} on {symbol}",
            }
        )

    def build(self, node: dict[str, Any]) -> tuple[int, int]:
        kind = node["type"]
        if kind == "epsilon":
            a = self.new_state("Create a start state for ε")
            b = self.new_state("Create an accept state for ε")
            self.edge(a, EPS, b)
            return a, b
        if kind == "lit":
            a = self.new_state(f"Create a state for literal '{node['ch']}'")
            b = self.new_state(f"Create a target state for '{node['ch']}'")
            self.edge(a, node["ch"], b)
            return a, b
        if kind == "class":
            a = self.new_state("Create a state for a character class")
            b = self.new_state("Create a target state for the class")
            for ch in node["chars"]:
                self.edge(a, ch, b)
            return a, b
        if kind == "any":
            a = self.new_state("Create a state for the wildcard")
            b = self.new_state("Create a target state for the wildcard")
            self.edge(a, ANY, b)
            return a, b
        if kind == "concat":
            start, end = self.build(node["parts"][0])
            for part in node["parts"][1:]:
                s2, e2 = self.build(part)
                self.edge(end, EPS, s2)
                end = e2
            return start, end
        if kind == "alt":
            start = self.new_state("Create a branch state for alternation")
            end = self.new_state("Create a merge state for alternation")
            for branch in node["branches"]:
                s, e = self.build(branch)
                self.edge(start, EPS, s)
                self.edge(e, EPS, end)
            return start, end
        if kind in ("star", "plus", "opt"):
            start = self.new_state(f"Create a state for '{kind}'")
            end = self.new_state(f"Create a target state for '{kind}'")
            s, e = self.build(node["child"])
            if kind == "star":
                self.edge(start, EPS, s)
                self.edge(start, EPS, end)
                self.edge(e, EPS, s)
                self.edge(e, EPS, end)
            elif kind == "plus":
                self.edge(start, EPS, s)
                self.edge(e, EPS, s)
                self.edge(e, EPS, end)
            else:
                self.edge(start, EPS, s)
                self.edge(start, EPS, end)
                self.edge(e, EPS, end)
            return start, end
        raise RegexError("Unsupported regular expression node", 0)


def _epsilon_closure(states: list[dict[str, Any]], seed: set[int]) -> set[int]:
    stack = list(seed)
    seen = set(seed)
    while stack:
        s = stack.pop()
        for nxt in states[s]["epsilon"]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def _move(states: list[dict[str, Any]], seed: set[int], symbol: str) -> set[int]:
    """move(S, a) for the subset construction.

    The wildcard is not an ordinary symbol: an NFA edge labelled Σ is also taken
    on every concrete character (except newline).  The DFA column Σ therefore
    stands for "any character not named elsewhere in the alphabet".
    """
    out: set[int] = set()
    for s in seed:
        for tr in states[s]["transitions"]:
            sym = tr["symbol"]
            if sym == symbol or (sym == ANY and symbol != NEWLINE):
                out.add(tr["to"])
    return out


def _alphabet(states: list[dict[str, Any]]) -> list[str]:
    symbols: set[str] = set()
    for st in states:
        for tr in st["transitions"]:
            symbols.add(tr["symbol"])
    explicit = sorted(s for s in symbols if s != ANY)
    return explicit + ([ANY] if ANY in symbols else [])


def _compact_symbols(symbols: list[str]) -> str:
    if ANY in symbols:
        return ANY
    return ", ".join(symbols)


def analyze_regex(pattern: str) -> dict[str, Any]:
    """Build the NFA and DFA for *pattern* with a full construction trace."""
    try:
        ast = parse_regex(pattern)
    except RegexError as exc:
        return {"valid": False, "pattern": pattern, "error": exc.as_dict()}

    try:
        builder = _NfaBuilder()
        start, accept = builder.build(ast)
        builder.states[accept]["accepting"] = True
        states = builder.states
        if len(states) > _MAX_STATES:
            raise RegexError("Pattern is too complex (state limit reached)", 0)

        closures = []
        for st in states:
            closures.append(
                {
                    "state": st["id"],
                    "closure": sorted(_epsilon_closure(states, {st["id"]})),
                }
            )

        alphabet = _alphabet(states)
        start_set = _epsilon_closure(states, {start})
        dfa_sets: list[frozenset[int]] = [frozenset(start_set)]
        dfa_index: dict[frozenset[int], int] = {frozenset(start_set): 0}
        dfa_transitions: list[dict[str, Any]] = []
        dfa_accepting: list[bool] = [any(states[s]["accepting"] for s in start_set)]
        subset_steps: list[dict[str, Any]] = [
            {
                "type": "start",
                "state": "D0",
                "nfaStates": sorted(start_set),
                "explanation": f"ε-closure({{q{start}}}) = {{{', '.join('q' + str(s) for s in sorted(start_set))}}} becomes D0, the DFA start state.",
            }
        ]
        queue: deque[int] = deque([0])
        while queue:
            di = queue.popleft()
            current = dfa_sets[di]
            for symbol in alphabet:
                moved = _move(states, current, symbol)
                if not moved:
                    continue
                closed = _epsilon_closure(states, moved)
                key = frozenset(closed)
                is_new = key not in dfa_index
                if is_new:
                    if len(dfa_sets) >= _MAX_STATES:
                        raise RegexError("DFA state limit reached; simplify the pattern", 0)
                    dfa_index[key] = len(dfa_sets)
                    dfa_sets.append(key)
                    dfa_accepting.append(any(states[s]["accepting"] for s in key))
                    queue.append(len(dfa_sets) - 1)
                target = dfa_index[key]
                dfa_transitions.append({"from": f"D{di}", "symbol": symbol, "to": f"D{target}"})
                label = "Σ (any character)" if symbol == ANY else f"'{symbol}'"
                subset_steps.append(
                    {
                        "type": "transition",
                        "state": f"D{di}",
                        "symbol": symbol,
                        "move": sorted(moved),
                        "closure": sorted(closed),
                        "to": f"D{target}",
                        "isNew": is_new,
                        "explanation": (
                            f"On {label}: move(D{di}, {label}) = {{{', '.join('q' + str(s) for s in sorted(moved))}}}; "
                            f"ε-closure = {{{', '.join('q' + str(s) for s in sorted(closed))}}} → D{target}"
                            + (" (new DFA state)." if is_new else " (already known).")
                        ),
                    }
                )

        dfa_states = [
            {
                "id": f"D{i}",
                "nfaStates": sorted(s),
                "accepting": dfa_accepting[i],
                "start": i == 0,
            }
            for i, s in enumerate(dfa_sets)
        ]
        subset_steps.append(
            {
                "type": "done",
                "explanation": f"Subset construction finished: {len(dfa_sets)} DFA states, {len(dfa_transitions)} transitions.",
            }
        )

        raw_dfa = {
            "start": "D0",
            "states": dfa_states,
            "transitions": dfa_transitions,
            "alphabet": alphabet,
            "accepting": [s["id"] for s in dfa_states if s["accepting"]],
        }
        minimal = minimize_dfa(raw_dfa)

        return {
            "valid": True,
            "pattern": pattern,
            "ast": render_ast(ast),
            "minDfa": minimal,
            "nfa": {
                "start": start,
                "accepting": [accept],
                "states": states,
                "alphabet": alphabet,
                "epsilonClosures": closures,
            },
            "dfa": {
                "start": "D0",
                "states": dfa_states,
                "transitions": dfa_transitions,
                "alphabet": alphabet,
                "accepting": [s["id"] for s in dfa_states if s["accepting"]],
            },
            "constructionSteps": builder.steps,
            "subsetSteps": subset_steps,
            "stats": {
                "nfaStates": len(states),
                "nfaEdges": sum(len(s["transitions"]) + len(s["epsilon"]) for s in states),
                "epsilonEdges": sum(len(s["epsilon"]) for s in states),
                "dfaStates": len(dfa_sets),
                "dfaEdges": len(dfa_transitions),
                "minDfaStates": len(minimal["states"]),
                "alphabetSize": len([s for s in alphabet if s != ANY]),
                "hasWildcard": ANY in alphabet,
            },
        }
    except RegexError as exc:
        return {"valid": False, "pattern": pattern, "error": exc.as_dict()}


def minimize_dfa(dfa: dict[str, Any]) -> dict[str, Any]:
    """Minimise a DFA by partition refinement (Moore's algorithm).

    Missing transitions are treated as edges to an implicit dead state, so the
    input does not need to be complete.  Every refinement round is recorded so
    the interface can show *why* two states were split or merged.
    """
    ids = [s["id"] for s in dfa["states"]]
    alphabet = list(dfa["alphabet"])
    trans = {(t["from"], t["symbol"]): t["to"] for t in dfa["transitions"]}
    accepting = set(dfa["accepting"])

    def label(block: list[str]) -> str:
        return "{" + ", ".join(block) + "}"

    block_of: dict[str, int] = {}
    groups = [g for g in ([s for s in ids if s in accepting], [s for s in ids if s not in accepting]) if g]
    for bi, g in enumerate(groups):
        for s in g:
            block_of[s] = bi
    steps: list[dict[str, Any]] = [
        {
            "round": 0,
            "partition": [list(g) for g in groups],
            "explanation": "Start with two blocks: accepting states "
            + label([s for s in ids if s in accepting])
            + " and non-accepting states "
            + label([s for s in ids if s not in accepting])
            + ". States in different blocks can never be equivalent.",
        }
    ]

    round_no = 0
    while True:
        round_no += 1
        signatures: dict[tuple[Any, ...], list[str]] = {}
        order: list[tuple[Any, ...]] = []
        for s in ids:
            sig = (block_of[s],) + tuple(
                block_of[trans[(s, a)]] if (s, a) in trans else -1 for a in alphabet
            )
            if sig not in signatures:
                signatures[sig] = []
                order.append(sig)
            signatures[sig].append(s)
        new_groups = [signatures[sig] for sig in order]
        if len(new_groups) == len(groups):
            steps.append(
                {
                    "round": round_no,
                    "partition": [list(g) for g in groups],
                    "explanation": f"Round {round_no}: no block splits, so the partition is stable. "
                    f"{len(ids)} DFA states collapse into {len(groups)} minimal states.",
                }
            )
            break
        splits = []
        for old in groups:
            pieces = [g for g in new_groups if g[0] in old]
            if len(pieces) > 1:
                splits.append(f"{label(old)} splits into " + " and ".join(label(p) for p in pieces))
        groups = new_groups
        block_of = {s: bi for bi, g in enumerate(groups) for s in g}
        steps.append(
            {
                "round": round_no,
                "partition": [list(g) for g in groups],
                "explanation": f"Round {round_no}: "
                + "; ".join(splits)
                + " because their transitions lead into different blocks.",
            }
        )

    # Renumber so the block containing the start state becomes M0, then BFS order.
    start_block = block_of[dfa["start"]]
    rep = {bi: g[0] for bi, g in enumerate(groups)}
    numbering: dict[int, int] = {start_block: 0}
    queue: deque[int] = deque([start_block])
    while queue:
        b = queue.popleft()
        for a in alphabet:
            t = trans.get((rep[b], a))
            if t is not None and block_of[t] not in numbering:
                numbering[block_of[t]] = len(numbering)
                queue.append(block_of[t])
    for bi in range(len(groups)):
        numbering.setdefault(bi, len(numbering))

    name = lambda bi: f"M{numbering[bi]}"
    states = sorted(
        (
            {
                "id": name(bi),
                "dfaStates": list(g),
                "accepting": g[0] in accepting,
                "start": bi == start_block,
            }
            for bi, g in enumerate(groups)
        ),
        key=lambda s: int(s["id"][1:]),
    )
    transitions = []
    for bi in sorted(range(len(groups)), key=lambda b: numbering[b]):
        for a in alphabet:
            t = trans.get((rep[bi], a))
            if t is not None:
                transitions.append({"from": name(bi), "symbol": a, "to": name(block_of[t])})
    return {
        "start": "M0",
        "states": states,
        "transitions": transitions,
        "alphabet": alphabet,
        "accepting": [s["id"] for s in states if s["accepting"]],
        "steps": steps,
        "removed": len(ids) - len(groups),
    }


def compile_dfa(dfa: dict[str, Any]) -> dict[str, Any]:
    """Pre-index a DFA so repeated matching does not rebuild lookup tables."""
    return {
        "start": dfa["start"],
        "trans": {(t["from"], t["symbol"]): t["to"] for t in dfa["transitions"]},
        "accepting": set(dfa["accepting"]),
        "compiled": True,
    }


def _step(trans: dict[tuple[str, str], str], current: str, ch: str) -> str | None:
    nxt = trans.get((current, ch))
    if nxt is None and ch != NEWLINE:
        nxt = trans.get((current, ANY))
    return nxt


def dfa_accepts(dfa: dict[str, Any], text: str) -> bool:
    """Convenience predicate used by tests and the lexer."""
    machine = dfa if dfa.get("compiled") else compile_dfa(dfa)
    current = machine["start"]
    for ch in text:
        current = _step(machine["trans"], current, ch)
        if current is None:
            return False
    return current in machine["accepting"]


def longest_dfa_match(dfa: dict[str, Any], text: str, start: int = 0) -> tuple[int, list[str]]:
    """Return (end offset, state path) for the longest accepting prefix.

    *dfa* may be a raw DFA record or the result of :func:`compile_dfa`.
    """
    machine = dfa if dfa.get("compiled") else compile_dfa(dfa)
    current = machine["start"]
    trans = machine["trans"]
    accepting = machine["accepting"]
    path = [current]
    best_end = start if current in accepting else -1
    best_path = list(path)
    i = start
    while i < len(text):
        nxt = _step(trans, current, text[i])
        if nxt is None:
            break
        current = nxt
        path.append(current)
        i += 1
        if current in accepting:
            best_end = i
            best_path = list(path)
    return best_end, best_path
