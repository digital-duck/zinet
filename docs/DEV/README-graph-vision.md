# The Graph Vision: graph.yaml as Universal Declarative IR

*ZiNets Ecosystem Architecture — formalized 2026-09-27*

---

## Origin: Chinese characters as decomposition graphs

ZiNets started with a simple observation: every Chinese character decomposes into smaller units — radicals → strokes → abstract primitives. That decomposition is a directed acyclic graph. The same graph that powers the ZiNets character explorer (`zinets_cache.sqlite → graph.yaml → ConceptBook navigator`) turned out to be the right data structure for everything else.

The reductionist instinct is familiar from physics: protons → quarks → fields; forces → interactions → composite systems. What ZiNets did was apply that same instinct to knowledge, code, computation, and optimization. Every complex thing decomposes into primitives, compositions, and capstone applications — and `graph.yaml` is how we model that decomposition structure.

---

## The schema: primitives → concepts → applications

```yaml
primitives:      # leaf nodes — built-in, atomic, non-decomposable
concepts:        # composed ideas — assembled from primitives + other concepts
applications:    # capstone uses — how this knowledge / code / computation  gets applied
```

This three-layer DAG maps naturally to every domain in the ecosystem:

| Tool | `primitives` | `concepts` | `applications` |
|---|---|---|---|
| SPL | built-in tools (`llm_call`, `api_call`, `cache_get`) | workflow steps, intermediate transforms | runnable recipes (e.g. `build_concept_book`) |
| Momagrid | GPU node | Hub-Spoke network | low-cost decentralized inference |
| ConceptBook | concept, atomic facts, definitions | composed ideas, theorems | capstone insights, worked examples |
| Graph-Code | leaf components, APIs | composed modules, services | deployable apps, systems |
| Solver | decision variables, parameters | constraints, derived quantities | objectives, solution targets |
| **Education** | primitive concepts (irreducible knowledge units) | prerequisite-ordered compositions | capstone mastery — the target concept the learner navigates toward |

The same `graph.yaml` validator, the same navigator (`graph.html`), and the same diff semantics work across all six domains. That is the leverage.

---

## The five-CLI ecosystem

As of 2026-09-27 the ZiNets toolchain has matured to five CLIs, all sharing `graph.yaml` as their common exchange format:

| CLI | Stack | Role | Purpose |
|---|---|---|---|
| `spl3` | SPL | workflow orchestration — the shared intelligence layer beneath `gfc` and `cba` | compute |
| `mg` | Momagrid | Grid-based distributed inference | network and compute |
| `cba` | ConceptBook App | `graph.yaml` → interactive educational concept books | learning and knowledge management |
| `gfc` | Graph-Code | `graph.yaml` → software blueprints and scaffolded apps | app builder |
| `solver` | Solver Box | `graph.yaml` → deterministic solver for real-world optimization | solution |

Each CLI is independently installable and operable, yet they compose naturally: `spl3` generates `graph.yaml`; `gfc` and `cba` consume it; `solver` uses the same format to formulate (problem, solution) pair.

---

## Two graphs, one family: knowledge and computation (2026-10-24)

The vision has become clearer with GraphLang ([`graflang`](https://github.com/digital-duck/graflang), command `graf`). There are two kinds of graph, and both live in plain YAML (the file persists the graph; the name is a convention):

| | Knowledge graph (zinet `graph.yaml`) | Computation graph (GraphLang `*.graph.yaml`) |
|---|---|---|
| What the graph is | what depends on what: a static dependency DAG, three layers | what runs and when: the program itself |
| Edges | `deps`, typed (`prerequisite`, `data_flow`, `constraint`, ...) | `triggers` (control) and `binds` (data) between **ports** |
| Cycles | forbidden | allowed (retry wires, `LOOP`) |
| Who changes it | people and tools that author knowledge | the model itself: it changes the topology (`MUTATE`) instead of writing code |
| Tools | `zinet` | `graf run`, `validate`, `compile`, `vis` |

**Interaction nets.** GraphLang's execution model comes from Lafont's *interaction nets* (Lafont, 1990): a program is a graph of agents with ports; a computation is a sequence of local rewrites where two connected agents interact; the rewrites are local, so independent ones can run in any order and still agree (confluence). That is why the graph can be the program, why parallelism comes from the topology, and why a rewrite can be checked locally (Cedar `GUARD` / `MUTATE`). Be exact about the status: GraphLang runs a **token-passing dataflow** over such a graph, not a true rewrite engine; interaction nets are the foundation, not a strict specification, and LLM-sampling nodes and `LOOP` are outside the confluent core (see graflang's `docs/DEV/readme-design.md`, gaps #26 and the semantics section).

**Graph-native workflows.** SPL scripts were text that had to be turned back into a picture (`.spl` to Mermaid) to be reviewed. A GraphLang workflow *is* the graph, so review is the graph itself: `graf vis FILE` shows the control flow first, data edges on demand, loops as one box that opens on a click. SPL scripts are being migrated to GraphLang workflows; the SPL-to-`graph.yaml` item below is therefore on hold, and `spl2graph` stays in SPL.py for the migration.

**Shared infrastructure.** Because both are graphs, they share code in zinet: the graph algorithms (`zinet.algorithms`), drawing and subgraph selection (`zinet.vis`, used by `graf vis` and `workgraph viz`), comment-preserving YAML (`zinet.roundtrip`), and recognising each other's files (`zinet.formats`). The next step is authoring workflows in the graph view itself (a visual IDE; see `readme-todo.md`). The ecosystem page [readme-ecosystem.md](readme-ecosystem.md) lists the apps and how each relates.

---

## SPL scripts as graph.yaml - *TODO*

An `.spl` script is already a computation DAG: tools are nodes, data flows are edges, recipes are capstone entry points. Persisting SPL scripts as `graph.yaml` makes that DAG visible:

- The ConceptBook navigator becomes a **browsable pipeline explorer** — click a recipe to see which steps it calls, which tools each step depends on.
- `cba gen-graph` regenerates the HTML view whenever the pipeline changes — no separate documentation pass required.
- Validation (`concept-book-press validate`) catches broken edges (missing tool deps, orphaned concepts) before a pipeline runs.

This closes the loop between authoring SPL scripts and explaining them — the same artifact is both the runnable spec and the human-readable overview.

---

## Education as a graph surface — ConceptBook + Novak & Gowin

ConceptBook (`cba`) is already in the five-CLI ecosystem.  What the paper
[Gong (2026), *ConceptBook: A Graph-First Framework for AI-Generated Curricula*]
adds is a deeper grounding: the graph-first approach to knowledge representation
is not only computationally convenient — it may be *cognitively correct*.

### The independent convergence

Novak & Gowin (1984), *Learning How to Learn*, arrived at concept maps —
knowledge represented as a directed graph of concepts and the relations between
them — from Ausubel's psychology of meaningful learning.  Their starting point
was cognitive science, not physics or graph theory.  The reductionist path
in ZiNets (Chinese characters → radicals → `graph.yaml`) arrived at the same
two-element structure (nodes = concepts, edges = prerequisite relations) from
a completely different direction.

Two independent paths converging on the same representation is the strongest
available evidence that the representation is tracking something real, not an
arbitrary design choice.

### The neuroscience connection (if validated)

Ausubel's assimilation theory — the cognitive foundation Novak & Gowin built
on — holds that meaningful learning happens when new knowledge is explicitly
anchored to existing concepts in a learner's cognitive structure.  The
concept-graph makes that anchoring *computable*: `learning_path(known, target)`
is not a metaphor for how the brain learns; it is a formal claim about which
prerequisite nodes must be activated before a new node can be meaningfully
integrated.

If this claim is validated against neuroscience evidence (fMRI studies of
schema activation, chunking research from working-memory literature, semantic
network models of long-term memory), the graph-first IR graduates from a
pedagogical tool to a *cognitively grounded representation* — one whose
structure reflects actual memory organization, not just curricular convenience.

Specific connections worth pursuing:
- **Chunking (Miller 1956):** the primitive-budget constraint (default: 2 new
  primitives per generated section) maps directly to cognitive load theory
  (Sweller) — the pipeline enforces it mechanically what the brain requires
  biologically.
- **Schema theory (Bartlett, Piaget):** each `composed_of` edge is a schema
  activation link — a new concept is learnable only when its prerequisite
  schemas are already formed.
- **Semantic network models:** Collins & Quillian (1969) modeled long-term
  memory as a directed graph of concepts and ISA/property relations — the
  same node/edge structure as `graph.yaml`.

### The coin

The paper's central claim — *teaching and learning are two sides of the same
coin, and the concept-graph is the coin* — maps precisely to the form/function
duality:

| Role | Graph operation | Duality |
|---|---|---|
| Teaching | Author the graph (declare primitives, compose concepts, define capstone) | Form — structure |
| Learning | Navigate the graph (`learning_path`, `gap`) | Function — process |

One artifact, two actors, same graph.  The teacher encodes structure; the
learner activates it.  Neither is complete without the other — the same
irreducibility as fermion and boson, form and function, node and edge.

---

## Solver problems as graph.yaml - *TODO*

A deterministic solver problem decomposes the same way:

```yaml
primitives:
  - id: daily_budget
    type: parameter
    value: 500.0
  - id: x_units
    type: variable
    bounds: [0, null]

concepts:
  - id: total_cost
    expression: "unit_cost * x_units"
  - id: capacity_constraint
    expression: "x_units <= max_units"

applications:
  - id: minimize_cost
    objective: total_cost
    constraints: [capacity_constraint]
    solver: linprog
```

This means:
1. **`gfc` can scaffold a solver app** from the same `graph.yaml` that describes the problem — the graph is both the spec and the generation target.
2. **`spl3` handles the human → formal translation layer** — natural language problem description → structured `graph.yaml` primitives/constraints/objectives — while the solver handles the rigorous math without LLM approximation.
3. The ConceptBook navigator becomes a **problem explorer** — visualize decision variables, trace constraint chains, inspect sensitivity.

The Solver Advisor architecture extends this into a full pipeline: `NL Input → Triage → Formulation → Checks → Solver (PuLP/CBC, OR-Tools, …) → Verification → Certificate`. The SPL verifier ladder (`C1–C7 ASSERT` gates) that certifies SymPy derivatives certifies CBC optimal solutions by the same mechanism — the solver class changes, the pattern does not.

**Research base:** `docs/publication/TMLR/SPL-Solver/` — Solver Reference Guide (recipes 75–94), SPL solver recipes, Solver Advisor architecture, TMLR paper plan "SPL for Operations Research" (builds on arXiv:2607.07727; extends the symbolic-math empirical base to LP/ILP/scheduling/routing).

See also: `SPL-Solver/solver/paper-spl-solver-plan.md` (full TMLR submission plan), `SPL-Solver/solver/solver-guide.md` (practitioner's guide), `SPL-Solver/solver/SPL-solver-recipes.md` (concrete SPL recipes for OR problems).

---

## The LLVM analogy

> For a full tutorial on LLVM's architecture and IR, see [README-LLVM.md](README-LLVM.md).

LLVM succeeded because it separated concerns: front-ends (C, Rust, Swift) emit one IR; back-ends (x86, ARM, WASM) consume it; optimizations operate on the IR independently. `graph.yaml` plays the same role for the ZiNets ecosystem:

- **Front-ends**: Claude CLI (extracts graphs from PDFs), `spl3` scripts, hand-authored YAML, ZiNets SQLite DB → all emit `graph.yaml`.
- **Back-ends**: `cba` (concept books), `gfc` (software), `solver` (optimization), `mg` (grid inference) → all consume `graph.yaml`.
- **Optimizations**: `concept-book-press validate` (structural checks), `cba gen-graph` (HTML rendering), future linters and graph diff tools → all operate on `graph.yaml` without knowing what back-end will consume it.

One format to author, validate, version, and transform.

---

## Practical implications

1. **Default to graph.yaml** when designing new data formats or persistence schemas anywhere in the ecosystem.
2. **Graph-first tooling**: before building a new UI or pipeline, check whether it can be expressed as a `graph.yaml` domain consumed by an existing back-end.
3. **graph.html as free documentation**: every `graph.yaml` domain gets a navigable HTML explorer for free via `cba gen-graph` — no separate documentation effort.
4. **Long-term convergence**: `gfc` and `cba` share the same input format and the same LLM layer (`spl3`). They are candidates for eventual merge into one unified "graph-to-X" tool — the `X` is just a back-end plugin.

---

## Graph-first in the wild

External tools independently validate the same insight — once structure is
represented as a graph, queries become subgraph / path problems rather than
string problems, and they generalise across surface syntax:

**Semgrep** (security static analysis) — matches vulnerability patterns against
a code AST rather than raw text.  A rule like `subprocess.run($CMD, shell=True)`
with a `pattern-not: subprocess.run("...", shell=True)` exclusion is
a subgraph query: find this call-node shape where the argument is *not* a
string literal.  The same rule fires regardless of how the code is formatted,
indented, or split across lines — because it operates on the parsed tree, not
characters.  This is why semgrep catches `os.system(user_cmd)` and
`subprocess.run(f"ls {d}", shell=True)` as the same CWE-78 class while grep
finds neither.

The parallel to `graph.yaml`: semgrep's rules are **primitives** (atomic sink
patterns) and **concepts** (composed taint flows), and a full vulnerability
scan is an **application** — the same three-layer DAG.  The difference is that
semgrep's graph is file-local AST; a full code graph (`gfc` / graph-code)
connects definitions and usages across module boundaries, which is where
semgrep's taint analysis reaches its limit and an LLM triage stage picks up.

*Practical use in this repo:* `cvecoder hunt scan` runs semgrep rules (ported
from `find-cve-agent`) as stage 1 of CVE discovery, before any LLM involvement.
See `docs/GUIDE/CVE-coder-User-Guide.md § CVE Discovery — hunt scan` and
`docs/RESEARCH/README-find-cve-agent.md § What is Semgrep?`.

---

## Appendix: Conceptual Grounding in Form-Function Duality

The graph-first approach is not an architectural preference — it reflects a
structural truth that appears independently across physics, mathematics, and
knowledge representation.

### The binary that won't reduce further

Three independent formalisms converge on the same two-element basis:

| Domain | Structure | Interaction |
|---|---|---|
| Physics | Fermion (matter, occupies space, Pauli exclusion) | Boson (force carrier, mediates exchange) |
| Graph theory | Node (identity, state) | Edge (relation, flow) |
| Form / Function | Form (what something *is*) | Function (what something *does*) |

The mapping runs deeper than analogy.  In physics, fermions *stack* (no two in
the same state — Pauli exclusion) while bosons *superpose* (a laser is a
trillion photons in the same state, coherently).  In graphs, nodes are discrete
and countable while edges are relational and can multiply between the same pair.
In form/function duality, forms are bounded and identifiable while functions
compose and chain freely.  The asymmetry is the same across all three domains.

### Why physics grounds this

The Standard Model tried hard to find something more fundamental than fermions
and bosons — and could not.  That irreducibility is the point.  When the ZiNets
graph-first IR arrives at the same two-element basis from a completely different
direction (Chinese character decomposition → node/edge → `graph.yaml`), the
convergence is evidence of a real structural truth, not a design decision.

### Consequence for the five surfaces

If every domain decomposes into nodes (identities with state) and edges
(relations with flow), then `graph.yaml` is the right IR not by convention but
by necessity — it is the minimal structure capable of representing anything:

- **SPL scripts**: tools are nodes, data flows are edges, recipes are capstone paths.
- **Momagrid**: GPU nodes, Hub-Spoke network edges, distributed inference as a flow graph.
- **ConceptBook**: concepts are nodes, logical dependencies are edges, worked examples are paths.
- **Graph-Code**: components are nodes, APIs and imports are edges, deployable apps are entry paths.
- **Solver**: decision variables are nodes, constraints are edges, the objective is the target path.
- **Education**: primitive knowledge units are nodes, prerequisite relations are edges, the target mastery concept is the capstone path — grounded in Novak & Gowin's (1984) concept maps, which independently arrived at the same representation from cognitive science rather than from physics or graph theory.  If validated against neuroscience (semantic networks, schema theory, cognitive load), this surface carries the deepest claim: the graph-first IR reflects not just a useful abstraction but actual memory architecture.

The `primitives → concepts → applications` three-layer schema is the same
fermion/boson duality applied recursively: primitives are pure form (leaves,
no decomposition), edges between them are pure function (relations, no identity
of their own), and applications are where form and function crystallize into a
usable whole.

### Practical implication

Each new surface added to the ecosystem (SPL, Momagrid, Solver, and beyond)
will have a "local graph / global graph" boundary — a point where intra-unit
static structure ends and cross-unit dynamic interaction begins.  That boundary
is where static analysis (semgrep operating on a file-local AST) hands off to
LLM reasoning (which can traverse cross-module edges).  Identifying that
boundary for each surface is the first design task when generalizing graph-first
to a new domain.

---

## References

- `~/projects/digital-duck/zinets/RESEARCH-status-and-plan.csv` — rows: "Graph.yaml as Universal IR", "ZiNets Ecosystem Five CLIs"
- `~/projects/digital-duck/conceptbook-app/docs/DEV/README-cli.md` — `cba` command reference
- `~/projects/digital-duck/graph-code/` — `gfc` implementation
- `~/projects/digital-duck/SPL.py/` — `spl3` implementation
- `~/projects/Proj-ZiNets/zinets_vis/` — ZiNets character explorer (origin of the graph metaphor)
- `docs/publication/TMLR/SPL-Solver/` — Solver research hub:
  - `Solver-Reference-Guide.pdf` — recipes 75–94 (solver SPL patterns)
  - `solver/paper-spl-solver-plan.md` — TMLR paper plan "SPL for Operations Research"
  - `solver/SPL-solver-recipes.md` — concrete SPL recipes for LP/ILP/scheduling/routing
  - `solver/solver-guide.md` — practitioner's guide to Solver Advisor
  - `solver/Solver-Box.md` — full Solver Advisor design document
- **Lafont, Y. (1990).** Interaction nets. *Proceedings of the 17th ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL).* — the graph-rewriting model GraphLang is grounded in: agents with ports, local rewrite rules, confluence.
- `~/projects/digital-duck/graflang/` — GraphLang (`graf`): executable workflow graphs; `docs/DEV/readme-design.md` has the exact semantics and the gap table.
- [README-LLVM.md](README-LLVM.md) — LLVM tutorial: IR architecture, SSA form, optimization passes, and the graph.yaml parallel
- **Novak, J. D., & Gowin, D. B. (1984).** *Learning How to Learn.* Cambridge University Press. — concept maps as prerequisite graphs for learners; grounded in Ausubel's assimilation theory; independent convergence with the graph-first IR from cognitive science. Cited in `docs/publication/TMLR/SPL-for-Education/spl4ed-paper-v1.1.tex` (§1.3, §2.1, §7.3).
- **Collins, A. M., & Quillian, M. R. (1969).** Retrieval time from semantic memory. *Journal of Verbal Learning and Verbal Behavior.* — original semantic network model of long-term memory as a directed concept graph; foundational neuroscience anchor for the Education surface.
- `docs/publication/TMLR/SPL-for-Education/spl4ed-paper-v1.1.tex` — ConceptBook paper: graph-first framework for AI-generated curricula; two-radical structure; teaching/learning as two sides of the same coin.
