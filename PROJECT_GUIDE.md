# ParseLab: Project Guide

**An interactive laboratory that shows, step by step, how a compiler reads and understands a program.**

This guide explains the whole project at two depths:

- 🟢 **Plain-language parts** are for readers with no programming background.
- 🔵 **Technical parts** are for readers who want the exact algorithms, files and data flow.

You can read only the 🟢 parts and still understand what the project does and why it matters.

---

## Contents

1. [ParseLab in one minute](#1-parselab-in-one-minute)
2. [What is a compiler front end? (no jargon)](#2-what-is-a-compiler-front-end-no-jargon)
3. [How the project is built](#3-how-the-project-is-built)
4. [A tour of every page](#4-a-tour-of-every-page)
5. [The Time Machine: why it exists](#5-the-time-machine-why-it-exists)
6. [Behind the scenes: the backend engine](#6-behind-the-scenes-the-backend-engine)
7. [The algorithms, explained twice](#7-the-algorithms-explained-twice)
8. [The frontend (what runs in the browser)](#8-the-frontend-what-runs-in-the-browser)
9. [Testing and quality](#9-testing-and-quality)
10. [How to run it](#10-how-to-run-it)
11. [Suggested presentation flow (7 minutes)](#11-suggested-presentation-flow-7-minutes)
12. [Likely questions and answers](#12-likely-questions-and-answers)
13. [Glossary](#13-glossary)

---

## 1. ParseLab in one minute

🟢 When you write a program, the computer does not understand it immediately. A **compiler** first has to *read* it: split the text into words, check that the words are arranged correctly, and build a structured picture of what the program means. This reading phase is called the **front end** of a compiler.

Normally this happens invisibly in a fraction of a second. **ParseLab makes it visible.** You type a small program or a grammar, and ParseLab shows every decision the compiler makes and *why* it made it, as tables, diagrams, animated trees and a step-by-step replay.

**What makes it different from a textbook:**

| A textbook shows… | ParseLab does… |
|---|---|
| One fixed example, already solved | Computes the answer live for **any input you type** |
| The final table or tree | Every **intermediate step**, with a reason for each one |
| Each topic in isolation | Connects all stages: characters → tokens → grammar → parse tree |
| Static pictures | Animations you can **play, pause, rewind and step through** |

Everything on screen is computed by a real engine written for this project. Nothing is pre-recorded or faked.

---

## 2. What is a compiler front end? (no jargon)

🟢 Think about how *you* read this English sentence:

> `price + tax * rate`

1. **You see letters and symbols.** (`p`, `r`, `i`, `c`, `e`, space, `+`, …)
2. **You group them into words.** (`price`, `+`, `tax`, `*`, `rate`) → this is **lexical analysis**.
3. **You check the words follow grammar rules.** ("a word, then an operator, then a word" is allowed) → this is **syntax analysis / parsing**.
4. **You understand the structure.** You know `tax * rate` happens *before* the `+`, because multiplication binds tighter → this is the **parse tree**.

A compiler does exactly these steps, but with precise mathematical rules:

```
   "price + tax * rate"          ← 1. raw characters (Source)
            │
            ▼  LEXER  (uses regular expressions / automata)
   ID  PLUS  ID  STAR  ID         ← 2. tokens (words)
            │
            ▼  PARSER (uses a grammar)
            E                     ← 3. parse tree (structure)
          / | \
         T  +  T
         |    /|\
        id  id * id
```

If the input breaks the rules (for example `price + * rate`), the parser stops and reports **exactly where and why**.

ParseLab has one "bench" (page) for each of these steps, plus the **Time Machine**, which connects them all.

---

## 3. How the project is built

🟢 ParseLab has two halves that talk to each other:

- The **engine** (backend) does all the thinking: it runs the compiler algorithms.
- The **interface** (frontend) is the website you click on. It sends your input to the engine and draws the results.

```
 ┌──────────────────────────────┐        JSON over HTTP         ┌───────────────────────────────┐
 │  FRONTEND  (browser)         │  ───── "analyze this" ──────► │  BACKEND  (Python engine)     │
 │  React + Vite                │                               │  FastAPI web server           │
 │  • editors and inputs        │  ◄──── full results + trace ─ │  • regex → NFA → DFA          │
 │  • tables, graphs, trees     │                               │  • lexer                      │
 │  • animations, step controls │                               │  • grammar analysis           │
 │  • light / dark theme        │                               │  • LL(1), SLR, LALR, LR(1)    │
 └──────────────────────────────┘                               │  • Time Machine trace builder │
          port 5173                                             └───────────────────────────────┘
                                                                          port 8001
```

🔵 **Technology choices**

| Layer | Technology | Why |
|---|---|---|
| Engine | Python 3.12, **FastAPI**, Uvicorn | Clear, readable algorithm code; FastAPI gives automatic API docs at `/docs` |
| Interface | **React 19**, Vite 6, lucide-react icons | Fast, component-based UI; Vite gives instant reload during development |
| Diagrams | Hand-written **SVG** (no chart library) | Full control over automata and tree layouts |
| Tests | **pytest** (63 tests) + Playwright browser checks during development | Verifies algorithms against textbook answers |

**Important design rule:** the frontend never computes compiler results itself. It only displays what the engine returns. This guarantees every number on screen comes from the real algorithm.

🔵 **Folder layout**

```
CC Project/
├── backend/
│   ├── app/
│   │   ├── main.py              ← web server: defines all API endpoints
│   │   ├── examples.py          ← 23 ready-made experiments
│   │   └── core/                ← the compiler engine
│   │       ├── regex_engine.py  ← regex parser, Thompson NFA, subset DFA, DFA minimization
│   │       ├── lexer.py         ← tokenizer (maximal munch)
│   │       ├── grammar.py       ← grammar parsing, FIRST/FOLLOW, diagnostics, transforms, sample sentences
│   │       ├── ll1.py           ← LL(1) table + predictive parser
│   │       ├── slr.py           ← LR(0) automaton, SLR(1) table + shift/reduce parser
│   │       ├── lr1.py           ← canonical LR(1), LALR(1), parser-class comparison
│   │       ├── trees.py         ← parse-tree building + leftmost/rightmost derivations
│   │       └── timemachine.py   ← joins every stage into one synchronized trace
│   ├── tests/                   ← 63 automated tests
│   ├── requirements.txt         ← runtime packages
│   └── requirements-dev.txt     ← test packages
├── frontend/
│   ├── src/
│   │   ├── main.jsx             ← the whole interface (all pages and components)
│   │   ├── style.css, extra.css ← light theme styles
│   │   └── dark.css             ← dark theme (generated automatically)
│   ├── scripts/gen-dark-theme.mjs ← builds dark.css from the light styles
│   └── dist/                    ← production build (served by the backend)
├── README.md                    ← short setup instructions
└── PROJECT_GUIDE.md             ← this document
```

---

## 4. A tour of every page

Each page follows the same layout: an **editor** on the left (where you type), **results** below it, and **Field notes** on the right (a short explanation of the concept). Every page has **Run analysis** (or `Ctrl + Enter`), **Reset** (restore the default example) and **Share** (copy a link to this exact experiment).

### 4.1 Overview (home page)

🟢 **Purpose:** a guided introduction. It shows the whole compiler journey on a single input *before* you open any detailed page.

**What you can do:**

- **Live pipeline (top right).** Type any arithmetic expression, such as `(a + b) * 2`. The real engine compiles it as you type, and the card animates through four stages:
  1. **Scan:** a cursor moves across the characters, showing which rule recognised each word and the automaton states it passed through.
  2. **Tokens:** the recognised words appear one by one.
  3. **Parse:** the parser's stack and its decision at every step.
  4. **Tree:** the parse tree grows node by node.

  The footer shows real statistics (e.g. *5 tokens · 17 parse steps · 19 nodes · 10 ms*). Try the presets *missing )* or *bad character* to see how errors are reported.
- **"One input. Many transformations."** Five tabs follow *your* expression through each stage:
  - Source: hover any character to see its position.
  - Tokens: a table explaining each token.
  - Automata: pick a token to see the exact state machine that recognised it.
  - Grammar: which grammar rules were used, and how many times.
  - Parse tree: the full tree and its derivations.
- **Choose your instrument.** Cards for each bench, with an animated preview on hover. Press keys **1–6** to open one.
- **Experiments.** Filter the 23 ready-made experiments by topic, or click **Surprise me**.

🔵 Behind the scenes, the hero calls `POST /api/timemachine` with a fixed expression grammar and lexer rules, then animates the returned trace on the client. The Automata tab calls `POST /api/regex/analyze` for the selected token's rule; the Grammar tab calls `POST /api/grammar/analyze`.

---

### 4.2 Lexical analysis

🟢 **Purpose:** turn raw text into a list of meaningful "words" (tokens).

**What you do:** define token rules (for example, *an identifier is a letter followed by letters or digits*), then type some source code.

**What you see:**

- The source text with every token highlighted. Click one to inspect it.
- A table of tokens with their type, text, line and column.
- Clear errors for characters no rule can recognise (for example `@`).

**Key idea: "maximal munch".** At each position, the lexer takes the **longest** possible match. That is why `count1` becomes one identifier, not `count` + `1`. If two rules match the same length, the rule **listed first** wins. That is how keywords like `if` beat the general identifier rule.

🔵 **How it works** (`backend/app/core/lexer.py`):

1. Each rule's regular expression is compiled to a **DFA** by the regex engine.
2. At each position, every DFA is run forward and the longest accepting prefix is recorded (`longest_dfa_match`).
3. The longest match wins; ties go to the earlier rule.
4. Rules marked **skip** (such as whitespace or comments) advance the position but produce no token.
5. An unmatched character becomes a lexical error. The lexer records it and continues, so all errors are reported at once.

Each token records its DFA state path, the competing rules and their match lengths, and a human-readable explanation.

---

### 4.3 Automata studio

🟢 **Purpose:** show how a pattern (a *regular expression*) becomes a machine that can recognise text.

A regular expression like `(a|b)*abb` means *"any mix of a's and b's, ending in abb"*. A computer checks this with a **state machine**: circles (states) connected by arrows (transitions). You start at the first state, follow one arrow per character, and if you end on a double circle, the text matches.

**What you see:** three versions of the machine, side by side via a toggle:

| View | Meaning | For `(a|b)*abb` |
|---|---|---|
| **Thompson NFA** | First, mechanical translation; has "free" ε-moves | 14 states |
| **Subset DFA** | Deterministic: exactly one arrow per character | 5 states |
| **Minimal DFA** | The smallest possible equivalent machine | **4 states** |

**Try a string:** type `abab` in *Try a string*. The path is highlighted on the graph, each arrow is numbered with the step that used it (`#1`, `#2,4`), and the result says ACCEPTED or REJECTED. If the string gets stuck, the state where it failed gets a dashed ring.

You can also step through the **subset construction** and the **minimization rounds** one step at a time, each with an explanation.

🔵 **How it works** (`backend/app/core/regex_engine.py`):

1. **Parse** the regex into a syntax tree. Supported syntax: concatenation, `|`, `*`, `+`, `?`, `( )`, character classes `[a-z0-9_]`, negated classes `[^"]`, `.` (any character except newline), `\d \w \s \D \W \S`, escapes (`\n \t \+ …`) and `ε`.
2. **Thompson's construction** builds an ε-NFA, one small fragment per operator.
3. **Subset construction** turns sets of NFA states into DFA states using ε-closure and `move`.
4. **Moore's partition refinement** minimizes the DFA. It starts with {accepting, non-accepting} and keeps splitting groups whose transitions lead to different groups until nothing changes.

Safety limits: 2,000-character patterns and 900 states, so a malicious pattern cannot freeze the server.

---

### 4.4 Grammar workbench

🟢 **Purpose:** a grammar is the rulebook of a language, e.g. *"an expression is a term, or an expression plus a term"*. This page checks a grammar for problems, computes important sets, and can rewrite it or derive sentences from it.

**What you see:**

- **Parser-class strip:** which parsing methods can handle this grammar (LL(1), SLR(1), LALR(1), LR(1)), each with a ✓ or ✗ and a one-line verdict.
- **FIRST and FOLLOW sets:** for each rule, which words can *start* it and which words can *come after* it. Parsers use these to make decisions.
- **Diagnostics,** colour-coded:
  - **Red (error):** the grammar is broken, e.g. a rule that can never finish.
  - **Amber (note):** a limitation, e.g. *"Left recursion: blocks LL(1)"*. The grammar is valid, but one parser type can't use it as written.
- **Transforms:** one click to **eliminate left recursion** or **left-factor** the grammar, with every step explained, and **Apply to editor**.
- **Derive a sentence:** ParseLab *generates* valid example sentences from your grammar. Click one, or type your own, to see the **leftmost and rightmost derivations** and the **parse tree**. If the grammar is ambiguous, it tells you.

🔵 **How it works** (`backend/app/core/grammar.py`):

- **Grammar syntax:** `A -> x y | z` (also `→`, `::=`, `:=`), alternatives on their own line starting with `|`, `ε`/`eps` for empty, `%start S`, and `//` or `#` comments.
- **Nullable, FIRST, FOLLOW:** fixed-point iteration. Rules are re-applied until no set changes, and every addition is recorded with its reason (shown under *How FIRST and FOLLOW were computed*).
- **Diagnostics:**
  - direct, indirect and *hidden* left recursion (via cycles in the left-corner graph)
  - left-factoring opportunities
  - unreachable and non-productive symbols
  - unit-production cycles
- **Left-recursion elimination:** the Dragon Book algorithm (Aho et al., Alg. 4.19), improved to substitute only rules that can actually reach the current one.
- **Left factoring:** repeatedly pulls out common prefixes into new primed non-terminals.
- **Sample sentences:**
  1. compute the shortest string each non-terminal can produce (fixed point)
  2. randomly expand from the start symbol, falling back to the shortest expansions so generation always terminates
  3. every sample is verified by the tests to be derivable
- **Derivation checking** uses canonical LR(1), the most general parser in the project (`POST /api/lr/analyze`).

---

### 4.5 LL(1) parsing (top-down)

🟢 **Purpose:** simulate a parser that reads left to right and *predicts* which grammar rule to use by looking at just **one** upcoming word.

Imagine building the tree from the **top** (the whole sentence) down to the **leaves** (the words). At each step the parser asks: *"I need an Expression, and the next word is `id`. Which rule should I use?"* It looks up the answer in a **table**.

**What you see:**

- The **parse table** (rows = grammar rules, columns = next word). Conflicts, where a cell has two answers, are shown in red with an explanation.
- A **step-by-step trace** with play/pause and ← → keys: the stack, the remaining input, the action (*expand* or *match*), and the table cell being used (highlighted).
- The **parse tree**. Show it complete, or switch to **Grow with steps** to watch it being built.
- Leftmost and rightmost derivations.

🔵 **How it works** (`backend/app/core/ll1.py`):

- **Table:** for each production `A → α`, put it in `M[A, a]` for every `a ∈ FIRST(α)`. If `α` can be empty, also put it in `M[A, b]` for every `b ∈ FOLLOW(A)`. Two productions in one cell means the grammar is **not LL(1)**.
- **Parser:** a stack initialised with `$ S`.
  - If the top of the stack is a terminal, **match** it against the input.
  - If it's a non-terminal, **expand** it using the table cell.
  - Accept when both the stack and the input reach `$`.

  Errors list the expected tokens, and a 1,200-step limit guards against runaway grammars.

---

### 4.6 LR parsing (bottom-up: SLR, LALR, LR(1))

🟢 **Purpose:** simulate the parsers that real compiler tools (yacc, bison) use. They build the tree from the **bottom** (the words) **up** to the whole sentence. They read words onto a stack (**shift**), and when the top of the stack matches a rule, they combine those pieces into a bigger one (**reduce**).

These parsers can handle more grammars than LL(1), including left-recursive ones like `E → E + T`.

**Three methods, one toggle:**

| Method | How it decides when to reduce | Power | Table size |
|---|---|---|---|
| **SLR(1)** | Reduce if the next word *can ever* follow this rule (FOLLOW set) | Lowest | Small |
| **LALR(1)** | Precise lookaheads, merged where possible | Middle (used by yacc/bison) | Small |
| **Canonical LR(1)** | Precise lookahead kept separately in every state | Highest | Large |

**What you see:** the state machine's item sets (states), the ACTION/GOTO table, conflicts explained, a step-by-step shift/reduce trace, and the parse tree. For LALR, each state shows which LR(1) states were merged into it (e.g. `I1 = 1 + 9`).

**Two classic experiments** (in *Experiments*) show why the three methods exist:

- **"Pointer assignment: LALR beats SLR"** (`S → L = R | R`): SLR has a conflict, LALR has none (10 states, merged from 14 LR(1) states).
- **"Where LALR merging fails":** LALR has a reduce/reduce conflict that only canonical LR(1) avoids.

🔵 **How it works**

- `slr.py`: LR(0) items, `closure` and `goto`, BFS over item sets, ACTION/GOTO table. Reduce actions are placed on `FOLLOW(A)`.
- `lr1.py`:
  - **LR(1) items** `[A → α·β, a]`. Closure adds `[B → ·γ, b]` for every `b ∈ FIRST(βa)`.
  - **LALR** merges LR(1) states that share the same core and unions their lookaheads.
  - `classify_grammar` builds all four tables and produces the verdict text.
- One shared shift/reduce simulator drives all three methods. Limits: 260 LR(0) states, 700 LR(1) states, 1,500 steps.

---

### 4.7 Time machine

🟢 **Purpose:** connect **every stage** into one continuous, replayable story. See [Section 5](#5-the-time-machine-why-it-exists) for the full explanation.

**What you do:**

1. Write a grammar.
2. Write a **source program**, e.g. `x + y * z`.
3. Define lexer rules, and a **token map** that connects lexer token names to grammar words (e.g. `ID → id`).
4. Choose **LL(1)** (top-down) or **SLR(1)** (bottom-up).

**What you see:** a timeline of every event, with a slider and play/pause. For each frame:

- The **stage** you are in: Source → Tokens → Grammar → Parse → Tree → Result.
- The **characters** being read, highlighted in the source.
- The **token** being consumed.
- The parser **stack** and remaining input.
- A **"Why"** and a **"Next"** explanation.
- The **parse tree** at that moment.

🔵 `backend/app/core/timemachine.py` runs the lexer, maps tokens to terminals, builds the chosen parser and simulates it. It then merges all of these into one ordered list of `steps`. Each step carries its stage, the source character range, token index, stack, table cell and created tree nodes, so the UI can synchronise every view to a single slider.

---

### 4.8 Experiments and Field notes

- **Experiments:** 23 curated, ready-to-run examples across six topics:

  | Topic | Count |
  |---|---|
  | Regex | 4 |
  | Lexer | 3 |
  | Grammar | 6 |
  | LL(1) | 2 |
  | LR | 4 |
  | Time machine | 4 |

  Each loads straight into its bench, with a title, difficulty and description. Examples include *Dangling else*, *Ambiguous arithmetic*, *Balanced parentheses* and *A journey that fails*.
- **Field notes:** a pocket reference covering each concept, the grammar notation, the regex operators, keyboard shortcuts and the grammar transforms.

### 4.9 Features available everywhere

| Feature | What it does |
|---|---|
| **Light / Dark / System theme** | Top-right switch; remembers your choice; follows Windows' theme on *System* |
| **Share link** | Copies a URL that reopens the exact experiment (grammar, input, method) |
| **Export parse tree** | Download as **SVG** or **PNG**, or copy as **LaTeX** (`qtree`) for reports |
| **Keyboard** | `Ctrl+Enter` run · `← →` step · `Space` play/pause · `1–6` open a bench (Overview) |
| **Honest status** | The editor footer shows *SYNTAX OK* or the exact error with its line number |
| **Mobile friendly** | Works at phone width with no sideways scrolling |

---

## 5. The Time Machine: why it exists

🟢 **The problem it solves.** In a compiler course, each topic (regular expressions, automata, lexers, grammars, parsers) is usually taught **separately**. Students learn each piece but often don't see **how they connect**. Questions like *"which characters produced this token?"* or *"which parser decision created this branch of the tree?"* are hard to answer from separate diagrams.

**The Time Machine answers them.** It records **one complete, real compilation** from the first character to the final verdict, and lets you **travel through it in time**:

- ⏪ **Rewind** to any moment and see the exact state of *every* stage at that moment.
- 🔗 **Cause and effect are linked.** Selecting a parse step highlights the token it consumed *and* the characters in the source that token came from.
- ❓ **Every frame explains itself** with a *Why* (the rule or table entry responsible) and a *Next* (what will happen next).
- ❌ **Failures are explained, not just reported.** In *"A journey that fails"*, you can step to the exact frame where the parser gets stuck and see what it expected.

**An analogy:** a normal compiler is like a sports result, *"Accepted"* or *"Syntax error on line 3"*. The Time Machine is the **full match replay** with commentary: you can pause on any move and see why it happened.

**Why it matters for learning:**

1. It shows the front end as **one pipeline**, not five unrelated topics.
2. It proves results: an *Accepted* verdict comes with the complete chain of evidence.
3. It lets you compare **top-down (LL)** and **bottom-up (SLR)** parsing of the *same* program by switching one toggle.

🔵 **Technically:** `run_time_machine()` produces a list of steps with `stage ∈ {source, lex, grammar, parse, tree, result}`. Each step stores `sourceRange`, `tokenIndex`, `stack`/`stateStack`, `input`, `tableCell`, `created` (tree node IDs) and `parseStep`. Each tree node stores `createdStep`, `expandedStep` and `matchedStep`, so the frontend can show the tree *as it existed* at any frame. If the lexer finds an illegal character, the machine **halts before parsing** with a precise error. An earlier version silently skipped bad characters and accepted invalid programs; that bug was found and fixed.

---

## 6. Behind the scenes: the backend engine

### 6.1 What happens when you click "Run analysis"

🟢 Step by step:

1. The browser packages your input (e.g. the grammar text and input string) as **JSON**.
2. It sends it to the engine at an address like `/api/ll1/analyze`.
3. The engine validates the input, runs the algorithm, and records every intermediate step with an explanation.
4. It sends back one JSON answer containing the results *and* the full trace.
5. The browser draws tables, graphs and trees from that answer. **No algorithm runs in the browser.**

This usually takes **10–20 milliseconds**.

### 6.2 API endpoints (all under `/api`)

Interactive documentation is generated automatically at **http://127.0.0.1:8001/docs**.

| Method | Endpoint | Input | Returns |
|---|---|---|---|
| GET | `/health` | – | Engine status, version, list of 17 modules |
| GET | `/examples`, `/examples/{id}` | – | The 23 experiments |
| POST | `/regex/analyze` | `pattern` | AST, NFA, DFA, minimal DFA, construction and minimization steps |
| POST | `/lexer/analyze` | `source`, `rules` | Tokens, errors, source spans, per-rule DFAs |
| POST | `/grammar/analyze` | `grammar` | FIRST/FOLLOW/nullable with reasons, diagnostics, sample sentences |
| POST | `/grammar/factor` | `grammar` | Left-factored grammar + steps |
| POST | `/grammar/left-recursion` | `grammar` | Left-recursion-free grammar + steps |
| POST | `/grammar/samples` | `grammar`, `seed` | Example sentences the grammar can derive |
| POST | `/grammar/classify` | `grammar` | LL(1)/SLR/LALR/LR(1) verdicts + explanation |
| POST | `/ll1/analyze` | `grammar`, `input` | LL(1) table, conflicts, parse trace, tree, derivations |
| POST | `/slr/analyze` | `grammar`, `input` | LR(0) automaton, SLR table, trace, tree |
| POST | `/lr/analyze` | `grammar`, `input`, `method` | Same as SLR, for `slr` / `lalr` / `lr1` |
| POST | `/timemachine` | `grammar`, `source`, `rules`, `tokenMap`, `mode` | The full synchronized trace |

Bad input never crashes the server. Wrong field types return HTTP **422** with a message, and grammar or regex mistakes return `valid: false` with the line or position of the problem.

### 6.3 Example request and response

```http
POST /api/ll1/analyze
{ "grammar": "E -> T E'\nE' -> + T E' | ε\nT -> id", "input": "id + id" }
```

```jsonc
{
  "valid": true,
  "isLL1": true,
  "table": { "columns": ["+", "id", "$"], "rows": [ ... ] },
  "simulation": {
    "accepted": true,
    "steps": [
      { "action": "expand", "stack": [...], "input": ["id","+","id","$"],
        "explanation": "Table[E, id] selects E → T E'. Replace E with T E' on the stack…" },
      ...
    ],
    "tree": { "symbol": "E", "children": [ ... ] },
    "derivations": { "leftmost": {...}, "rightmost": {...} }
  }
}
```

### 6.4 Safety limits

| Limit | Value | Prevents |
|---|---|---|
| Regex length | 2,000 characters | Huge inputs |
| NFA / DFA states | 900 | Exponential blow-up |
| LR(0) / LR(1) states | 260 / 700 | Very large grammars freezing the server |
| Parse steps | 1,200 (LL) / 1,500 (LR) | Infinite loops on pathological grammars |

---

## 7. The algorithms, explained twice

| Algorithm | 🟢 In plain words | 🔵 Technically | File |
|---|---|---|---|
| **Thompson's construction** | Build a small machine for each piece of the pattern, then snap the pieces together | One NFA fragment per operator, joined by ε-transitions | `regex_engine.py` |
| **Subset construction** | Turn a "maybe in several places at once" machine into a "always in exactly one place" machine | DFA states = ε-closures of sets of NFA states; `move` + closure per symbol | `regex_engine.py` |
| **DFA minimization** | Merge states that behave identically, to get the smallest machine | Moore's partition refinement over (block, transition-signature) | `regex_engine.py` |
| **Maximal munch** | Always grab the longest word you can | Longest accepting DFA prefix; ties go to the earliest rule | `lexer.py` |
| **Nullable / FIRST / FOLLOW** | Work out what can start a rule, what can follow it, and whether it can be empty | Fixed-point iteration with recorded reasons | `grammar.py` |
| **Left-recursion elimination** | Rewrite rules like "E is E + T" so a top-down parser won't loop forever | Ordered substitution + `A → βA′`, `A′ → αA′ \| ε` | `grammar.py` |
| **Left factoring** | Pull out a shared beginning so the parser can delay its choice | Common-prefix extraction into fresh primed non-terminals | `grammar.py` |
| **LL(1) table + parser** | A lookup table says which rule to use for each next word | `M[A,a]` from FIRST/FOLLOW; stack-based predictive parser | `ll1.py` |
| **LR(0) / SLR(1)** | A state machine decides when to read a word and when to combine pieces | Item-set closure/goto; reduce on FOLLOW(A) | `slr.py` |
| **LR(1) / LALR(1)** | Same idea, but tracks exactly which word may come next, so it's more powerful | Items with a lookahead; LALR merges equal cores | `lr1.py` |
| **Derivations** | The list of rewriting steps from the start rule to the sentence | Leftmost and rightmost frontier walks over the parse tree | `trees.py` |
| **Sample sentences** | Invent valid sentences the grammar can produce | Shortest-yield fixed point + bounded random expansion | `grammar.py` |

**Verified against textbook answers** (these are checked by the automated tests):

| Input | Result | Matches |
|---|---|---|
| `(a\|b)*abb` | DFA 5 states → minimal **4** | The classic Dragon Book Chapter 3 example |
| Expression grammar `E → E + T \| T …` | **12** LR(0)/LALR states, **22** canonical LR(1) states | Standard state counts for this grammar |
| `S → L = R \| R` | Not SLR, **is LALR** (10 states from 14) | Dragon Book, Example 4.48 |
| `S → A a \| b ; A → A c \| S d \| e` | Left recursion removed exactly as in the book | Dragon Book, Example 4.20 |
| Binary multiples of 3 regex | Minimal DFA has **3** states | Standard result (one state per remainder 0, 1, 2) |

---

## 8. The frontend (what runs in the browser)

🟢 The interface is a single-page website. Clicking between pages does not reload the browser; it swaps content instantly.

🔵 **Key parts of `frontend/src/main.jsx`:**

| Component | Role |
|---|---|
| `App` | Page switching, the form state for each bench, running analyses, share links, keyboard shortcuts |
| `EditorPanel` | The editors: grammar, regex, rules, source, method/mode toggles, input |
| `LivePipeline`, `Journey`, `LaunchGrid`, `ExampleStrip` | The interactive Overview page |
| `AutomataGraph` + `layoutAutomaton` | Draws state machines: layered layout, curved edges that avoid nodes, path highlighting |
| `TreeDiagram` + `layoutTree` | Draws parse trees as SVG; full or growing view; SVG/PNG/LaTeX export |
| `ParserOutput`, `TableRenderer`, `Stepper` | Parse tables, traces, and play/pause/step controls |
| `GrammarOutput` | Grammar analysis, transforms, "Derive a sentence" |
| `TimeOutput` | The Time Machine view |
| `ThemeToggle` | Light / Dark / System |

**Other details:**

- **Dark theme generator.** `scripts/gen-dark-theme.mjs` reads every colour in the light stylesheets and produces a matching dark theme automatically before each build. It flips lightness, keeps hue and keeps accent colours. New styles therefore never miss a dark version.
- **Share links** encode the current bench's settings in the URL (`#/slr?d=…`), so opening the link restores the experiment.
- **Accessibility:** keyboard navigation, ARIA labels on graphs and controls, and reduced motion respected (animations are skipped if the operating system asks for it).

---

## 9. Testing and quality

🟢 The project includes **63 automated tests** that check the engine gives the correct answers, including textbook results computed by hand. They run in under one second.

🔵 **Test files** (`backend/tests/`):

| File | Covers |
|---|---|
| `test_regex.py` | Regex parsing, NFA/DFA correctness |
| `test_lexer.py` | Tokens, positions, maximal munch, errors |
| `test_grammar.py` | Grammar syntax, FIRST/FOLLOW, diagnostics |
| `test_ll1.py`, `test_slr.py` | Tables, conflicts, accept/reject |
| `test_lr1.py` | LR(1)/LALR state counts, LALR-vs-SLR and LR(1)-vs-LALR grammars, agreement between all parsers |
| `test_improvements.py` | Regression tests for every bug fixed (below), minimization preserving the language on random strings, transforms, sample sentences, API endpoints |

In addition, every page was exercised in a real Chrome browser during development using Playwright: clicking, typing, theme switching, exports and share links, with zero console errors. These scripts were used during development and are not part of the repository.

**Bugs found and fixed during testing** (each now has a regression test):

| Bug | Impact | Fix |
|---|---|---|
| Programs with illegal characters were **accepted** by the Time Machine | Wrong verdict | Halt with a lexical error before parsing |
| `ab\|.c` rejected `"ac"` | Wrong DFA for patterns with `.` | Wildcard transitions are included in subset construction |
| `.` matched newlines, so `//.*` comments swallowed the whole file | Wrong tokens | `.` excludes newline |
| `[^"]` didn't match tabs or newlines | Strings with tabs failed | Negated classes include whitespace |
| Hidden left recursion (`A → B A`, `B ⇒ ε`) not detected | Missed diagnostic | Detected via the left-corner graph |
| `\|` on a new line rejected | Textbook grammar layout failed | Continuation lines supported |
| `id + id*id` rejected | Mixed spacing failed | Smart tokenisation of input |
| Left recursion labelled an "error" | Valid grammars looked broken | Now a note: "blocks LL(1)" |
| Lexer rebuilt lookup tables for every character | Slow | Pre-compiled DFAs (≈2.5× faster) |

---

## 10. How to run it

**Requirements:** Python 3.10+ and Node.js 18+.

```powershell
# 1. Backend (engine): terminal 1, from the project folder
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001

# 2. Frontend (interface): terminal 2
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Keep both terminals running. Other devices on the same Wi-Fi can open `http://<this-computer's-IP>:5173`.

**Run the tests:**

```powershell
pip install -r backend\requirements-dev.txt
cd backend
python -m pytest -q
```

> Note: after changing Python code, restart the backend. The auto-reload option did not detect file changes in this folder on Windows. Frontend changes appear instantly.

---

## 11. Suggested presentation flow (7 minutes)

| Time | Show | Say |
|---|---|---|
| 0:00 | **Overview**: type `(a + b) * 2` in the live pipeline | "Everything you see is computed live by our own engine, not pre-recorded." |
| 0:45 | Click preset **bad character**, then **missing )** | "Errors are pinpointed: the lexer catches `@`; the parser explains what it expected." |
| 1:30 | Scroll to **One input, many transformations** → Automata tab, pick a token | "This is the actual minimal DFA that recognised this word, and the path it took." |
| 2:15 | **Automata studio**: `(a\|b)*abb`, toggle NFA → DFA → Minimal, try `abab` | "14 NFA states become 5 DFA states and then 4, matching the textbook." |
| 3:00 | **Grammar workbench**: default grammar → note *Blocks LL(1)* → **Eliminate left recursion** → **Apply** | "The tool rewrites the grammar and explains each step." |
| 3:45 | **Derive a sentence**: click a generated sentence | "It invents valid sentences and proves them with derivations and a tree." |
| 4:30 | **LL(1) parsing**: press ▶ on the trace | "Each step uses one table cell, highlighted here." |
| 5:15 | **Experiments → Pointer assignment: LALR beats SLR**, toggle SLR / LALR / LR(1) | "Why yacc and bison use LALR: SLR fails, LALR succeeds with the same state count." |
| 6:00 | **Time machine**: drag the slider; switch LL ↔ SLR | "The whole front end in one replay, with cause and effect linked at every frame." |
| 6:40 | Export the tree as **LaTeX**; toggle **dark mode**; show the **63 tests** passing | "Usable for reports, polished, and verified against textbook answers." |

---

## 12. Likely questions and answers

**Q: Are the results hard-coded?**
No. Every page sends your input to the Python engine, which computes the answer each time. Type any grammar or regex and the output changes accordingly.

**Q: How do you know the algorithms are correct?**
63 automated tests compare outputs with textbook answers (e.g. Dragon Book state counts). Minimization is also checked on hundreds of random strings, and every generated sample sentence is verified by the LR(1) parser.

**Q: Why include SLR, LALR and LR(1)?**
They trade power for table size. The experiments show grammars where SLR fails but LALR works, and where LALR fails but LR(1) works, demonstrating the strict hierarchy SLR ⊂ LALR ⊂ LR(1).

**Q: What is the purpose of the Time Machine?**
To show the front end as one connected pipeline and make every decision traceable from source character to parse-tree node. It is especially useful for understanding errors. See [Section 5](#5-the-time-machine-why-it-exists).

**Q: Can it handle ambiguous grammars?**
It detects them. An ambiguous grammar produces conflicts in every LR table, and the workbench explains that no deterministic one-lookahead parser exists for it as written.

**Q: What happens with bad input?**
The engine never crashes. It returns a precise message with the line (grammar) or position (regex), and the UI shows it in red in the result area and the editor footer.

**Q: What are the limitations?**
- Parsing is limited to one-token lookahead (LL(1)/LR(1) families).
- There is no semantic analysis or code generation (it is a *front-end* lab).
- The Time Machine supports LL(1) and SLR modes.
- Very large grammars hit safety limits by design.

---

## 13. Glossary

| Term | Meaning |
|---|---|
| **Compiler front end** | The part of a compiler that reads and checks the program (lexing + parsing) |
| **Token** | A "word" of a program: identifier, number, operator, … |
| **Lexeme** | The actual text of a token, e.g. `price` |
| **Regular expression** | A compact pattern describing a set of strings, e.g. `[a-z]+` |
| **NFA / DFA** | State machines; a DFA has exactly one next state per character |
| **ε (epsilon)** | The empty string; an ε-move changes state without reading anything |
| **Grammar** | Rules describing valid sentences, e.g. `E → E + T \| T` |
| **Terminal / Non-terminal** | Actual words (`id`, `+`) vs. rule names (`E`, `T`) |
| **Production** | One grammar rule, e.g. `T → T * F` |
| **Derivation** | Step-by-step rewriting from the start symbol to a sentence |
| **Parse tree** | A tree showing how a sentence is built from grammar rules |
| **FIRST / FOLLOW** | Words that can start a rule / words that can come after it |
| **Left recursion** | A rule that starts with itself (`E → E + T`); breaks top-down parsers |
| **LL(1)** | Top-down parsing, Left-to-right, Leftmost derivation, 1 lookahead token |
| **LR(1)** | Bottom-up parsing, Left-to-right, Rightmost derivation (reversed), 1 lookahead |
| **SLR / LALR** | Simpler and smaller variants of LR(1) |
| **Shift / Reduce** | Push the next word onto the stack / replace a rule's right side with its name |
| **Conflict** | A table cell with two possible actions; the parser can't decide |
| **Ambiguous grammar** | A grammar where some sentence has more than one parse tree |
| **Maximal munch** | The lexer rule "always take the longest match" |
