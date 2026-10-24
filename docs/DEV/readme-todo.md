# zinet TODO: Cross-Repo Refactoring

Future work for moving shared graph logic from graph-code, cba (ConceptBook App), and spl (spl3)
onto zinet. Nothing here is started unless marked otherwise. Items are in rough priority order
within each section.

Background: [README-graph-vision.md](README-graph-vision.md) describes the `graph.yaml` IR design.
zinet v0.1.0 implements its own flat v1.0 schema (primitives, concepts, applications as lists of nodes with `deps`; ConceptBook's flat v1.0 writes the same layers as mappings with `composed_of` / `needs`, see the ecosystem page). graph-code
uses the richer v2.1 schema (form/function spaces, events, transitions, aliased imports), so the
two cannot be merged directly. Work is to share the schema-agnostic algorithms first.


---

## Shared-code consolidation review (2026-10-24)

Review of ConceptBook (all `cb-*` / `concept-book*` repos, `conceptbook-app`), graph-code, work-graph
and GraphLang (`graflang`) for graph code that should live here, so the apps stay lean. Counts were
measured by file hash and line count on 2026-10-24. Nothing below is started unless marked.

### Decisions already made

- **File names.** `*.graph.yaml` is a GraphLang workflow. Plain `graph.yaml` is a zinet graph.
  There is **no** `*.zinet.yaml`: `zinet` is a tool brand, not a file format, and `.yaml` is the
  base format ("graph" says the file persists graph data). The name is only a convention: tools tell
  the two kinds apart by content (`workflow:` + `nodes:` + `edges:` is GraphLang; `primitives:` /
  `concepts:` / `applications:` is a knowledge graph), so a file called `graph.yaml` works with either tool.
  Note (found 2026-10-24): "knowledge graph" covers two dialects, zinet's (lists, `deps`) and ConceptBook /
  graph-code's (mappings, `composed_of` / `needs`); zinet cannot read the second yet. See question 6.
- **zinet and GraphLang stay separate repos.** zinet is a published, domain-free library (a static
  dependency DAG: `deps`, `edge_types`, opaque `meta`). GraphLang is an executable workflow IR
  (typed nodes with ports, `triggers`/`binds` edges, cycles allowed for retries, Cedar). The models
  do not match, and folding zinet into graflang would make SPL, ConceptBook and Solver depend on
  cedarpy, dd-llm and a runtime they do not need.
- **Minimal dependencies (WEN, 2026-10-24).** The core install stays small. It holds everything that
  needs no heavy package: the algorithms, the validator, the cytoscape viewer (JavaScript bundled in
  the wheel), graphviz (through the `dot` program), mermaid, ascii, and comment-preserving YAML
  (`ruamel.yaml`). `pyvis` (pulls in ipython, jinja2, jsonpickle) and `graphify` (numpy, rapidfuzz and
  about 25 tree-sitter packages) stay optional extras: `zinet[pyvis]`, `zinet[graphify]`.
- **Scope for now: graph-code, work-graph and GraphLang.** The ConceptBook paper is work in progress,
  so ConceptBook is frozen (the refactoring will be revisited in future): the `cb-*` repos (and the other copies of `concept_graph.py` /
  `graph_lib.py`) are not touched, and refactoring `concept-book-press` and `concept-book-base` is
  **on hold** (see "On hold" below). Nobody deletes the 19 copies.
- **No release pressure.** Take the time to do it right. Work on a branch; `0.2.0` is cut when the
  work is ready, and other repos use editable installs until then.
- **`spl2graph` stays in SPL.py.** The SPL cookbook will be migrated to a GraphLang cookbook (a big
  task). Once GraphLang is well tested and proven, SPL development may stop and the focus shifts to
  GraphLang. So the SPL-to-`graph.yaml` items in the spl section below are on hold too.

### What is duplicated today

| Code | Copies | Size each | Notes |
|---|---|---|---|
| `scripts/concept_graph.py` | 19 repos, 7 variants | 1,498 to 1,720 lines (about 28,000 in total) | `acyclic`, `reducible`, `ancestors`, `gap`, `learning_path`, `productivity_order`, four renderers (`_to_mermaid`, `_to_dot`, `_to_ascii`, and a `_to_html` of about 630 lines), a YAML loader and writer, and a click CLI (`stats`, `show`, `ancestors`, `path`, `order`, `visualize`, `export`, `compose`, `convert`, `share`). Copies live in `cb-*`, `concept-book`, `concept-book-base`, `cb-zinets`, `conceptbook-app`, `graph-driven-workflow`, `SPL.py`. |
| `spl/graph_lib.py` | 18 repos, 5 variants | 656 to 679 lines (about 11,700 in total) | the same algorithms as a library, plus domain-specific `verify_*` helpers (sympy/sage maths checks, character decomposition) that must **not** move. `concept-book-base` looks like the template that spreads it. |
| `concept-book-press/pipeline/validate/checker.py` | 1 | 200 lines | re-implements `validate`: acyclic, reducible, connected. |
| graph-code `graph_lib.py` and `loader.py` | 1 | 1,083 and 439 lines | its own `acyclic` (`nx.simple_cycles`, can be exponential), `reducible`, `productivity_order`, `learning_path`, `gap`, `build_order`, aliased `resolve_imports`. See the graph-code section below. |
| work-graph `convert.py` | 1 | 204 lines | comment-preserving YAML round-trip (`harvest` / `attach`) and a canonical dump, with ruamel. This is the item `prettify` lists as not implemented. |
| work-graph `viz.py` | 1 | 287 lines | `select` (filters, neighbourhood, node cap) and four engines: cytoscape (bundled Cytoscape.js 3.30.2, offline), pyvis, graphify, graphviz. |
| GraphLang `graphlang/grafv/` | 1 | about 430 lines (`engines.py` and `model.py`) | the cytoscape and graphviz engines copied from work-graph, plus pyvis, graphify and mermaid, over a small neutral graph model (`label`, `kind`, `color`, `parent`, edge `label` and `relation`). Adds node positions from `dot -Tjson`. |
| renderers in general | at least 6 implementations | | zinet `render.py`, the 19 `concept_graph.py` copies, work-graph, GraphLang, SPL.py `spl2mmd.py`. |

### What should stay out of zinet

- ConceptBook: the `verify_*` maths helpers and the ZiNets / Chinese-character builders (`cb-zinets/scripts/zinets_to_graph.py`).
- graph-code: events, transitions, call contracts, drift, intent drift, `suggest_clusters`, the blueprint and scaffold tooling.
- work-graph: layer partitions and context (`layers.py`), UIDs and refs (`refs.py`), search and embeddings (`query.py`), the Claude Code import.
- GraphLang: the runtime, Cedar, `topology.py` (port-level checks), format detection (`formats.py`).
- SPL.py: `spl2graph.py`, which targets GraphLang (see the spl section).

### Proposed shape in zinet

Core dependencies: networkx, pydantic, pyyaml and, new, ruamel.yaml. Nothing else is installed by default; `pyvis` and `graphify` are the only optional extras. All changes are additive (the public API of 0.1.0 does not change) and ship as 0.2.0 when ready.

Design requirements that come from the three apps we are adopting first:

- **Algorithms take a plain `networkx.DiGraph`**, not only a zinet `Graph`, because graph-code works on `GraphDomain.form_graph` and ConceptBook on `nx.DiGraph`. `to_networkx(Graph)` is the bridge, and it sets `kind` from the layer. Variants of `reducible` are parameters, not separate functions.
- **The drawing engines take a `networkx.MultiDiGraph` plus style functions** (node label, colour, shape and group; edge label and style), not fixed attribute names. work-graph colours by `layer` and dashes `INFERRED` edges; GraphLang colours by node type, draws `binds` edges dashed and a `LOOP` as a box (a `parent` group). One set of engines must serve all three without each app renaming its attributes.

| Module / extra | What moves in | Replaces |
|---|---|---|
| algorithms (extend `dag.py`) | `acyclic`, `restrict`, `applications_of`, `gap`, `learning_path`, `productivity_order`, `minimal`, `build_order`, a parametrised `reducible`; a `to_networkx(Graph)` helper that sets `kind` from the layer | `graph_lib.py` x18, the algorithm halves of `concept_graph.py` x19, graph-code's equivalents |
| validator | the connected and reducible checks, as new issue codes | `concept-book-press` `checker.py` |
| `zinet.vis` (core) | engines cytoscape, graphviz, mermaid and ascii over the neutral graph model, plus `select`; node positions from `dot -Tjson` when Graphviz is installed. `pyvis` and `graphify` engines behind `zinet[pyvis]` / `zinet[graphify]` | work-graph `viz.py`, GraphLang `grafv/engines.py` (start from this one: it already has groups, positions and five engines) |
| `zinet.roundtrip` (core) | comment-preserving YAML read and write (ruamel); lets `prettify --write` handle commented files | work-graph `convert.py`; closes the "comment-preserving formatting" item in the README |
| `zinet` CLI | the generic commands of `concept_graph.py` (`stats`, `show`, `ancestors`, `path`, `order`, `visualize`, `export`, `convert`) | on hold with ConceptBook; the 19 copies stay |

### Suggested order (revised 2026-10-24)

**Phase A: zinet foundation (on a branch, no release pressure)**

1. [x] **Characterisation tests first** (done, `tests/characterization/`; see `divergences.md`). Freeze today's behaviour of graph-code's `acyclic`, `build_order`, `learning_path`, `gap`, `productivity_order` and `reducible` (its existing test suite is the starting point), and of work-graph's `convert.py` round-trip and GraphLang's engines. ConceptBook's variants are read only for reference; their tests wait until ConceptBook is un-held.
2. [x] **Algorithms and validator** (done, `src/zinet/algorithms.py`): plain `nx.DiGraph`, `to_networkx`, options that reproduce graph-code and both ConceptBook variants (`tests/test_algorithms_characterization.py`), one `CycleError` / `UnknownNodeError`. Optional validator checks `not_reducible` and `disconnected` (`zinet validate --check` / `--strict`), off by default so existing graphs stay valid.
3. [ ] **`zinet.vis`**: engines, `select` and the style functions, based on GraphLang's `grafv`.
4. [ ] **`zinet.roundtrip`**: move work-graph's comment-preserving YAML in; make `prettify --write` accept commented files.
5. [ ] **Format recognition**: the zinet side of "say what a GraphLang file is" (cross-tool follow-ups below).

**Phase B: adoption, one app at a time (each keeps its own tests green)**

6. [ ] **GraphLang first.** `grafv/engines.py` (355 lines) is replaced by `zinet.vis`. `grafv/model.py` (workflow to graph) and `graf vis` stay. Smallest change: the engines already match, and it proves the style-function design.
7. [ ] **work-graph second.** `viz.py` engines and `convert.py` move to zinet; `select`, the layer colours and the `INFERRED` dashes become style functions. Keeps `layers.py`, `refs.py`, search and embeddings.
8. [ ] **graph-code third.** `acyclic` (today `nx.simple_cycles`, which can be exponential), `build_order`, `learning_path`, `gap`, `productivity_order` and `reducible` use zinet. Events, transitions, call contracts, drift and clustering stay. Largest semantic risk, so it goes last and relies on its existing tests.

**Later (decided separately)**

9. [ ] **Aliased imports and the v2.1 mapping** (graph-code section).

### On hold (ConceptBook: to be revisited in future)

- **`concept-book-press`**: swap `pipeline/validate/checker.py` for zinet's `validate`, then `publish/registry.py`. Future ingestion pipelines would benefit from the consolidated graph functions.
- **`concept-book-base`**: the template for new domain repos. Replace `spl/graph_lib.py` and `scripts/concept_graph.py` with zinet, keep the `verify_*` maths helpers in a slim domain module, and call the `zinet` CLI instead of a script path (`sync_from_press.py`). Acceptance test: generate a brand-new concept book from the base (as its own `docs/readme-refactor.md` already requires).
- **The `zinet` CLI commands from `concept_graph.py`**, and where `compose` and `share` live.
- **Revisit in future** (WEN, 2026-10-24); there is no date. Phase A makes it cheap: the algorithms, engines and CLI will already be in zinet.
- **SPL to `graph.yaml`** (the spl section below): on hold until the SPL-to-GraphLang direction is settled.

### Risks

- **`reducible` is not one function.** graph-code has `first_radical_only`, ConceptBook has `strict`, and some copies decide by the `kind` attribute (an undeclared root is invalid). The results differ on edge cases, so freeze each variant's behaviour in a test before replacing it, and expose the differences as parameters.
- **The copies are not identical** (7 variants of `concept_graph.py`, 5 of `graph_lib.py`). Diff them and take the newest as the base. Some differences may be real fixes, some drift.
- **graph-code's v2.1 schema** (form, function and event spaces) is richer than zinet's flat one. Only the schema-agnostic algorithms move, as the graph-code section already says.
- **zinet is published (0.1.0 on PyPI).** The public API (`load_graph`, `validate`, `diff_graphs`, `slice_to`, `dump_graph`) must not change. Additions only.

### Cross-tool follow-ups (zinet and GraphLang)

- [ ] **zinet side: say what a GraphLang file is.** Today `zinet validate` on a GraphLang workflow fails with `unsupported graph version '1.0-graph'`. Detect `workflow:` / `nodes:` + `edges:` in `io._read` and say "this is a GraphLang workflow; use `graf validate|vis|run FILE`". Add a test.
- [x] **GraphLang side (done in graflang, not yet committed).** `graphlang/formats.py` detects a zinet file by content, and `graf run|validate|info|compile|check|vis` explain it instead of failing on a schema error. A GraphLang workflow named plain `graph.yaml` works.
- [ ] **README section "Two graph formats, one family"** in both repos: zinet is the static knowledge and dependency IR; GraphLang is the executable workflow IR; `spl3` is the bridge. Include the file-name rule above.
- [ ] **Optional: `graf vis` for zinet files.** Convert a zinet graph into GraphLang's neutral model (coloured by layer) so GraphLang's engines draw it. Only worth doing if `zinet[vis]` does not land first; if it does, GraphLang should use the shared engines instead.

### Open questions (answered by WEN on 2026-10-24; the resulting decisions are above)

1. Is zinet the home for all of the above, or should ConceptBook-specific commands (`compose`, `share`, `convert`) move to `cba` / `concept-book-press` instead?

[WEN] don't touch existing cb-*/ repos, they are already functional and tested.
but refactor /home/papagame/projects/digital-duck/concept-book-base, so that future conceptbook will be using new zinet codebase

[WEN] refactor concept-book-press too so future ingestion pipeline will benefit from consolidated graph functionality

2. Are engines and ruamel as optional extras (`zinet[vis]`, `zinet[roundtrip]`) acceptable, or do you want the interactive viewer in the core install?

[WEN] they belongs to core install

3. Should step 1 ship as zinet 0.2.0, with each repo migrating on its own schedule?

[WEN] no release pressure, we will take time to do the right thing

4. Who owns deleting the 19 `concept_graph.py` copies: a one-off script across all repos, or each repo when it is next touched?

[WEN] no cleanup for now, see #1, we will not touch cb-*/ codebases


5. Should `spl2graph` (SPL to GraphLang) stay in SPL.py, or should SPL scripts as `graph.yaml` (the spl section below) be the primary path, with GraphLang generated from it?

[WEN] let `spl2graph` (SPL to GraphLang) stay in SPL.py for now, we will migrate SPL cookbook to GraphLang cookbook (which is a big task), Once GraphLang is well tested and proven, we may stop developing SPL, but shift focus to GraphLang

6. **New (2026-10-24): should zinet's loader also read the ConceptBook / graph-code mapping dialect?** A real ConceptBook `graph.yaml` (`cb-linalg/public/domains/graph.yaml`) fails in `zinet validate` ("Input should be a valid list"), although the layers are the same. Options: (a) leave it: apps convert to a `networkx` graph themselves and use the shared algorithms (what Phase B does); (b) add a reader in zinet that accepts the mapping dialect and maps `composed_of` / `needs` to `deps` and the other fields to `meta`, so `zinet validate|render|slice` work on ConceptBook files; (c) also write that dialect. My suggestion: (a) now, (b) when ConceptBook is un-held, since it needs the same decisions as that refactor. Also decide what plain `graph.yaml` should mean in the file-name rule.

Feedback:  see my comments above tagged by "[WEN]"

---

## graph-code

Repo: `~/projects/digital-duck/graph-code` (module `src/graph_code/`).

- [ ] **Replace `acyclic` with zinet cycle detection.** `graph_lib.py:83` calls `nx.simple_cycles`,
  which enumerates every cycle and can be exponential. Use `zinet.topological_order` and its
  `CycleError.members`. Keep the same `ToolFailed` message.
- [ ] **Replace `build_order` with `zinet.topological_order`.** `graph_lib.py:214`. Confirm that
  the tie-break order (zinet sorts ties alphabetically) is acceptable for `grafcode order`
  output and for `build_component.spl`, which consumes it.
- [ ] **Express `learning_path` and `gap` on top of `zinet.ancestors`.** `graph_lib.py:164`.
  Keep graph-code's own logic for the known set and primitive exclusion. Only the transitive
  closure is shared.
- [ ] **Share the core structural checks.** `validate_full` (`graph_lib.py:563`) overlaps with
  zinet's `validate` on cycles, unknown deps, and orphans. Keep the event, transition, and
  call-contract checks in graph-code. Map its warnings onto zinet `Issue` codes.
- [ ] **Decide how v2.1 maps onto zinet's model.** Options: (a) keep zinet flat and convert
  graph-code's form graph to it for the shared checks; (b) extend zinet `Graph` with optional
  form/function blocks; (c) keep the two schemas separate and share only the algorithms. Recommend
  (a) or (c) first. Record the decision in the vision doc before changing code.
- [ ] **Evaluate adopting aliased imports.** `resolve_imports` (`graph_lib.py:403`) namespaces
  imported symbols as `<alias>.<export>` and supports `optional`, `exports`, and `bind`. zinet
  currently merges without namespacing and rejects duplicate ids. Adopting alias namespacing is a
  breaking change to `load_graph`, so it needs a version bump and a migration note.
- [ ] **Evaluate `suggest_clusters` as a zinet transform.** `graph_lib.py:978`, exposed as
  `grafcode tools suggest-graph-clusters`. Not yet verified to be domain-free. Read the body
  before moving it.
- [ ] **Point CLI commands at zinet where the logic is shared.** `grafcode validate`,
  `order`, and `validate-all` (`src/graph_code/cli.py`). Keep the output format of each
  command unchanged, and check it with the existing tests.
- [ ] **Keep drift in graph-code.** `drift_report` and the LLM intent component
  (`graph_lib.py:906`) are semantic and domain-specific. Do not move them into zinet.
- [ ] **Keep graph-code-only tooling in graph-code.** `extract`, `build`, `ide`, `scaffold-*`,
  `spl-lint`, `new-app`, `clean-port`, and `prettify` depend on graph-code apps, spl3 workflows,
  or its Vue and FastAPI tooling. Do not move these.

## cba (ConceptBook App)

> **On hold:** ConceptBook refactoring will be revisited in future (see "On hold" in the consolidation review above). Nothing here is started.

Repo: `~/projects/digital-duck/conceptbook-app`. Not yet inspected in this work. The items below
are based on the vision doc and must be checked first.

- [ ] **Inventory cba's graph code.** Find where `cba gen-graph` builds the `graph.html` data, and
  where `concept-book-press validate` runs its checks. List which checks duplicate zinet's
  `validate` and which are education-specific.
- [ ] **Share validation.** Make `concept-book-press validate` call zinet `validate` for the
  structural checks, keeping cba's own checks for concept-book content.
- [ ] **Share prerequisite paths.** Where cba computes prerequisite closures for navigation, use
  `zinet.slice_to` or `zinet.ancestors`.
- [ ] **Decide whether `graph.html` generation moves to zinet.** zinet `render` covers
  SVG, PNG, PDF, and Mermaid, but not the interactive navigator. Keep the interactive explorer in
  cba unless a shared data-preparation step is clearly reusable. The vision doc (Practical
  implications, item 3) names `cba gen-graph` as the free documentation step.
- [ ] **Align edge types.** cba's prerequisite edges should map to zinet `EdgeType.PREREQUISITE`
  (`prerequisite_of` in the Gemini feedback). Confirm the mapping against cba's actual data.

## spl (spl3)

> **On hold:** `spl2graph` stays in SPL.py, and the SPL cookbook is to be migrated to GraphLang first (see the decisions above). Nothing here is started.

Repo: `~/projects/digital-duck/SPL.py` (per the vision doc). Not yet inspected in this work.

- [ ] **Compile `.spl` scripts to `graph.yaml`.** This is the TODO from the vision doc
  ("SPL scripts as graph.yaml") and the first step in the Gemini feedback. Map tools to primitives,
  workflow steps to concepts, and recipes to applications. Emit a graph built with `zinet.Graph`
  and validated before writing.
- [ ] **Consume `graph.yaml` as input.** The Gemini feedback proposes a symmetric pipeline:
  front-ends write `graph.yaml`, spl3 executes it, and spl3 emits an updated `graph.yaml`.
- [ ] **Define edge typing for dataflow.** Map `input_of`/`output_of` to `data_flow`, and
  constraints to `constraint`, using zinet's `EdgeType`. Confirm the mapping against spl3's
  existing dependency handling.
- [ ] **Add execution state metadata.** The Gemini feedback suggests `status` and `cache_key` on
  intermediate nodes so spl3 can resume incrementally. Decide whether these live in `meta` (the
  current opaque payload) or in a new typed field, and record that decision in zinet's README.
- [ ] **Use zinet for ordering.** Replace spl3's own topological sort with
  `zinet.topological_order`, if it has one.
- [ ] **Keep graph-code's `.spl` files working during migration.** `src/graph_code/spl/*.spl`
  (`build_app`, `build_component`, `compile_blueprint`, `integrate_system`,
  `compute_intent_drift`) are used by `grafcode build` and `extract --llm`. Migrate them only after
  spl3 can read `graph.yaml`, and keep the `.spl` form working until then.

## zinet (follow-ups from these items)

- [x] **Write `docs/SPECIFICATION.md`.** The formal `graph.yaml` spec, which the Gemini feedback
  lists as the first action item. Include the layer rules, edge types, and import semantics.
- [x] **Export JSON Schema.** `zinet schema -o schemas/graph.schema.json` generates it from the
  Pydantic models, so non-Python tools (cba, spl3 in other languages) can validate. A test fails
  if the committed copy is stale.
- [ ] **Decide on import namespacing.** See the graph-code item above. Record the decision and
  the migration path.
- [x] **Add `zinet prettify`.** Canonical YAML formatting, the zinet counterpart of graph-code's
  `prettify`. Shows a diff by default, and `--write` rewrites in place. Comments are not preserved,
  so `--write` refuses files that contain them. Named `prettify`, not `fmt`, to match graph-code.
- [ ] **Keep the tutorial current.** `docs/GUIDE/TUTORIAL.md` must follow any CLI change.
  Subcommands are now alphabetical in `zinet -h`, but the tutorial's section order is still
  validate, diff, slice, render.
