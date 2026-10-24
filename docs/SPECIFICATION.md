# graph.yaml Specification (v1.0)

This document specifies the `graph.yaml` format as implemented by zinet 0.2.0. The machine-readable
schema is [`schemas/graph.schema.json`](../schemas/graph.schema.json), generated from the Pydantic
models by `zinet schema`. If this document and the schema disagree, the schema is the reference
for structure and this document is the reference for the rules that a schema cannot express.

Keywords MUST, MUST NOT, and MAY are used as in RFC 2119.

---

## 1. Document

A graph.yaml document is a YAML mapping with these top-level keys. Any other key is an error.

| Key | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `version` | string | no | `"1.0"` | Format version. Readers MUST reject versions they do not support. |
| `imports` | list of strings | no | `[]` | Relative paths to other graph.yaml files whose nodes are merged in (section 5). |
| `primitives` | list of nodes | no | `[]` | Layer 1 (section 2). |
| `concepts` | list of nodes | no | `[]` | Layer 2 (section 2). |
| `applications` | list of nodes | no | `[]` | Layer 3 (section 2). |

A document with no nodes is valid.

---

## 2. Nodes and layers

Every node lives in exactly one layer. The layer is the key under which the node is written, not a
field of the node.

| Layer | Role | Dependency rule |
|---|---|---|
| `primitives` | Irreducible leaves: built-in tools, parameters, variables, irreducible concepts | MUST have no `deps` |
| `concepts` | Ideas, steps, or components composed from other nodes | MAY depend on primitives and concepts |
| `applications` | Capstones: recipes, deployable systems, objectives, target concepts | MAY depend on any layer |

Nothing MAY depend on an application (see rule V4). Applications are terminal in the DAG.

### Node fields

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | non-empty string | yes | — | Identifier. Unique across the whole document, including imports. |
| `label` | string | no | none | Human-readable name. Used by `render`. |
| `deps` | list of ids | no | `[]` | Ids this node depends on. These are its incoming edges. |
| `edge_types` | mapping: dep id → edge type | no | `{}` | Optional type for individual dependencies (section 3). Each key MUST appear in `deps`. |
| `meta` | mapping | no | `{}` | Domain payload. Opaque to zinet: it is never read, validated, or transformed. |

Unknown fields on a node are an error. Domain data belongs in `meta`.

---

## 3. Dependency edges

An edge runs from each dependency to the node that lists it, so `deps` points "upstream". A
topological order lists dependencies before their dependents.

Each edge has a type. An edge without an entry in `edge_types` has type `depends_on`.

| Edge type | Meaning |
|---|---|
| `depends_on` | Default. Generic dependency or composition. |
| `data_flow` | A value or artifact passes from dependency to dependent. |
| `prerequisite` | The dependency must be understood before the dependent. |
| `constraint` | The dependency bounds or defines the dependent (for example, a solver constraint). |
| `inheritance` | The dependent extends or specializes the dependency. |

Edge types affect rendering and documentation only. Validation treats all edges the same.

---

## 4. Validation

`validate` returns a list of issues. Each issue has a severity, a code, and optionally a node id.

### Errors

| Code | Rule |
|---|---|
| `duplicate_id` (V1) | Each id MUST be defined once in the document after imports are merged. |
| `unknown_dep` (V2) | Every entry in `deps` MUST name a defined id. |
| `primitive_has_deps` (V3) | A node in `primitives` MUST have an empty `deps`. |
| `layer_violation` (V4) | No node MAY list an application in its `deps`. |
| `cycle` (V5) | The dependency graph MUST be acyclic. A self-dependency is a cycle. |

### Warnings

| Code | Rule |
|---|---|
| `orphan` | A node with no `deps` and no dependents, in a document with more than one node. Warnings do not make a document invalid. |

### Optional checks

Off by default, so a document that is valid under v1.0 stays valid. A reader MAY offer them (`zinet validate --check NAME` or `--strict`).

| Code | Severity | Rule |
|---|---|---|
| `not_reducible` | error | With `reducible`: when the document has primitives and no cycle, every concept and application SHOULD have at least one primitive among its transitive dependencies. |
| `disconnected` | warning | With `connected`: the document SHOULD be one piece when edges are read as undirected. |

A document is valid when it has no errors. Structural validation does not check `meta`, `label`,
or domain semantics. Those belong to the consuming tool.

---

## 5. Imports

- `imports` entries are paths relative to the directory of the file that lists them.
- Imports are resolved recursively. Each imported file is read with the same rules as the importing file.
- Imported nodes are merged into their layers, in import order, before the importing file's own nodes.
- Imported nodes keep their ids. There is no namespacing, so ids MUST be unique across the whole import tree.
- Import cycles are an error.
- The resolved graph has no `imports`. Loading does not validate. Run validation separately.

Namespacing and optional imports are not in v1.0. See `docs/DEV/readme-todo.md`.

---

## 6. Formatting

The canonical form is the output of `zinet prettify --write`:

- `version` first, then `imports` if present, then the layers in order `primitives`, `concepts`, `applications`.
- Node keys in the order `id`, `label`, `deps`, `edge_types`, `meta`.
- Fields holding their default value are omitted, except `version`, which is always written.
- List items are indented under their parent key.

Formatting does not change meaning. Comments are kept: each is anchored to the node (by `id`), the node key or the top-level
section it sits next to, and re-attached in the canonical text; a comment block above the first line stays at the top of the
file. A formatter MUST NOT rewrite a file if a comment cannot be put back. Comments on lines deeper than a node's own keys
move to the key they belong to; a comment on an entry of a block `deps` list is anchored to the entry by position and moves to the `deps` key if the entry is gone.

---

## 7. Serialization

- Files are UTF-8. Non-ASCII labels and ids are written as-is.
- Enum values are written as their lowercase string form (for example, `data_flow`).
- Round-tripping a valid document through load, dump, and load produces an equal graph.

---

## 8. Compatibility

- v1.0 is the flat layered schema in this document.
- graph-code uses the richer v2.1 schema (form and function spaces, events, transitions, aliased
  imports). v2.1 documents are not valid v1.0 documents. Mapping between them is future work.
- The JSON Schema describes structure only. The rules in sections 2 to 5 apply on top of it.
