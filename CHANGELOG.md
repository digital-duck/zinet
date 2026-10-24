# Changelog

## 0.2.1

- `Style.show_kind` (default `True`): set it to `False` and nodes show only their label, in the interactive page, graphviz, mermaid and pyvis; the colour and the legend still say the kind.
- Node text in the interactive page wraps inside the box (long labels no longer overflow).
- Tests: the page's JavaScript is checked with `node` and its behaviour in headless Chrome (skipped when either is missing).

## 0.2.0

Additive: the public API of 0.1.0 (`load_graph`, `validate`, `diff_graphs`, `slice_to`, `dump_graph`, `render`) is unchanged.

### Added
- **Graph algorithms** on a plain `networkx.DiGraph` (`zinet.algorithms`): `to_networkx`, `is_acyclic`, `ensure_acyclic`, `restrict`, `applications_of`, `build_order`, `learning_path`, `gap`, `productivity_order`, `reducible`, `mandatory_subgraph`. Options reproduce the copies in graph-code and ConceptBook. `topological_order` and `ancestors` also accept a `DiGraph`. New `UnknownNodeError` (a `KeyError`).
- **Optional validator checks** `not_reducible` and `disconnected` (`validate(checks=...)`, `zinet validate --check NAME` / `--strict`), off by default.
- **`zinet.vis`**: draw and trim any `networkx` graph. Engines cytoscape (interactive HTML, works offline, Cytoscape.js bundled), graphviz, mermaid, ascii in the core install; pyvis and graphify as extras (`zinet[pyvis]`, `zinet[graphify]`). `Style`, `select`. The page shows data edges on demand, highlights a node's connections, and collapses groups.
- **`zinet render --format html|ascii`.**
- **Comment-preserving YAML** (`zinet.roundtrip`): `zinet prettify --write` keeps comments; `zinet convert` goes between YAML and JSON, keeping comments in a small SQLite database (`~/.zinet/comments.db`, `$ZINET_HOME`, `--store`).
- **`zinet.formats`**: a GraphLang workflow or a ConceptBook / graph-code graph is reported as such, with the command to use, instead of a schema error.

### Changed
- `prettify --write` no longer refuses files with comments; it refuses only if a comment cannot be put back exactly.

### Notes
- Core dependencies are unchanged (networkx, pydantic, pyyaml). The wheel now includes `src/zinet/vis/data/cytoscape.min.js` (Cytoscape.js 3.30.2, MIT) with its license.
