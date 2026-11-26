# zinet code review (Opus 5.5)

Date: 2026-11-25 · Commit reviewed: `94cd687` (main, clean) · Scope: `src/zinet/` (2,434 lines), the CLI, the tests.

**How I checked it.**

- I read the format half (`schema`, `io`, `validator`, `dag`, `transforms`, `formats`, `prettify`, `roundtrip`, `cli`), and the parts
  of `algorithms` and `vis/cytoscape.py` that handle data.
- `pytest`: **203 passed, 1 skipped** (7.7 s). The interactive page's own tests (`test_vis_page.py`, 10) ran for real, since `node`,
  `dot` and Chrome are installed here, so their pass covers the page's JavaScript.
- Every bug marked **confirmed** was reproduced through the `zinet` CLI on a small file. Version 0.2.3 matches in `pyproject.toml`
  and `__init__.py`.

## 1. Summary

zinet is small, careful and well-tested. It is the most mature of the shared packages:

- a strict schema (unknown keys rejected);
- validation that returns issues instead of raising;
- characterization tests that freeze the behaviour of the copies it replaced, with options instead of "simplifications" where those
  copies disagree;
- a vis layer that maps each app's attributes through a `Style` instead of special-casing.

Two real bugs:

- **(B1)** a graph whose imports form a diamond cannot be loaded;
- **(B2)** `zinet prettify --write` can silently drop a comment.

The rest are small edges.

## 2. Strengths

| Area | What is good |
|---|---|
| Schema | `extra="forbid"` on nodes and graphs catches typos; `edge_types` must name real deps (`schema.py:41-46`); domain data lives only in opaque `meta`. |
| Validator | Issues, not exceptions; optional checks (`reducible`, `connected`) are off by default so existing graphs stay valid; unknown deps are filtered before the cycle check, so one problem is not reported as two. |
| Foreign files | `formats.explain_foreign` says "this is a GraphLang workflow" or "a ConceptBook graph" instead of a schema error: the right answer for a format that several tools write under one name. |
| Behaviour contract | `tests/characterization/` freezes what the old copies did; `reducible` keeps all four rules and `order=` both orders. book-graph's port confirmed this pays off: 260 / 260 ConceptBook graphs keep the SPL teaching order (`productivity_order` breaks ties by id, so it is deterministic across processes). |
| Prettify safety | Comments are harvested and re-attached; when one cannot be put back, the CLI **refuses to write** (`cli.py`, `_cmd_prettify`). |
| Interactive page | Data is embedded with `</` escaped (`vis/cytoscape.py:343`); the side panel escapes labels (`esc(d.label)`). A label `</script><img src=x onerror=alert(1)>` neither closed the script nor fired, in Chromium. |

## 3. Bugs

### B1 (Medium, confirmed): a diamond of imports cannot be loaded

`io._resolve` merges every imported file's nodes into one list and treats a second sighting of an id as a duplicate
(`io.py:72-76`). When two files import the same third file, its nodes arrive twice:

```
a.yaml: imports [b.yaml, c.yaml]     b.yaml: imports [d.yaml]     c.yaml: imports [d.yaml]
$ zinet validate a.yaml
zinet: error: duplicate node id 'd': defined in b.yaml and c.yaml        (exit 2)
```

The message is also wrong, since `d` is defined only in `d.yaml`: `add` records the importing child's path, not the file that
defines the node. A shared "common primitives" file imported by several chapters is the natural use of `imports:`, and it is
exactly what fails.

**Fix:** remember which resolved files were already merged, and skip a file the second time; keep the duplicate-id error for
*different* files defining the same id. Record the defining file in `origin`, so the message names it.

### B2 (Medium, confirmed): `prettify --write` drops a comment that follows an apostrophe

`roundtrip._split_comment` (`roundtrip.py:54-65`) treats `'` as the start of a quoted string even inside a plain scalar. In
`label: Newton's law  # keep me`, the `#` is then "inside quotes", so `harvest` never sees the comment. Because it was never
harvested, it cannot count as lost, so the refusal guard does not fire:

```
$ zinet prettify g.yaml --write
g.yaml: rewritten                      (exit 0; the "keep me" comment is gone, a plain trailing comment on another line survives)
```

This is silent data loss in a command whose promise is to keep comments. Labels and `defines` with an apostrophe are common in
concept graphs ("Newton's", "Euler's").

**Fix:**
- only treat a quote as opening a string where YAML would: at the start of a scalar, after `: `, `- `, `[`, `{` or `,`;
- and, as a backstop, refuse to write when `has_comments(original)` counts more comment lines than `harvest` found. The prettify
  module already computes `has_comments` but nothing uses it for that.

### B3 (Low, confirmed): imports can read any file

`imports:` paths are joined to the importing file's folder with no confinement (`io.py:80`): `imports:
[../../../../../../etc/hostname]` was opened (it failed only because it is not a mapping). For a local tool this matters only when
a `graph.yaml` comes from someone else. Then a graph can probe the reader's files, and the error messages echo the path. Confining
imports to the importing file's tree, or to an opt-in root, would close it.

### B4 (Low, confirmed): a dependency listed twice passes validation

`deps: [p, p]` validates as `ok` (`zinet validate`). `to_networkx` collapses it to one edge and `diff_graphs` compares the sorted
list, so the duplicate is harmless downstream. But it is almost always a mistake, and the validator is the place to warn about it
(`duplicate_dep`, a warning).

## 4. Smaller notes

- `formats.detect` calls a file with an empty mapping layer (`concepts: {}`) a ConceptBook graph. That is harmless, since the
  explanation is still right.
- `io.to_yaml` writes `version` first, then `model_dump(exclude_defaults=True)`. A graph with only default fields round-trips to just
  `version: '1.0'`. That is fine, but worth a test, since `prettify` relies on it.
- `vis/cytoscape.py:340` embeds `__OPTS__` with `json.dumps` and no `</` escape, unlike the data on line 343. The options come from
  the app's `Style`, not the graph, so this is not reachable from a graph file today; escaping it the same way would remove the
  difference.

## 5. Gaps

- **Diamond imports** (B1) need a test. The current import tests cover a chain and a cycle, not a shared file.
- **A comment-safety test with apostrophes and `#` inside plain scalars** (B2).
- **CLAUDE.md** says svg/png/pdf need `dot`, and the related tests adapt or skip. On a machine without `dot` and Chrome, a green run
  covers neither the layouts nor the page's JavaScript. A CI note, or a marker that says what was skipped, would make that visible.

## 6. Suggested order

1. **B2:** silent loss in a command that promises to keep comments.
2. **B1:** a shared import file is the obvious multi-chapter layout.
3. **B4**, then **B3**.
