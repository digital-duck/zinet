# graph-ir TODO: Cross-Repo Refactoring

Future work for moving shared graph logic from graph-code, cba (ConceptBook App), and spl (spl3)
onto graph-ir. Nothing here is started unless marked otherwise. Items are in rough priority order
within each section.

Background: [README-graph-vision.md](README-graph-vision.md) describes the `graph.yaml` IR design.
graph-ir v0.1.0 implements the flat v1.0 schema (primitives, concepts, applications). graph-code
uses the richer v2.1 schema (form/function spaces, events, transitions, aliased imports), so the
two cannot be merged directly. Work is to share the schema-agnostic algorithms first.

---

## graph-code

Repo: `~/projects/digital-duck/graph-code` (module `src/graph_code/`).

- [ ] **Replace `acyclic` with graph-ir cycle detection.** `graph_lib.py:83` calls `nx.simple_cycles`,
  which enumerates every cycle and can be exponential. Use `graph_ir.topological_order` and its
  `CycleError.members`. Keep the same `ToolFailed` message.
- [ ] **Replace `build_order` with `graph_ir.topological_order`.** `graph_lib.py:214`. Confirm that
  the tie-break order (graph-ir sorts ties alphabetically) is acceptable for `grafcode order`
  output and for `build_component.spl`, which consumes it.
- [ ] **Express `learning_path` and `gap` on top of `graph_ir.ancestors`.** `graph_lib.py:164`.
  Keep graph-code's own logic for the known set and primitive exclusion. Only the transitive
  closure is shared.
- [ ] **Share the core structural checks.** `validate_full` (`graph_lib.py:563`) overlaps with
  graph-ir's `validate` on cycles, unknown deps, and orphans. Keep the event, transition, and
  call-contract checks in graph-code. Map its warnings onto graph-ir `Issue` codes.
- [ ] **Decide how v2.1 maps onto graph-ir's model.** Options: (a) keep graph-ir flat and convert
  graph-code's form graph to it for the shared checks; (b) extend graph-ir `Graph` with optional
  form/function blocks; (c) keep the two schemas separate and share only the algorithms. Recommend
  (a) or (c) first. Record the decision in the vision doc before changing code.
- [ ] **Evaluate adopting aliased imports.** `resolve_imports` (`graph_lib.py:403`) namespaces
  imported symbols as `<alias>.<export>` and supports `optional`, `exports`, and `bind`. graph-ir
  currently merges without namespacing and rejects duplicate ids. Adopting alias namespacing is a
  breaking change to `load_graph`, so it needs a version bump and a migration note.
- [ ] **Evaluate `suggest_clusters` as a graph-ir transform.** `graph_lib.py:978`, exposed as
  `grafcode tools suggest-graph-clusters`. Not yet verified to be domain-free. Read the body
  before moving it.
- [ ] **Point CLI commands at graph-ir where the logic is shared.** `grafcode validate`,
  `order`, and `validate-all` (`src/graph_code/cli.py`). Keep the output format of each
  command unchanged, and check it with the existing tests.
- [ ] **Keep drift in graph-code.** `drift_report` and the LLM intent component
  (`graph_lib.py:906`) are semantic and domain-specific. Do not move them into graph-ir.
- [ ] **Keep graph-code-only tooling in graph-code.** `extract`, `build`, `ide`, `scaffold-*`,
  `spl-lint`, `new-app`, `clean-port`, and `prettify` depend on graph-code apps, spl3 workflows,
  or its Vue and FastAPI tooling. Do not move these.

## cba (ConceptBook App)

Repo: `~/projects/digital-duck/conceptbook-app`. Not yet inspected in this work. The items below
are based on the vision doc and must be checked first.

- [ ] **Inventory cba's graph code.** Find where `cba gen-graph` builds the `graph.html` data, and
  where `concept-book-press validate` runs its checks. List which checks duplicate graph-ir's
  `validate` and which are education-specific.
- [ ] **Share validation.** Make `concept-book-press validate` call graph-ir `validate` for the
  structural checks, keeping cba's own checks for concept-book content.
- [ ] **Share prerequisite paths.** Where cba computes prerequisite closures for navigation, use
  `graph_ir.slice_to` or `graph_ir.ancestors`.
- [ ] **Decide whether `graph.html` generation moves to graph-ir.** graph-ir `render` covers
  SVG, PNG, PDF, and Mermaid, but not the interactive navigator. Keep the interactive explorer in
  cba unless a shared data-preparation step is clearly reusable. The vision doc (Practical
  implications, item 3) names `cba gen-graph` as the free documentation step.
- [ ] **Align edge types.** cba's prerequisite edges should map to graph-ir `EdgeType.PREREQUISITE`
  (`prerequisite_of` in the Gemini feedback). Confirm the mapping against cba's actual data.

## spl (spl3)

Repo: `~/projects/digital-duck/SPL.py` (per the vision doc). Not yet inspected in this work.

- [ ] **Compile `.spl` scripts to `graph.yaml`.** This is the TODO from the vision doc
  ("SPL scripts as graph.yaml") and the first step in the Gemini feedback. Map tools to primitives,
  workflow steps to concepts, and recipes to applications. Emit a graph built with `graph_ir.Graph`
  and validated before writing.
- [ ] **Consume `graph.yaml` as input.** The Gemini feedback proposes a symmetric pipeline:
  front-ends write `graph.yaml`, spl3 executes it, and spl3 emits an updated `graph.yaml`.
- [ ] **Define edge typing for dataflow.** Map `input_of`/`output_of` to `data_flow`, and
  constraints to `constraint`, using graph-ir's `EdgeType`. Confirm the mapping against spl3's
  existing dependency handling.
- [ ] **Add execution state metadata.** The Gemini feedback suggests `status` and `cache_key` on
  intermediate nodes so spl3 can resume incrementally. Decide whether these live in `meta` (the
  current opaque payload) or in a new typed field, and record that decision in graph-ir's README.
- [ ] **Use graph-ir for ordering.** Replace spl3's own topological sort with
  `graph_ir.topological_order`, if it has one.
- [ ] **Keep graph-code's `.spl` files working during migration.** `src/graph_code/spl/*.spl`
  (`build_app`, `build_component`, `compile_blueprint`, `integrate_system`,
  `compute_intent_drift`) are used by `grafcode build` and `extract --llm`. Migrate them only after
  spl3 can read `graph.yaml`, and keep the `.spl` form working until then.

## graph-ir (follow-ups from these items)

- [ ] **Write `docs/SPECIFICATION.md`.** The formal `graph.yaml` spec, which the Gemini feedback
  lists as the first action item. Include the layer rules, edge types, and import semantics.
- [ ] **Export JSON Schema.** Generate `schemas/graph.schema.json` from the Pydantic models, so
  non-Python tools (cba, spl3 in other languages) can validate.
- [ ] **Decide on import namespacing.** See the graph-code item above. Record the decision and
  the migration path.
- [ ] **Add `gir fmt`.** Canonical YAML formatting, the graph-ir counterpart of graph-code's
  `prettify`.
- [ ] **Keep the tutorial current.** `docs/GUIDE/TUTORIAL.md` must follow any CLI change.
  Subcommands are now alphabetical in `gir -h`, but the tutorial's section order is still
  validate, diff, slice, render.
