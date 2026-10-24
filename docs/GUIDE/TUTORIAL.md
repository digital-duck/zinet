# zinet Tutorial: Using the `zinet` Command

This tutorial walks through the `zinet` command-line tool, which validates, compares, slices,
renders, and formats `graph.yaml` files, and exports its JSON Schema. Every example uses the sample graphs in `tests/fixtures/`, and the
outputs shown were produced by the current version (`zinet 0.1.0`).

---

## 1. Install

From the repository root:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -p .venv/bin/python -e ".[dev]"

zinet --version                    # zinet 0.1.0
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

## 3. Validate a graph: `zinet validate`

Run it on the bundled solver example:

```bash
zinet validate tests/fixtures/solver_problem.yaml
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
zinet validate broken.yaml
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
| `not_reducible` | error | only with `--check reducible` or `--strict`: a concept or application with no primitive ancestor |
| `disconnected` | warning | only with `--check connected` or `--strict`: the graph is in more than one piece |

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
zinet: error: typo.yaml: 1 validation error for Graph
concepts2_placeholder
  Extra inputs are not permitted [type=extra_forbidden, input_value=1, input_type=int]
```

---

## 4. Draw a graph: `zinet render`

`render` writes the graph to stdout by default, in SVG. Use `-o` to write a file.

| `--format` | Output | Requires |
|---|---|---|
| `svg` (default) | SVG markup | Graphviz `dot` |
| `png` | PNG image, needs `-o` | Graphviz `dot` |
| `pdf` | PDF document, needs `-o` | Graphviz `dot` |
| `mermaid` | Mermaid flowchart text | nothing |
| `html` | one interactive page (search, zoom, click a node for its details), works offline | nothing (uses Graphviz for the layout when installed) |
| `ascii` | a plain-text outline by depth | nothing |

```bash
# Image files
zinet render tests/fixtures/solver_problem.yaml --format png -o solver.png
zinet render tests/fixtures/solver_problem.yaml --format pdf -o solver.pdf

# SVG to a file
zinet render tests/fixtures/solver_problem.yaml -o solver.svg

# Mermaid, for pasting into a Markdown file or GitHub comment
zinet render tests/fixtures/solver_problem.yaml --format mermaid
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

## 5. Extract a subgraph: `zinet slice`

`slice` keeps a target node and everything it transitively depends on. For a concept graph this is
the prerequisite closure of the target:

```bash
zinet slice tests/fixtures/solver_problem.yaml budget_constraint -o budget_part.yaml
zinet validate budget_part.yaml
```

```text
budget_part.yaml: ok (5 nodes)
```

Without `-o`, the YAML goes to stdout, which you can pipe into another tool. An unknown target is
an error:

```bash
zinet slice tests/fixtures/solver_problem.yaml nope
```

```text
zinet: error: unknown node: 'nope'
```

---

## 6. Compare two graphs: `zinet diff`

`diff` matches nodes by id and reports what was added, removed, or changed. Dependency order is
ignored, so reordering a `deps` list is not a change.

```bash
zinet diff tests/fixtures/spl_pipeline.yaml tests/fixtures/concept_book.yaml
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
zinet diff before.yaml after.yaml || echo "graph changed"
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
zinet validate pipeline.yaml
```

Imports are merged, and ids must stay unique across the whole tree. Two files that define the same
id, or an import cycle, fail at load time with exit code 2. The merged graph is validated as one.

---

## 8. Python API

Everything the CLI does is available from Python:

```python
from zinet import load_graph, validate, slice_to, diff_graphs, dump_graph, to_mermaid

graph = load_graph("tests/fixtures/solver_problem.yaml")   # resolves imports

for issue in validate(graph):
    print(issue)

prereqs = slice_to(graph, "budget_constraint")
dump_graph(prereqs, "budget_part.yaml")

print(to_mermaid(graph))
```

`load_graph` does not validate on its own. Call `validate` when you want the structural checks (`validate(graph, checks=["reducible", "connected"])` adds the optional ones).

The same graph as a `networkx` graph gives you the shared algorithms: `G = zinet.to_networkx(graph)`, then `zinet.learning_path(G, "app")`, `zinet.productivity_order(G)`, `zinet.reducible(G)` and others (see the README, "Graph algorithms").

---

## 9. Typical workflow

```bash
zinet validate pipeline.yaml                       # 1. check the graph
zinet render pipeline.yaml --format mermaid > pipeline.md   # 2. document it
zinet slice pipeline.yaml final_report -o part.yaml         # 3. extract what one target needs
zinet diff main.yaml feature.yaml                  # 4. review a change to the graph
```

---

## 10. Format a graph: `zinet prettify`

`prettify` compares a file with its canonical form: `version` first, layers in order, list items
indented under their keys, and defaults omitted. Without `--write`, it prints a diff and changes
nothing. It exits 1 when the file would change, so it can run in CI.

```bash
zinet prettify messy.yaml             # show the diff
zinet prettify messy.yaml --write     # rewrite the file in place
```

```text
--- messy.yaml
+++ messy.yaml (prettified)
@@ -1,3 +1,5 @@
+version: '1.0'
 primitives:
-  - meta: {x: 1}
-    id: a
+  - id: a
+    meta:
+      x: 1
```

`prettify` formats one file and never resolves imports, so imported nodes are not copied into it.
YAML comments are kept: each stays next to the node, key or section it was on (a comment block at the top of the file stays
on top). `--write` refuses a file only if a comment could not be put back exactly, and then exits 2 without changing it.
A comment on an entry of a block `deps:` list stays on that entry (while the entry is still at the same position in the list).

### Converting to JSON and back: `zinet convert`

```bash
zinet convert graph.yaml            # writes graph.json; the comments go into ~/.zinet/comments.db
zinet convert graph.json            # writes graph.yaml, with the comments put back
zinet convert graph.yaml -o out/g.json --store my-comments.db
```

JSON cannot hold comments, so they wait in a small SQLite database (`$ZINET_HOME`, `--store`) until the JSON is converted back.
Comments you add to the YAML between two conversions are kept. A comment whose node was removed or renamed is written at the end of
the file as `# [orphaned from <id>] ...` and returns if the node comes back.

---

## 11. JSON Schema: `zinet schema`

`schema` prints the JSON Schema for `graph.yaml`, which editors and other tools can use to check
files. The committed copy is `schemas/graph.schema.json`:

```bash
zinet schema                                  # print to stdout
zinet schema -o schemas/graph.schema.json     # regenerate the committed file
```

The specification in `docs/SPECIFICATION.md` covers the rules a schema cannot express, such as
the layer dependency rules and cycle detection.

---

## Quick reference

```text
zinet convert FILE [-o OUT] [--store DB]
zinet diff OLD NEW
zinet prettify FILE [--write]
zinet render FILE [--format svg|png|pdf|mermaid|html|ascii] [-o OUT] [--no-imports]
zinet schema [-o OUT]
zinet slice FILE TARGET [-o OUT]
zinet validate FILE [--no-imports] [--check reducible|connected] [--strict]
zinet --version
```
