# zinet ecosystem: related graph-first apps

zinet is the small, domain-free core for `graph.yaml`: a static dependency graph in three layers
(`primitives`, `concepts`, `applications`) with a validator, diff, slice, render and prettify. It
persists a graph in plain YAML, and it does not run anything. The apps below are graph-first in the
same sense (the graph is the main artifact, not a by-product), but each has its own graph model and
its own job. This page says what each one is and how it relates to zinet.

For the wider design, see [README-graph-vision.md](README-graph-vision.md) (the five-CLI ecosystem
and the layered design). For the shared-code plan, see [readme-todo.md](readme-todo.md).

Last reviewed: 2026-10-24.

## The four related apps

| App | Repo | Command | The graph is... | Relation to zinet |
|---|---|---|---|---|
| **ConceptBook** | `conceptbook-app` (`cba`), `concept-book-press`, `concept-book-base`, one `cb-*` repo per domain | `cba`, `cb_pipeline` | a curriculum: concepts joined by prerequisite edges, from irreducible primitives up to target mastery | same three layers and the same flat `graph.yaml`; the closest relative and the biggest source of duplicated graph code |
| **Graph-Code** | `graph-code` | `grafcode`, `gfc` | an app or curriculum as typed nodes and edges (the Unified Duality Graph Schema v2.1+: form and function spaces, events, transitions, aliased imports) | a richer schema that also reads the flat v1.0 format; shares algorithms with zinet, not the schema |
| **work-graph** | `work-graph` | `workgraph` | everything produced and consumed while building software (requirements, decisions, code, tests, bugs, notes), as layered graphs that reference each other | its own layer files (JSON canonical, YAML for review); shares tooling (comment-preserving YAML, drawing), not the format |
| **GraphLang** | `graflang` | `graf` | an executable workflow: typed nodes with ports, `triggers` (control) and `binds` (data) edges, loops and retries, Cedar policies | a different kind of graph (it runs, and may contain cycles); recognised by content, shares drawing code |

### ConceptBook

A body of knowledge is first a graph (nodes are concepts, edges are prerequisites), then a book.
- `conceptbook-app` is the web app and the `cba` CLI. `concept-book-press` (`cb_pipeline`) turns
  open-source textbooks into concept graphs. `concept-book-base` is the template that new domain
  repos are forked from. Each domain (`cb-linalg`, `cb-calculus`, `cb-chemistry`, ...) is its own repo.
- Input is a `graph.yaml` of primitives, concepts and applications, which is zinet's format.
- Today every domain repo carries its own copy of `scripts/concept_graph.py` (19 copies) and
  `spl/graph_lib.py` (18 copies). Moving that code into zinet is the main item in
  [readme-todo.md](readme-todo.md).

### Graph-Code

Graph-driven code and curriculum generation: the graph describes an app, and tools build, check
and scaffold it.
- Schema v2.1+ separates a form space (nodes) from a function space and adds events, transitions,
  call contracts and aliased imports. It loads the flat v1.0 format by converting it to v2.1.
- It has its own versions of the algorithms zinet also has (cycle check, build order, learning path,
  gap). Those are the schema-agnostic part and can move to zinet. Events, transitions, drift and
  clustering stay in graph-code.

### work-graph

A personal AI assistant whose long-term memory is a knowledge graph covering the whole software
lifecycle and the knowledge around it. Status per its README: hackathon project, early prototype.
- Several graphs (repo, product, org, process) with their own vocabularies that reference each
  other, stored as JSON (canonical) and YAML (for review).
- Useful to zinet because it already has a comment-preserving YAML round-trip and a graph-drawing
  module with several engines. Both are listed in [readme-todo.md](readme-todo.md) as code that
  could live in zinet.

### GraphLang

A language for agentic workflows where the graph is the program and the model changes the topology
instead of writing code. Early prototype; evolved from SPL.py.
- Workflow files are `*.graph.yaml` (`workflow:`, `nodes:`, `edges:`). They are executed, checked,
  compiled (a stub) and drawn by the one command `graf`.
- It is not a zinet graph: its edges carry control and data between ports, nodes have types and
  a `config`, and cycles are allowed for retries. Folding it into zinet would force that model onto the
  other apps, so the two stay separate and recognise each other's files.
- `spl3` can lift an SPL workflow into a GraphLang graph (`spl2graph.py`, an unreviewed draft).

## How they differ

| | zinet | ConceptBook | Graph-Code | work-graph | GraphLang |
|---|---|---|---|---|---|
| Purpose | store and check a graph | teach a domain | build an app | remember a project | run a workflow |
| Graph kind | dependency DAG | prerequisite DAG | typed form/function graph | layered multigraph | port graph, may have cycles |
| Layers | primitives, concepts, applications | the same | form and function spaces | repo, product, org, process | none (nodes have types) |
| Executes | no | no | builds code | no | yes |
| Persisted as | `graph.yaml` | `graph.yaml` | `graph.yaml` (v2.1, or flat v1.0) | JSON and YAML layer files | `*.graph.yaml` |

## File names

`*.graph.yaml` is a GraphLang workflow. Plain `graph.yaml` is a zinet graph. There is no
`*.zinet.yaml`: `zinet` is a tool name, not a file format, and `.yaml` is the base format (the word
"graph" says the file persists graph data). The name is only a convention. The tools tell the two
kinds apart by content: `workflow:` with `nodes:` and `edges:` is GraphLang, and `primitives:`,
`concepts:` or `applications:` is zinet, so a file named `graph.yaml` works with either tool.

## What is shared today and what is planned

| Shared | Status |
|---|---|
| `graph.yaml` format, validator, diff, slice, prettify, render, JSON Schema | in zinet 0.1.0 |
| Graph algorithms (acyclic, ancestors, gap, learning path, productivity order, reducible) | duplicated in ConceptBook and Graph-Code; planned for zinet 0.2.0, adopted first by Graph-Code |
| Drawing engines (cytoscape, graphviz, mermaid, ascii in the core install; pyvis and graphify as extras) | duplicated in work-graph, GraphLang and ConceptBook; planned for zinet 0.2.0, adopted first by GraphLang, then work-graph |
| Comment-preserving YAML | in work-graph; planned for the zinet core (`ruamel.yaml`) |
| Recognising each other's files | done in GraphLang (not yet committed); to do in zinet |

ConceptBook is frozen for now (its paper is in progress): the `cb-*` repos stay as they are, and refactoring `concept-book-press` and `concept-book-base` is on hold, to be revisited in future. The first adopters are GraphLang, work-graph and Graph-Code.

Details, the order of work, risks and decisions are in [readme-todo.md](readme-todo.md).
