# graph-ir

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

```bash
uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"
```

## CLI: `gir`

```bash
gir validate graph.yaml            # exit 1 on errors; warnings are printed but do not fail
gir diff old.yaml new.yaml         # exit 1 when the graphs differ
gir slice graph.yaml target_id -o part.yaml   # target plus its prerequisite closure
gir render graph.yaml                              # svg to stdout (default)
gir render graph.yaml --format mermaid             # mermaid flowchart text
gir render graph.yaml --format png -o graph.png    # png and pdf need -o
```

`render` supports `svg`, `png`, `pdf`, and `mermaid`. Mermaid needs nothing installed. The
other formats need Graphviz's `dot` on PATH (`apt install graphviz`).

Exit code 2 means a usage, load, or render error.

## Python API

```python
from graph_ir import load_graph, validate, diff_graphs, slice_to, dump_graph

graph = load_graph("solver_pipeline.yaml")   # resolves imports
for issue in validate(graph):
    print(issue)
prereqs = slice_to(graph, "minimize_cost")
```

## Checks

| Code | Severity | Meaning |
|---|---|---|
| `duplicate_id` | error | an id is defined more than once |
| `unknown_dep` | error | a dep names an id that does not exist |
| `primitive_has_deps` | error | a primitive depends on something |
| `layer_violation` | error | a node depends on an application |
| `cycle` | error | the dependency graph is not a DAG |
| `orphan` | warning | a node with no deps and no dependents |

## Layout

```text
src/graph_ir/
  schema.py       Pydantic models: Graph, Node, Layer, EdgeType
  dag.py          topological order, ancestors (domain-agnostic)
  validator.py    structural checks -> Issue list
  io.py           load_graph (with imports), dump_graph, to_yaml
  transforms/     diff_graphs, slice_to
  render.py       DOT and Mermaid generation, svg/png/pdf via `dot`
  cli.py          the `gir` command
tests/            pytest suite; tests/fixtures holds one graph per domain
```

## Design decisions

- Imports merge nodes without namespacing, so ids must be unique across the whole import tree.
- `load_graph` does not validate. Run `validate` separately for structural checks.
- Unknown top-level and node keys are rejected, so typos fail loudly. Domain data goes in `meta`.
- Only the core checks are here. Domain rules (for example, solver bounds) belong in the back-end.

## Not yet implemented

- JSON Schema export (`schemas/graph.schema.json`) and domain overlays.
- `graph.html` interactive explorer (belongs to `cba`) and `fmt`.
- `spl3` integration, which is the next step: SPL scripts compiling to `GraphIR`.
