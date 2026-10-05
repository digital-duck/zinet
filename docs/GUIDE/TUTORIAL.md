# graph-ir Tutorial: Using the `gir` Command

This tutorial walks through the `gir` command-line tool, which validates, compares, slices, and
renders `graph.yaml` files. Every example uses the sample graphs in `tests/fixtures/`, and the
outputs shown were produced by the current version (`gir 0.1.0`).

---

## 1. Install

From the repository root:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -p .venv/bin/python -e ".[dev]"

gir --version                    # gir 0.1.0
```

Rendering to SVG, PNG, or PDF also needs Graphviz's `dot` on your PATH. Mermaid output needs nothing.

```bash
sudo apt install graphviz        # Debian / Ubuntu
```

---

## 2. Anatomy of a `graph.yaml`

A graph has three layers. Each layer is a list of nodes:

```yaml
version: "1.0"
imports: [./shared/tools.yaml]   # optional, resolved relative to this file
primitives:                      # leaves: must not depend on anything
  - id: x_units
    meta: {type: variable}
concepts:                        # composed from primitives and other concepts
  - id: capacity_constraint
    deps: [x_units, max_units]   # ids this node depends on
    edge_types: {max_units: constraint}
    meta: {expression: "x_units <= max_units"}
applications:                    # capstones: nothing may depend on these
  - id: minimize_cost
    deps: [capacity_constraint]
```

| Field | Meaning |
|---|---|
| `id` | Unique across the whole graph, including imports |
| `deps` | Ids this node depends on (the incoming edges) |
| `edge_types` | Optional type for a dependency: `depends_on` (default), `data_flow`, `prerequisite`, `constraint`, `inheritance` |
| `meta` | Domain payload. The core never interprets it |
| `label` | Optional human-readable name, used by `render` |

Unknown keys are rejected on purpose, so a typo such as `primitves:` fails at load time.

---

## 3. Validate a graph: `gir validate`

Run it on the bundled solver example:

```bash
gir validate tests/fixtures/solver_problem.yaml
```

```text
tests/fixtures/solver_problem.yaml: ok (8 nodes)
```

Now try a broken graph. This one has a primitive with a dependency, an unknown id, a cycle, and an
isolated application:

```yaml
# broken.yaml
primitives:
  - id: a
    deps: [b]
  - id: b
concepts:
  - id: c
    deps: [ghost, d]
  - id: d
    deps: [c]
applications:
  - id: app
```

```bash
gir validate broken.yaml
```

```text
broken.yaml: error: primitive_has_deps [a]: primitives are leaves but depend on ['b']
broken.yaml: error: unknown_dep [c]: depends on undefined id 'ghost'
broken.yaml: error: cycle: dependency cycle among: c, d
broken.yaml: warning: orphan [app]: not connected to any other node
```

### Checks

| Code | Severity | Meaning |
|---|---|---|
| `duplicate_id` | error | an id is defined more than once |
| `unknown_dep` | error | a dep names an id that does not exist |
| `primitive_has_deps` | error | a primitive depends on something |
| `layer_violation` | error | a node depends on an application |
| `cycle` | error | the dependency graph is not a DAG (self-loops count) |
| `orphan` | warning | a node with no deps and no dependents |

Warnings are printed but do not change the exit code.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | success |
| `1` | validation errors, or differences found by `diff` |
| `2` | usage error, file not found, or a schema violation such as an unknown key |

A schema violation is a load-time failure, so it exits with 2 before any structural check runs:

```yaml
# typo.yaml
primitives:
  - id: a
concepts2_placeholder: 1
```

```text
gir: error: typo.yaml: 1 validation error for Graph
concepts2_placeholder
  Extra inputs are not permitted [type=extra_forbidden, input_value=1, input_type=int]
```

---

## 4. Draw a graph: `gir render`

`render` writes the graph to stdout by default, in SVG. Use `-o` to write a file.

| `--format` | Output | Requires |
|---|---|---|
| `svg` (default) | SVG markup | Graphviz `dot` |
| `png` | PNG image, needs `-o` | Graphviz `dot` |
| `pdf` | PDF document, needs `-o` | Graphviz `dot` |
| `mermaid` | Mermaid flowchart text | nothing |

```bash
# Image files
gir render tests/fixtures/solver_problem.yaml --format png -o solver.png
gir render tests/fixtures/solver_problem.yaml --format pdf -o solver.pdf

# SVG to a file
gir render tests/fixtures/solver_problem.yaml -o solver.svg

# Mermaid, for pasting into a Markdown file or GitHub comment
gir render tests/fixtures/solver_problem.yaml --format mermaid
```

Mermaid output looks like this (shortened):

```text
flowchart LR
  subgraph primitives
    n0(["daily_budget"])
    n1(["unit_cost"])
  ...
  n5["budget_constraint"]
  n0 -->|constraint| n5
  n4 --> n5
```

In the rendered image, each layer is a cluster, and the layers use different shapes. Primitives are
ellipses, concepts are boxes, and applications are double octagons. Edges run from dependency to
dependent and carry their type as a label when the type is not `depends_on`.

Use `--no-imports` to render only the file itself, without merging its imports.

---

## 5. Extract a subgraph: `gir slice`

`slice` keeps a target node and everything it transitively depends on. For a concept graph this is
the prerequisite closure of the target:

```bash
gir slice tests/fixtures/solver_problem.yaml budget_constraint -o budget_part.yaml
gir validate budget_part.yaml
```

```text
budget_part.yaml: ok (5 nodes)
```

Without `-o`, the YAML goes to stdout, which you can pipe into another tool. An unknown target is
an error:

```bash
gir slice tests/fixtures/solver_problem.yaml nope
```

```text
gir: error: unknown node: 'nope'
```

---

## 6. Compare two graphs: `gir diff`

`diff` matches nodes by id and reports what was added, removed, or changed. Dependency order is
ignored, so reordering a `deps` list is not a change.

```bash
gir diff tests/fixtures/spl_pipeline.yaml tests/fixtures/concept_book.yaml
```

```text
+ capstone_chain_rule
+ concept_derivative
+ concept_function
+ concept_limit
- recipe_build_concept_book
- step_summarize
- tool_cache_get
- tool_llm_call
```

Changed nodes print each field that differs, in the form `~ node.field: old -> new`:

```text
~ step_summarize.label: None -> 'summarize v2'
```

`diff` exits 1 when the graphs differ and 0 when they match, like the Unix `diff` command. That
makes it usable in scripts:

```bash
gir diff before.yaml after.yaml || echo "graph changed"
```

---

## 7. Modular graphs with imports

Large graphs can be split across files. List the files under `imports:`, and paths resolve relative
to the file that lists them:

```yaml
# shared/tools.yaml
primitives:
  - id: tool_llm_call
  - id: tool_cache_get
```

```yaml
# pipeline.yaml
imports: [shared/tools.yaml]
concepts:
  - id: step_summarize
    deps: [tool_llm_call, tool_cache_get]
```

```bash
gir validate pipeline.yaml
```

Imports are merged, and ids must stay unique across the whole tree. Two files that define the same
id, or an import cycle, fail at load time with exit code 2. The merged graph is validated as one.

---

## 8. Python API

Everything the CLI does is available from Python:

```python
from graph_ir import load_graph, validate, slice_to, diff_graphs, dump_graph, to_mermaid

graph = load_graph("tests/fixtures/solver_problem.yaml")   # resolves imports

for issue in validate(graph):
    print(issue)

prereqs = slice_to(graph, "budget_constraint")
dump_graph(prereqs, "budget_part.yaml")

print(to_mermaid(graph))
```

`load_graph` does not validate on its own. Call `validate` when you want the structural checks.

---

## 9. Typical workflow

```bash
gir validate pipeline.yaml                       # 1. check the graph
gir render pipeline.yaml --format mermaid > pipeline.md   # 2. document it
gir slice pipeline.yaml final_report -o part.yaml         # 3. extract what one target needs
gir diff main.yaml feature.yaml                  # 4. review a change to the graph
```

---

## Quick reference

```text
gir validate FILE [--no-imports]
gir diff OLD NEW
gir slice FILE TARGET [-o OUT]
gir render FILE [--format svg|png|pdf|mermaid] [-o OUT] [--no-imports]
gir --version
```
