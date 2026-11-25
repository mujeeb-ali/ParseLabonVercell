"""Curated experiments. Every payload is fed to the real engine."""

from __future__ import annotations

from typing import Any

ARITH_RULES = [
    {"name": "ID", "pattern": "[a-zA-Z_][a-zA-Z0-9_]*", "skip": False},
    {"name": "NUM", "pattern": "[0-9]+", "skip": False},
    {"name": "ASSIGN", "pattern": "=", "skip": False},
    {"name": "PLUS", "pattern": "\\+", "skip": False},
    {"name": "MINUS", "pattern": "-", "skip": False},
    {"name": "STAR", "pattern": "\\*", "skip": False},
    {"name": "SLASH", "pattern": "/", "skip": False},
    {"name": "LPAREN", "pattern": "\\(", "skip": False},
    {"name": "RPAREN", "pattern": "\\)", "skip": False},
    {"name": "SEMI", "pattern": ";", "skip": False},
    {"name": "WS", "pattern": "[ \\t\\n\\r]+", "skip": True},
]

DECL_RULES = [
    {"name": "LET", "pattern": "let", "skip": False},
    {"name": "CONST", "pattern": "const", "skip": False},
    {"name": "ID", "pattern": "[a-zA-Z_][a-zA-Z0-9_]*", "skip": False},
    {"name": "NUM", "pattern": "[0-9]+(\\.[0-9]+)?", "skip": False},
    {"name": "STRING", "pattern": "\"[^\"]*\"", "skip": False},
    {"name": "ASSIGN", "pattern": "=", "skip": False},
    {"name": "SEMI", "pattern": ";", "skip": False},
    {"name": "COMMA", "pattern": ",", "skip": False},
    {"name": "WS", "pattern": "[ \\t\\n\\r]+", "skip": True},
]

CONTROL_RULES = [
    {"name": "IF", "pattern": "if", "skip": False},
    {"name": "ELSE", "pattern": "else", "skip": False},
    {"name": "WHILE", "pattern": "while", "skip": False},
    {"name": "RETURN", "pattern": "return", "skip": False},
    {"name": "ID", "pattern": "[a-zA-Z_][a-zA-Z0-9_]*", "skip": False},
    {"name": "NUM", "pattern": "[0-9]+", "skip": False},
    {"name": "EQ", "pattern": "==", "skip": False},
    {"name": "ASSIGN", "pattern": "=", "skip": False},
    {"name": "LPAREN", "pattern": "\\(", "skip": False},
    {"name": "RPAREN", "pattern": "\\)", "skip": False},
    {"name": "LBRACE", "pattern": "\\{", "skip": False},
    {"name": "RBRACE", "pattern": "\\}", "skip": False},
    {"name": "SEMI", "pattern": ";", "skip": False},
    {"name": "WS", "pattern": "[ \\t\\n\\r]+", "skip": True},
]

EXPR_LL = """E  -> T E'
E' -> + T E' | - T E' | \u03b5
T  -> F T'
T' -> * F T' | / F T' | \u03b5
F  -> ( E ) | id | num"""

EXPR_SLR = """E -> E + T | E - T | T
T -> T * F | T / F | F
F -> ( E ) | id | num"""

ASSIGN_LL = """S  -> id = E ;
E  -> T E'
E' -> + T E' | - T E' | \u03b5
T  -> F T'
T' -> * F T' | / F T' | \u03b5
F  -> ( E ) | id | num"""

STMT_LL = """S  -> id = E ; | print ( E ) ;
E  -> T E'
E' -> + T E' | - T E' | \u03b5
T  -> F T'
T' -> * F T' | / F T' | \u03b5
F  -> ( E ) | id | num"""

BALANCED = """S -> ( S ) S | \u03b5"""

DANGLING = """S -> if E then S | if E then S else S | other
E -> cond"""

AMBIGUOUS = """E -> E + E | E * E | id"""

POINTER_ASSIGN = """S -> L = R | R
L -> * R | id
R -> L"""

LR1_NOT_LALR = """S -> a A d | b B d | a B e | b A e
A -> c
B -> c"""

UNIT_CYCLE = """S -> A
A -> B | a
B -> A | b"""

TOKEN_MAP_ARITH = {
    "ID": "id",
    "NUM": "num",
    "PLUS": "+",
    "MINUS": "-",
    "STAR": "*",
    "SLASH": "/",
    "LPAREN": "(",
    "RPAREN": ")",
    "ASSIGN": "=",
    "SEMI": ";",
}


EXAMPLES: list[dict[str, Any]] = [
    {
        "id": "lex-arithmetic",
        "title": "Arithmetic stream",
        "kind": "lexer",
        "kicker": "LEX / 01",
        "tagline": "Maximal munch on a numeric expression",
        "description": "Identifiers, numbers, operators and whitespace are separated into a precise token stream.",
        "tags": ["maximal munch", "operators", "positions"],
        "difficulty": "intro",
        "payload": {
            "source": "total = price * 12 + tax;",
            "rules": ARITH_RULES,
        },
    },
    {
        "id": "lex-declarations",
        "title": "Declarations and literals",
        "kind": "lexer",
        "kicker": "LEX / 02",
        "tagline": "Keywords, strings and fractional numbers",
        "description": "A small declaration language with keyword priority, string literals and decimal numbers.",
        "tags": ["keywords", "strings", "priority"],
        "difficulty": "intro",
        "payload": {
            "source": 'let ratio = 3.14;\nconst label = "parse lab";\nlet empty = 0;',
            "rules": DECL_RULES,
        },
    },
    {
        "id": "lex-control",
        "title": "Control flow with an error",
        "kind": "lexer",
        "kicker": "LEX / 03",
        "tagline": "Keywords, two-character operators and a deliberate fault",
        "description": "Includes an illegal character so the error path and source highlighting can be inspected.",
        "tags": ["keywords", "errors", "maximal munch"],
        "difficulty": "intermediate",
        "payload": {
            "source": "if (count == 10) {\n  return count @ 2;\n}",
            "rules": CONTROL_RULES,
        },
    },
    {
        "id": "regex-abb",
        "title": "The classic (a|b)*abb",
        "kind": "regex",
        "kicker": "AUT / 01",
        "tagline": "Thompson construction and subset construction",
        "description": "A textbook expression with a compact NFA and a five-state DFA produced by subset construction.",
        "tags": ["Thompson", "epsilon closure", "subset construction"],
        "difficulty": "intro",
        "payload": {"pattern": "(a|b)*abb"},
    },
    {
        "id": "regex-identifier",
        "title": "Identifier automaton",
        "kind": "regex",
        "kicker": "AUT / 02",
        "tagline": "A lexer rule as a machine",
        "description": "Letters, digits and underscore: the automaton behind almost every programming language.",
        "tags": ["character classes", "DFA", "lexing"],
        "difficulty": "intro",
        "payload": {"pattern": "[a-zA-Z_][a-zA-Z0-9_]*"},
    },
    {
        "id": "regex-number",
        "title": "Decimal number",
        "kind": "regex",
        "kicker": "AUT / 03",
        "tagline": "Optional fractions, real states",
        "description": "Integer and fractional parts with an optional decimal point and exponent-free syntax.",
        "tags": ["optional", "classes", "DFA"],
        "difficulty": "intermediate",
        "payload": {"pattern": "[0-9]+(\\.[0-9]+)?"},
    },
    {
        "id": "regex-binary",
        "title": "Binary strings ending in 11",
        "kind": "regex",
        "kicker": "AUT / 04",
        "tagline": "Watch a DFA remember two bits",
        "description": "A four-state language that demonstrates how states encode memory.",
        "tags": ["DFA", "memory", "acceptance"],
        "difficulty": "intro",
        "payload": {"pattern": "(0|1)*11"},
    },
    {
        "id": "grammar-expression-ll",
        "title": "Expression grammar (LL)",
        "kind": "grammar",
        "kicker": "GRM / 01",
        "tagline": "Left-factored and ready for predictive parsing",
        "description": "The classic expression grammar rewritten without left recursion so FIRST and FOLLOW can drive LL(1).",
        "tags": ["FIRST", "FOLLOW", "LL(1)"],
        "difficulty": "intro",
        "payload": {"grammar": EXPR_LL, "input": "id + id * id"},
    },
    {
        "id": "grammar-expression-slr",
        "title": "Expression grammar (SLR)",
        "kind": "grammar",
        "kicker": "GRM / 02",
        "tagline": "Left recursion is welcome here",
        "description": "The canonical left-recursive expression grammar used by bottom-up parsers.",
        "tags": ["left recursion", "SLR", "precedence"],
        "difficulty": "intro",
        "payload": {"grammar": EXPR_SLR, "input": "id + id * id"},
    },
    {
        "id": "grammar-balanced",
        "title": "Balanced parentheses",
        "kind": "grammar",
        "kicker": "GRM / 03",
        "tagline": "Epsilon, recursion and a nullable start symbol",
        "description": "A tiny grammar where epsilon handling is impossible to avoid.",
        "tags": ["epsilon", "nullable", "recursion"],
        "difficulty": "intro",
        "payload": {"grammar": BALANCED, "input": "( ( ) ) ( )"},
    },
    {
        "id": "grammar-dangling",
        "title": "Dangling else",
        "kind": "grammar",
        "kicker": "GRM / 04",
        "tagline": "A famous conflict, made visible",
        "description": "The dangling-else grammar is structurally valid but produces an SLR shift/reduce conflict.",
        "tags": ["conflict", "ambiguity", "SLR"],
        "difficulty": "advanced",
        "payload": {"grammar": DANGLING, "input": "if cond then if cond then other else other"},
    },
    {
        "id": "grammar-ambiguous",
        "title": "Ambiguous arithmetic",
        "kind": "grammar",
        "kicker": "GRM / 05",
        "tagline": "Two parse trees for one string",
        "description": "E -> E + E | E * E | id has no precedence. The SLR table shows exactly where the choice explodes.",
        "tags": ["ambiguity", "shift/reduce", "conflict"],
        "difficulty": "advanced",
        "payload": {"grammar": AMBIGUOUS, "input": "id + id * id"},
    },
    {
        "id": "grammar-unit-cycle",
        "title": "Unit-production cycle",
        "kind": "grammar",
        "kicker": "GRM / 06",
        "tagline": "A grammar detective case",
        "description": "A -> B and B -> A. The diagnostic engine flags the cycle before parsing begins.",
        "tags": ["diagnostics", "cycle", "validation"],
        "difficulty": "intermediate",
        "payload": {"grammar": UNIT_CYCLE, "input": "a"},
    },
    {
        "id": "ll-expression",
        "title": "Predictive expression parser",
        "kind": "ll1",
        "kicker": "LL / 01",
        "tagline": "One table cell, one decision",
        "description": "Run id + id * id through a real LL(1) table and watch the stack shrink.",
        "tags": ["LL(1)", "stack", "table"],
        "difficulty": "intro",
        "payload": {"grammar": EXPR_LL, "input": "id + id * id"},
    },
    {
        "id": "ll-statements",
        "title": "Assignment or print",
        "kind": "ll1",
        "kicker": "LL / 02",
        "tagline": "Two statement forms, one lookahead",
        "description": "A statement grammar with assignment and print forms. Follow the lookahead to the correct row.",
        "tags": ["LL(1)", "statements", "lookahead"],
        "difficulty": "intermediate",
        "payload": {"grammar": STMT_LL, "input": "id = id + num ;"},
    },
    {
        "id": "slr-expression",
        "title": "SLR expression parser",
        "kind": "slr",
        "kicker": "SLR / 01",
        "tagline": "States, items and GOTO",
        "description": "The full LR(0) automaton for the expression grammar, with a conflict-free ACTION/GOTO table.",
        "tags": ["LR(0)", "SLR", "ACTION/GOTO"],
        "difficulty": "intermediate",
        "payload": {"grammar": EXPR_SLR, "input": "id + id * id"},
    },
    {
        "id": "slr-assignment",
        "title": "Assignment statement (SLR)",
        "kind": "slr",
        "kicker": "SLR / 02",
        "tagline": "A complete assignment goes through the automaton",
        "description": "S -> id = E ; | E ; with a full expression grammar. Observe the reduce chain.",
        "tags": ["SLR", "assignment", "reductions"],
        "difficulty": "advanced",
        "payload": {"grammar": ASSIGN_LL, "input": "id = id + num * id ;"},
    },
    {
        "id": "lalr-pointer-assignment",
        "title": "Pointer assignment: LALR beats SLR",
        "kind": "slr",
        "kicker": "LR / 03",
        "tagline": "The Dragon Book's favourite counter-example",
        "description": "S -> L = R | R with C-style pointers. SLR reports a shift/reduce conflict on '=' because = is in FOLLOW(R); LALR(1) lookaheads show the reduction is never needed there.",
        "tags": ["LALR(1)", "SLR conflict", "lookaheads"],
        "difficulty": "advanced",
        "payload": {"grammar": POINTER_ASSIGN, "input": "* id = id", "method": "lalr"},
    },
    {
        "id": "lr1-not-lalr",
        "title": "Where LALR merging fails",
        "kind": "slr",
        "kicker": "LR / 04",
        "tagline": "Canonical LR(1) is strictly stronger",
        "description": "Two LR(1) states share a core but disagree on lookaheads. Merging them for LALR(1) creates a reduce/reduce conflict; canonical LR(1) keeps them apart.",
        "tags": ["LR(1)", "LALR(1)", "reduce/reduce"],
        "difficulty": "advanced",
        "payload": {"grammar": LR1_NOT_LALR, "input": "a c d", "method": "lr1"},
    },
    {
        "id": "time-arith-ll",
        "title": "a + b * c, end to end",
        "kind": "timemachine",
        "kicker": "TM / 01",
        "tagline": "Characters to parse tree in one trace",
        "description": "The signature journey: source code, tokens, grammar, LL(1) decisions, tree growth and acceptance.",
        "tags": ["time machine", "LL(1)", "parse tree"],
        "difficulty": "intro",
        "payload": {
            "source": "x + y * z",
            "rules": ARITH_RULES,
            "grammar": EXPR_LL,
            "mode": "ll",
            "tokenMap": TOKEN_MAP_ARITH,
        },
    },
    {
        "id": "time-assignment-ll",
        "title": "A full assignment, end to end",
        "kind": "timemachine",
        "kicker": "TM / 02",
        "tagline": "Lexing, FIRST/FOLLOW, and a larger tree",
        "description": "total = price * 12 + tax ; travels from characters to a complete assignment tree.",
        "tags": ["time machine", "LL(1)", "assignment"],
        "difficulty": "intermediate",
        "payload": {
            "source": "total = price * 12 + tax;",
            "rules": ARITH_RULES,
            "grammar": ASSIGN_LL,
            "mode": "ll",
            "tokenMap": TOKEN_MAP_ARITH,
        },
    },
    {
        "id": "time-arith-slr",
        "title": "Bottom-up journey",
        "kind": "timemachine",
        "kicker": "TM / 03",
        "tagline": "Shift, reduce, accept",
        "description": "The same expression, parsed by SLR: watch states and symbols accumulate on the stack.",
        "tags": ["time machine", "SLR", "shift/reduce"],
        "difficulty": "intermediate",
        "payload": {
            "source": "( x + y ) * z",
            "rules": ARITH_RULES,
            "grammar": EXPR_SLR,
            "mode": "slr",
            "tokenMap": TOKEN_MAP_ARITH,
        },
    },
    {
        "id": "time-rejected",
        "title": "A journey that fails",
        "kind": "timemachine",
        "kicker": "TM / 04",
        "tagline": "Failure is information",
        "description": "x + * y cannot be lexed into a legal expression. See exactly where the front end stops and why.",
        "tags": ["time machine", "errors", "diagnostics"],
        "difficulty": "intro",
        "payload": {
            "source": "x + * y",
            "rules": ARITH_RULES,
            "grammar": EXPR_LL,
            "mode": "ll",
            "tokenMap": TOKEN_MAP_ARITH,
        },
    },
]


def list_examples() -> list[dict[str, Any]]:
    return EXAMPLES


def get_example(example_id: str) -> dict[str, Any] | None:
    return next((e for e in EXAMPLES if e["id"] == example_id), None)
