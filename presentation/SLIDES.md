# ParseLab: Presentation Slide Deck

Slide-by-slide content for building the PowerPoint. Each slide has:

- **On the slide:** the text to put on the slide (kept short on purpose)
- **Visual:** which image from `presentation/screenshots/` to use
- **Speaker notes:** what to say (paste into the PowerPoint *Notes* box)

**Length:** 14 slides, about 10–12 minutes including a live demo.

---

## Design kit (to match the app)

| Element | Value |
|---|---|
| Background | Off-white `#F4F2EB` (dark slides: `#252620`) |
| Text | Near-black `#242520` |
| Accent 1 (highlights, key numbers) | Orange `#DF553A` |
| Accent 2 (success, ✓) | Olive `#6C7A35` or lime `#CCE36D` on dark slides |
| Headings font | **Manrope** (fallback: Segoe UI Semibold) |
| Body font | **DM Sans** (fallback: Segoe UI) |
| Code / labels font | **DM Mono** (fallback: Consolas) |

**Tips:**

- Use at most 3–4 bullets per slide. Let the screenshots do the talking.
- Put small monospace labels above titles (e.g. `01 · THE PROBLEM`) to echo the app's style.
- Screenshots are 2× resolution, so they stay sharp when enlarged.

---

## Slide 1: Title

**On the slide**

> # ParseLab
> ### An interactive laboratory for compiler front ends
> See how languages come to life: from characters to parse trees, one decision at a time.
>
> *Your name · Roll no. · Course: Compiler Construction · Instructor's name · Date*

**Visual:** `01-overview-hero.png` (full-bleed on the right half, or as the background with a dark overlay)

**Speaker notes**
> "Good morning. My project is ParseLab, an interactive lab that shows exactly how a compiler reads a program. Every result you'll see today is computed live by an engine I built, not pre-recorded."

---

## Slide 2: The problem

`01 · THE PROBLEM`

**On the slide**

> ## Compiler theory is hard to *see*
> - Each topic (regex, automata, grammars, parsers) is taught **separately**
> - Textbooks show **one solved example**, only the final table or tree
> - Students rarely see **why** each decision is made, or how the stages **connect**

**Visual:** none, or a simple icon row: 📄 regex · ⚙️ automata · 📐 grammar · 🌳 parser, with broken links between them

**Speaker notes**
> "In class we learn regular expressions, automata, FIRST and FOLLOW sets and parsing tables, each in isolation, usually from a single solved example. What's missing is the ability to try *your own* input and watch every step, and to see how one stage feeds the next."

---

## Slide 3: What is a compiler front end?

`02 · BACKGROUND`

**On the slide**

> ## Reading a program, like reading a sentence
>
> `price + tax * rate`
>
> | Step | What happens | Compiler name |
> |---|---|---|
> | 1 | Group characters into words | **Lexical analysis** |
> | 2 | Check the word order against rules | **Parsing** |
> | 3 | Build the structure | **Parse tree** |

**Visual:** `02-live-pipeline-scan.png` (small) or a hand-drawn tree: `E → T + T`, `T → id * id`

**Speaker notes**
> "When you read *price plus tax times rate*, you group letters into words, check the grammar, and understand that multiplication happens first. A compiler does the same thing with precise rules: the lexer finds the words, and the parser checks the structure and builds a tree."

---

## Slide 4: The solution

`03 · THE SOLUTION`

**On the slide**

> ## ParseLab: type anything, see everything
> - ✅ Computes results **live** for any grammar, regex or program
> - ✅ Shows **every intermediate step**, each with a reason
> - ✅ **Connects** all stages: characters → tokens → grammar → tree
> - ✅ Play, pause, **rewind** and step through any process

**Visual:** `01-overview-hero.png`

**Speaker notes**
> "ParseLab has one bench for each stage of the front end, plus a Time Machine that ties them together. You type an input, the engine computes the answer, and the interface shows every decision, so you can see *why*, not just *what*."

---

## Slide 5: Architecture

`04 · HOW IT'S BUILT`

**On the slide**

> ## Two parts, one rule
>
> ```
>  Browser (React)  ──JSON──►  Engine (Python · FastAPI)
>  draws results    ◄──────    runs every algorithm
> ```
> - **Frontend:** React 19 + Vite, hand-drawn SVG diagrams
> - **Backend:** Python 3.12, FastAPI, 14 API endpoints, 8 engine source files
> - **Rule:** the browser never computes results. *Every number comes from the real algorithm.*

**Visual:** recreate the box diagram with PowerPoint shapes (two rounded rectangles + two arrows)

**Speaker notes**
> "The project has two halves. The Python engine runs all the compiler algorithms; the React interface only displays what the engine returns. That separation guarantees every table and tree on screen comes from the real algorithm. A typical analysis takes 10 to 20 milliseconds."

---

## Slide 6: Lexical analysis and automata

`05 · FROM PATTERNS TO MACHINES`

**On the slide**

> ## Regex → NFA → DFA → Minimal DFA
> - **Thompson's construction** builds an NFA
> - **Subset construction** makes it deterministic
> - **Partition refinement** minimizes it
> - `(a|b)*abb`: **14 → 5 → 4 states** (matches the textbook)
> - Lexer uses **maximal munch**: longest match wins, earlier rule breaks ties

**Visual:** `08-automata-minimal-dfa.png` (main), `07-automata-nfa.png` (small inset)

**Speaker notes**
> "A token rule is a regular expression. ParseLab turns it into a state machine in three steps, and you can toggle between them. For the classic pattern a-or-b-star-abb, 14 NFA states become 5 DFA states and then 4 after minimization, exactly the textbook answer. Here I tested 'abab': the path is highlighted, and each arrow shows the step number that used it."

---

## Slide 7: Grammar workbench

`06 · UNDERSTANDING A GRAMMAR`

**On the slide**

> ## Analyze, fix and test a grammar
> - **FIRST / FOLLOW** sets, with the reason for every entry
> - **Diagnostics:** left recursion (incl. *hidden*), unreachable rules, cycles
> - **One-click transforms:** eliminate left recursion, left factoring
> - **Derive a sentence:** generates valid examples and proves them with derivations + tree

**Visual:** `10-grammar-workbench.png` (main), `11-grammar-transform.png` or `12-grammar-derive.png` (inset)

**Speaker notes**
> "The grammar workbench checks a grammar for problems. For the classic expression grammar, it notes that left recursion blocks LL(1) parsing, and one click rewrites it into an equivalent LL(1) grammar, explaining each step. It can also invent valid sentences from any grammar and prove them with a derivation and a parse tree."

---

## Slide 8: Top-down parsing, LL(1)

`07 · PREDICTIVE PARSING`

**On the slide**

> ## LL(1): predict the rule from one lookahead token
> - Table built from **FIRST** and **FOLLOW**
> - Step-by-step trace: **stack · remaining input · action**
> - The active **table cell is highlighted** at each step
> - Parse tree shown **complete** or **growing with the steps**

**Visual:** `13-ll1-table-and-trace.png`

**Speaker notes**
> "An LL(1) parser builds the tree from the top down. At each step it looks at one upcoming token and the table tells it which rule to use. Here we're at step 7: the parser matched the plus sign, which is highlighted in the tree. I can press play and watch all 17 steps."

---

## Slide 9: Bottom-up parsing, SLR vs LALR vs LR(1)

`08 · THE LR FAMILY`

**On the slide**

> ## Three bottom-up parsers, side by side
>
> | | SLR(1) | LALR(1) | LR(1) |
> |---|---|---|---|
> | Lookahead | FOLLOW set | merged precise | precise |
> | Power | lowest | middle | highest |
> | Used by | teaching | **yacc / bison** | theory |
>
> `S → L = R | R`: **SLR ✗ · LALR ✓ (10 states) · LR(1) ✓ (14 states)**

**Visual:** `15-lr-class-strip.png` (main), `16-lr-lalr-page.png` (optional second slide)

**Speaker notes**
> "Real compiler tools use bottom-up parsers. ParseLab implements all three classic variants. This pointer-assignment grammar from the Dragon Book shows why they exist: SLR has a conflict, but LALR solves it with the same number of states, which is exactly why yacc and bison use LALR. Another experiment shows a grammar only full LR(1) can handle."

---

## Slide 10: The Time Machine ⭐

`09 · THE SIGNATURE FEATURE`

**On the slide**

> ## One compilation. Every stage. Rewindable.
> - Records a **complete, real compilation**: source → tokens → parse → tree → verdict
> - Drag the timeline to **any moment** and see every stage at that instant
> - **Cause and effect linked:** parse step ↔ token ↔ source characters
> - Every frame explains **Why** and **Next**; switch **LL(1) ↔ SLR** on the same program

**Visual:** `17-time-machine.png`

**Speaker notes**
> "This is the signature feature. Instead of separate topics, the Time Machine records one full compilation and lets you travel through it. At frame 21, the source highlights the character *y*, the token strip highlights the matching token, and the tree highlights the nodes just built. Every frame explains why it happened. It's like a match replay with commentary. When a program fails, you can step to the exact moment it went wrong."

---

## Slide 11: Live demo

`10 · LIVE DEMO`

**On the slide**

> ## Live demo
> 1. Overview: type an expression → watch it compile
> 2. Try an error: `a + @ b`, `x * (y + z`
> 3. Grammar: eliminate left recursion → derive a sentence
> 4. LR: *LALR beats SLR* experiment
> 5. Time Machine: rewind a compilation

**Visual:** `04-live-pipeline-error.png` (as a backup in case the demo fails)

**Speaker notes**
> Switch to the browser (http://localhost:5173). Follow the 7-minute script in `PROJECT_GUIDE.md`, Section 11. If anything goes wrong, use the screenshots on slides 6–10 as a fallback.
>
> **Before presenting:** start both servers (backend on port 8001, frontend on port 5173), open the Overview page, and set the theme you want.

---

## Slide 12: Correctness and testing

`11 · IS IT CORRECT?`

**On the slide**

> ## Verified against textbook answers
> - **63 automated tests**, running in under 1 second
> - `(a|b)*abb` → **4**-state minimal DFA ✓
> - Expression grammar → **12** LALR / **22** LR(1) states ✓
> - Dragon Book **Ex. 4.20** (left recursion) and **Ex. 4.48** (LALR vs SLR) ✓
> - Minimization checked on **1,000 random strings**; every generated sentence re-verified

**Visual:** a screenshot of the terminal showing `63 passed` (run `python -m pytest -q` in `backend/`)

**Speaker notes**
> "To make sure the engine is correct, I wrote 63 tests that compare its output with answers from the textbook. For example, the minimal DFA and the LR state counts match exactly. The minimizer is also tested on a thousand random strings to confirm the smaller machine accepts exactly the same language."

---

## Slide 13: Bugs found and fixed

`12 · ENGINEERING`

**On the slide**

> ## Testing found real bugs, now fixed
> - ❌ Programs with **illegal characters were accepted** → ✅ lexer halts with an exact error
> - ❌ `ab|.c` **rejected "ac"** (wildcard bug in subset construction) → ✅ fixed
> - ❌ `//.*` comments **swallowed the whole file** → ✅ `.` no longer matches newline
> - ❌ **Hidden left recursion** went undetected → ✅ detected
> - Each fix is protected by a **regression test**

**Visual:** optional before/after pair, e.g. `04-live-pipeline-error.png` showing the lexical error

**Speaker notes**
> "Testing also uncovered real logic bugs. The most serious: a program containing an illegal character was still reported as Accepted, because the bad character was silently skipped. Now the lexer stops with the exact line and column. Each bug has a test so it can't come back."

---

## Slide 14: Conclusion and Q&A

`13 · SUMMARY`

**On the slide**

> ## ParseLab in numbers
> **6** interactive benches · **4** parsers (LL(1), SLR, LALR, LR(1)) · **17** computation modules · **23** ready-made experiments · **63** tests
>
> Plus: dark mode · share links · export trees to **SVG / PNG / LaTeX** · works on phones
>
> **Future work:** semantic analysis · code generation · LL(k) / GLR for ambiguous grammars
>
> # Thank you. Questions?

**Visual:** `18-dark-mode.png` (shows polish), or a collage of 3–4 small screenshots

**Speaker notes**
> "To summarize: ParseLab makes the whole compiler front end visible, interactive and verifiable, from regular expressions to LR(1) parsing, connected by the Time Machine. Thank you. I'm happy to take questions."
>
> Likely questions and prepared answers are in `PROJECT_GUIDE.md`, Section 12.

---

## Screenshot index

All files are in `presentation/screenshots/` (2× resolution PNG).

| File | Shows | Used on slide |
|---|---|---|
| `01-overview-hero.png` | Home page with the live pipeline (tree stage) | 1, 4 |
| `02-live-pipeline-scan.png` | Pipeline scanning characters (maximal munch) | 3 |
| `03-live-pipeline-parse.png` | Pipeline showing the parser stack | optional |
| `04-live-pipeline-error.png` | Lexical error on `a + @ b` | 11, 13 |
| `05-journey-automata.png` | Overview journey: the DFA that read a token | optional |
| `06-journey-grammar.png` | Overview journey: grammar rules used | optional |
| `07-automata-nfa.png` | Thompson NFA | 6 |
| `08-automata-minimal-dfa.png` | Minimal DFA with highlighted path | 6 |
| `09-lexer.png` | Lexical analysis page | optional |
| `10-grammar-workbench.png` | Grammar workbench overview | 7 |
| `11-grammar-transform.png` | Left-recursion elimination steps | 7 |
| `12-grammar-derive.png` | Derive a sentence + parse tree | 7 |
| `13-ll1-table-and-trace.png` | LL(1) table, trace and tree | 8 |
| `14-experiments.png` | Experiments library | optional |
| `15-lr-class-strip.png` | LL / SLR / LALR / LR(1) verdict strip | 9 |
| `16-lr-lalr-page.png` | Full LALR page | 9 (optional) |
| `17-time-machine.png` | Time Machine at frame 21 | 10 |
| `18-dark-mode.png` | Dark theme | 14 |

> To retake screenshots with your own inputs, use **Windows + Shift + S** while the app is open.
