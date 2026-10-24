# Characterization tests (Phase A, step 1)

These files freeze what the existing copies of zinet's future shared code do **today**, so the code can move into zinet
without changing anyone's results. They come first on purpose: the copies disagree in places (see
[divergences.md](divergences.md)), and a silent change would be a bug in an app that depends on the old behaviour.

| Golden file | Source (read only, never modified) | Frozen behaviour | Used by |
|---|---|---|---|
| `golden/graph_code.json` | graph-code `graph_lib.py` | `acyclic`, `reducible` (and `first_radical_only`), `productivity_order`, `build_order`, `learning_path`, `gap` | step 2 (algorithms) |
| `golden/conceptbook_v1.json` | concept-book `spl/graph_lib.py` | the same family, plus `ancestors`, `applications_of`, `reducible(strict=True)` | step 2; ConceptBook itself is on hold |
| `golden/conceptbook_v2.json` | conceptbook-app `spl/graph_lib.py` | as v1, with the older `reducible` rule | step 2; ConceptBook itself is on hold |
| `golden/workgraph_roundtrip.json` | work-graph `convert.py` | `harvest`, `attach`, `dump_yaml`: comments survive a rewrite, orphans, canonical key order | step 4 (`zinet.roundtrip`) |
| `golden/graphlang_engines.json` | graflang `graphlang/grafv` | Mermaid text, DOT text, cytoscape elements for the bundled workflows (no node positions) | step 3 (`zinet.vis`) |

`cases.py` and `roundtrip_cases.py` hold the inputs. They are small graphs, one behaviour each (a chain, a diamond, ties,
a dangling reference, a cycle, optional edges, a two-radical set, a missing target, and so on).

## How to use

```bash
python tests/characterization/generate.py          # rerun the sources and rewrite the golden files and divergences.md
python tests/characterization/generate.py --check  # exit 1 if a committed file no longer matches the sources
```

`generate.py` is a script, not part of `pytest`: it needs the sibling repos (`graph-code`, `concept-book`, `conceptbook-app`,
`work-graph`, `graflang`) next to this one, or `ZINET_SOURCES_DIR` pointing at them. The commit of each source is recorded in
the golden file. `tests/test_characterization_data.py` only checks that the committed files are complete and consistent, so the
normal test run needs nothing outside this repo.

## What step 2 does with them

For every behaviour on which the sources **agree**, the new zinet function must reproduce the golden result exactly.
For every row in `divergences.md`, zinet either picks one behaviour and says why, or offers a parameter that selects each
source's behaviour (`reducible` is the clearest case: three rules). Each choice is written next to its test, so a later
reader can see which app relied on what.
