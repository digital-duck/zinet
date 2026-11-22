# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`zinet` is the `graph.yaml` intermediate representation shared across the ZiNets ecosystem (SPL, ConceptBook, graph-code,
GraphLang/`graf`, work-graph, Solver): Pydantic schema, structural validator, transforms, graph algorithms, comment-preserving
YAML round-tripping, and `zinet.vis` (drawing for *any* `networkx` graph). Other repos depend on it, so behaviour changes
ripple outward; see `CHANGELOG.md` for how releases are described.

## Commands

```bash
uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"   # dev install (README's way)
pytest                                     # whole suite (testpaths = tests)
pytest tests/test_validator.py::test_name  # one test
zinet schema -o schemas/graph.schema.json  # regenerate the JSON Schema after changing schema.py
python -m build && twine upload dist/*     # release (build/twine are in the dev extra)
```

There is no linter or formatter configured.

- `tests/test_schema.py` fails if `schemas/graph.schema.json` is stale: regenerate it whenever `schema.py` changes.
- `tests/test_vis_page.py` checks the interactive page's JavaScript with `node --check` and drives it in headless Chrome;
  those tests are skipped silently when `node` / Chrome are missing, so a pass without them does not cover the page's JS.
- svg/png/pdf output and Graphviz-based layouts need `dot` on PATH; related tests adapt or skip without it.
- Version lives in both `pyproject.toml` and `src/zinet/__init__.py` (`__version__`); bump both on release.

## Architecture

Two independent halves share the package:

1. **The zinet format** (operates on `schema.Graph`):
   `schema.py` (Pydantic models; unknown keys rejected, domain data only in opaque `meta`) → `io.py` (`load_graph` resolves
   `imports` by merging nodes without namespacing; it does **not** validate) → `validator.py` (returns `Issue` lists; optional
   checks `not_reducible`/`disconnected` are off by default so existing graphs stay valid) → `transforms/` (`diff_graphs`,
   `slice_to`) → `render.py` (DOT/Mermaid for a `Graph`; the `html`/`ascii` formats delegate to `zinet.vis`).
   `formats.py` detects GraphLang workflows and ConceptBook-dialect files by *content* so `load_graph` can explain them instead
   of raising a schema error. `prettify.py` + `roundtrip.py` do canonical formatting while harvesting and re-attaching YAML
   comments (and the SQLite comment store used by `zinet convert` YAML↔JSON). `cli.py` wires these into `zinet` subcommands
   (exit 1 = errors/diff/non-canonical, exit 2 = usage/load/render error).

2. **Generic networkx layer** (no dependence on `Graph`): `algorithms.py` works on a `DiGraph` whose edges run dependency →
   dependent with an optional node `kind`; `to_networkx` bridges from a `Graph`. `vis/` draws any graph: `engines.py` is the
   registry (`cytoscape` default, `graphviz`, `mermaid`, `ascii`, optional `pyvis`/`graphify`), and engines never read
   attribute names directly — a `vis.style.Style` is a bundle of small functions that map each app's own attributes
   (label, kind, colour, shape, group, dashed edges, ...). Add per-app look via a `Style`, not by renaming attributes or
   special-casing an engine. `vis/cytoscape.py` emits one self-contained HTML page with the bundled
   `vis/data/cytoscape.min.js` and, when `dot` is available, precomputed expanded and collapsed-group layouts from `vis/dot.py`.
   `vis/select.py` trims big graphs (filters, neighbourhood, hidden kinds, hub edges, node cap).

## Characterization tests (behaviour-preservation contract)

The algorithms, round-trip and vis code were moved in from copies in sibling apps. `tests/characterization/golden/*.json`
freezes what those copies did; `test_algorithms_characterization.py`, `test_roundtrip.py` and `test_vis_characterization.py`
require zinet to reproduce them exactly. Where the copies disagree (`tests/characterization/divergences.md`), zinet exposes a
parameter selecting each behaviour (e.g. `reducible`'s four rules, `order=`), defaulting to graph-code's — keep such options
rather than "simplifying" them away. `tests/characterization/generate.py [--check]` regenerates goldens and needs the sibling
repos (or `ZINET_SOURCES_DIR`); it is not part of pytest. `golden/graphlang_engines.json` is frozen permanently (GraphLang now
draws through zinet) — never regenerate it.

## Format rules worth remembering

`docs/SPECIFICATION.md` is normative for rules a schema can't express; the JSON Schema is normative for structure. Three
layers `primitives` / `concepts` / `applications`; primitives have no `deps`; nothing may depend on an application; ids are
unique across the whole import tree. Domain-specific checks belong in back-ends, not here.
