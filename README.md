# zinet

Graph IR core package shared across SPL, ConceptBook, Graph-Code, Momagrid, and Solver domains.

`graph.yaml` is the common intermediate representation of the ZiNets ecosystem, the way LLVM IR
is for compilers: front-ends emit it, back-ends consume it, and the shared validator and
transforms live here once.

## The format

Every graph has three layers, each a list of nodes:

```yaml
version: "1.0"
imports: [./shared/tools.yaml]   # optional; resolved relative to this file
primitives:                      # leaves: must not have deps
  - id: x_units
    meta: {type: variable}
concepts:                        # composed from primitives and other concepts
  - id: capacity_constraint
    deps: [x_units, max_units]
    edge_types: {max_units: constraint}
    meta: {expression: "x_units <= max_units"}
applications:                    # capstones: nothing may depend on these
  - id: minimize_cost
    deps: [capacity_constraint]
```

- `deps` are the ids a node depends on (incoming edges).
- `edge_types` optionally types a dependency: `depends_on` (default), `data_flow`,
  `prerequisite`, `constraint`, `inheritance`.
- `meta` is an opaque domain payload that the core never interprets.

## Install

From PyPI:

```bash
pip install zinet
```

From source, for development:

```bash
uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"
```

## CLI: `zinet`

```bash
zinet validate graph.yaml            # exit 1 on errors; warnings are printed but do not fail
zinet validate graph.yaml --strict   # also check that every concept reaches a primitive and the graph is one piece
zinet diff old.yaml new.yaml         # exit 1 when the graphs differ
zinet slice graph.yaml target_id -o part.yaml   # target plus its prerequisite closure
zinet render graph.yaml                              # svg to stdout (default)
zinet render graph.yaml --format mermaid             # mermaid flowchart text
zinet render graph.yaml --format html -o graph.html  # interactive page (search, zoom, click a node); works offline
zinet render graph.yaml --format ascii               # plain-text outline by depth
zinet render graph.yaml --format png -o graph.png    # png and pdf need -o
zinet prettify graph.yaml                            # diff against canonical formatting (exit 1 if it would change)
zinet prettify graph.yaml --write                    # rewrite in place; comments are kept
zinet convert graph.yaml                             # to graph.json; the comments are kept in a small database
zinet convert graph.json                             # back to graph.yaml, with the comments put back
zinet schema -o schemas/graph.schema.json            # JSON Schema for editors and other tools
```

`render` supports `svg`, `png`, `pdf`, `mermaid`, `html` and `ascii`. Mermaid, html and ascii need nothing installed. The `svg`,
`png` and `pdf` formats need Graphviz's `dot` on PATH (`apt install graphviz`).

Exit code 2 means a usage, load, or render error. `prettify` exits 1 when a file is not in
canonical form, so it can run in CI.

## Specification

The format is specified in [docs/SPECIFICATION.md](docs/SPECIFICATION.md). The machine-readable
JSON Schema is [schemas/graph.schema.json](schemas/graph.schema.json), regenerated with
`zinet schema -o schemas/graph.schema.json`. A test fails if the committed schema is out of date.

## Python API

```python
from zinet import load_graph, validate, diff_graphs, slice_to, dump_graph

graph = load_graph("solver_pipeline.yaml")   # resolves imports
for issue in validate(graph):
    print(issue)
prereqs = slice_to(graph, "minimize_cost")
```

## Graph algorithms

Plain-`networkx` functions that the apps share (graph-code, ConceptBook and others had their own copies). The input is a
`networkx.DiGraph` with edges from a dependency to its dependent and an optional `kind` attribute per node (`primitive`,
`concept`, `application`; none means "referenced but never declared"). `to_networkx(graph)` builds one from a zinet `Graph`.

```python
import zinet
G = zinet.to_networkx(zinet.load_graph("graph.yaml"))
zinet.learning_path(G, "app", known=["a"])        # what is still needed to reach `app`, dependencies first
zinet.productivity_order(G)                       # order that unlocks the most nodes as early as possible
zinet.reducible(G)                                # does everything rest on primitives?
zinet.build_order(G), zinet.gap(G, "app", ["a"]), zinet.applications_of(G, "a"), zinet.restrict(G, nodes)
zinet.ensure_acyclic(G)                           # raises CycleError, naming the nodes on the cycle
```

The options select the behaviour of the code these functions replace: `include_primitives`, `include_target`,
`order="topological"|"alphabetical"|"reach"`, `weighted_applications`, `seed_by_reach`, and four `reducible` rules
(`primitive_ancestry`, `declared`, `declared_or_listed`, `named_primitives`). Defaults follow graph-code.
A missing node raises `UnknownNodeError` (a `KeyError`) and a cycle raises `CycleError`. What each copy did, and where
they differ, is frozen in `tests/characterization/` (see `divergences.md`). `topological_order` and `ancestors` also accept a
`DiGraph`.

## Comments

`prettify --write` keeps your YAML comments. Each comment is pinned to what it sits next to (a node by `id`, a key of that node,
or a top-level section; a comment block at the top of the file stays on top) and put back into the canonical text. If any
comment cannot be put back exactly, the file is not rewritten.

`zinet convert` goes between YAML and JSON. JSON has no comments, so the YAML's comments are stored in a small SQLite database
(`~/.zinet/comments.db`, or `$ZINET_HOME`, or `--store PATH`) and put back when you convert the JSON to YAML again. A comment
whose node was removed or renamed is written at the end of the file as `# [orphaned from <id>] ...` and returns if the node does.
This is the approach work-graph uses for its layer files (the same code, see `zinet.roundtrip`); there is nothing to install.

## Drawing any graph

`zinet.vis` draws and trims any `networkx` graph, not only zinet's, so other tools do not each carry their own copy
(GraphLang and work-graph did). A `Style` is a set of small functions that read your attribute names (node label, kind, colour,
shape, group; edge label and dashing), so no app has to rename anything.

```python
from zinet.vis import render, select, zinet_style
G = zinet.to_networkx(zinet.load_graph("graph.yaml"))
render(G, "graph.html")                         # engine="cytoscape" (default) | "graphviz" | "mermaid" | "ascii" | "pyvis" | "graphify"
sub, note = select(G, node="app", hops=2)       # a readable neighbourhood of a big graph: filters, hidden kinds, hub edges, a node cap
```

The `cytoscape` engine writes one HTML file with Cytoscape.js bundled (MIT, see `src/zinet/vis/data/LICENSE-cytoscape.txt`), so it works
offline; if Graphviz is installed it also takes the node layout from `dot` (it keeps a group together and picks a left-to-right or
top-to-bottom shape that fits the screen). `graphviz` writes svg, png or pdf by file extension. `mermaid` writes flowchart text
(`-o FILE.md` wraps it in a fenced block). `pyvis` and `graphify` need `pip install zinet[pyvis]` / `zinet[graphify]`.
GraphLang's and work-graph's output through these engines is checked against golden files in `tests/characterization/`.

## Checks

| Code | Severity | Meaning |
|---|---|---|
| `duplicate_id` | error | an id is defined more than once |
| `unknown_dep` | error | a dep names an id that does not exist |
| `primitive_has_deps` | error | a primitive depends on something |
| `layer_violation` | error | a node depends on an application |
| `cycle` | error | the dependency graph is not a DAG |
| `orphan` | warning | a node with no deps and no dependents |
| `not_reducible` | error | optional (`--check reducible`): a concept or application with no primitive ancestor |
| `disconnected` | warning | optional (`--check connected`): the graph is in more than one piece when edges are read as undirected |

`zinet validate --strict` runs both optional checks. They are off by default, so a graph that is valid today stays valid.

## Layout

```text
src/zinet/
  schema.py       Pydantic models: Graph, Node, Layer, EdgeType
  dag.py          topological order, ancestors (domain-agnostic)
  validator.py    structural checks -> Issue list
  io.py           load_graph (with imports), dump_graph, to_yaml
  prettify.py     canonical formatting for `zinet prettify`
  roundtrip.py    comment-preserving YAML (harvest and re-attach), SQLite comment store, `zinet convert`
  transforms/     diff_graphs, slice_to
  algorithms.py   graph algorithms on a plain networkx DiGraph (learning path, order, reducible, ...)
  render.py       DOT and Mermaid generation for zinet graphs, svg/png/pdf via `dot`
  vis/            drawing for any networkx graph: engines, `select`, `Style` (see "Drawing any graph")
  cli.py          the `zinet` command
docs/SPECIFICATION.md   the graph.yaml format specification
schemas/graph.schema.json   generated JSON Schema
tests/            pytest suite; tests/fixtures holds one graph per domain
```

## Design decisions

- Imports merge nodes without namespacing, so ids must be unique across the whole import tree.
- `load_graph` does not validate. Run `validate` separately for structural checks.
- Unknown top-level and node keys are rejected, so typos fail loudly. Domain data goes in `meta`.
- Only the core checks are here. Domain rules (for example, solver bounds) belong in the back-end.

## Not yet implemented

- Domain-specific JSON Schema overlays (solver, spl, cba).
- `graph.html` interactive explorer (belongs to `cba`).
- `spl3` integration, which is the next step: SPL scripts compiling to `GraphIR`.
