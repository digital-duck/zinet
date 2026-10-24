#!/usr/bin/env python3
"""Freeze what the existing graph-algorithm copies do today, so zinet can replace them without changing behaviour.

Run by hand (it is not part of the test suite):

    python tests/characterization/generate.py            # rewrite golden/*.json and divergences.md
    python tests/characterization/generate.py --check    # exit 1 if the committed files are out of date

It builds the small graphs in `cases.py`, runs each source implementation on them, and records the results:

    graph_code      graph-code     src/graph_code/graph_lib.py       (works on a GraphDomain)
    conceptbook_v1  concept-book   spl/graph_lib.py                  (nx.DiGraph; `reducible` has a `strict` flag)
    conceptbook_v2  conceptbook-app spl/graph_lib.py                 (nx.DiGraph; older `reducible`, no `strict`)

Three more files freeze work-graph's comment-preserving YAML round-trip (`generate_roundtrip.py`), GraphLang's drawing
output (`generate_engines.py`) and work-graph's subgraph picker (`generate_select.py`). The sources are read, never modified. Sibling repos are looked up next to this one (override with
ZINET_SOURCES_DIR). The commit of each source is stored in the golden file, so a change in a source shows up
as a diff when this script is rerun.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import networkx as nx

HERE = Path(__file__).resolve().parent
SOURCES_DIR = Path(os.environ.get("ZINET_SOURCES_DIR", HERE.parents[2]))
GOLDEN = HERE / "golden"


def _commit(repo: str) -> str:
    out = subprocess.run(["git", "-C", str(SOURCES_DIR / repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


CASES = _load_module("zinet_characterization_cases", HERE / "cases.py").CASES


def _record(fn: Callable[[], Any]) -> Any:
    """The JSON-friendly result of a call, or {"raises": ExceptionName}. Sets become sorted lists."""
    try:
        return _plain(fn())
    except Exception as exc:  # noqa: BLE001: the point is to record whatever the source does
        return {"raises": type(exc).__name__}


def _plain(value: Any) -> Any:
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, tuple):
        return list(value)
    return value


# ---- graph-code ------------------------------------------------------------------------------------------------

def run_graph_code(case: dict) -> dict:
    sys.path.insert(0, str(SOURCES_DIR / "graph-code" / "src"))
    from graph_code import graph_lib as gl
    from graph_code.loader import _build_graph_domain

    nodes = {}
    for n in case["nodes"]:
        entry = {"composed_of": list(n["deps"])}
        if n.get("optional"):
            entry["optionally_depends_on"] = list(n["optional"])
        nodes[n["id"]] = entry
    domain = _build_graph_domain({
        "form": {"primitives": {p: {} for p in case["primitives"]}, "nodes": nodes},
        "first_radical_primitives": case.get("first_radical", []),
    })
    out: dict[str, Any] = {
        "acyclic": _record(lambda: (gl.acyclic(domain), "ok")[1]),
        "reducible": _record(lambda: gl.reducible(domain)),
        "reducible_first_radical_only": _record(lambda: gl.reducible(domain, first_radical_only=True)),
        "productivity_order_w1": _record(lambda: gl.productivity_order(domain, 1.0)),
        "productivity_order_w2": _record(lambda: gl.productivity_order(domain, 2.0)),
        "build_order": _record(lambda: gl.build_order(domain)),
    }
    for i, q in enumerate(case["queries"]):
        out[f"learning_path_{i}"] = _record(lambda q=q: gl.learning_path(domain, q["known"], q["target"]))
        out[f"gap_{i}"] = _record(lambda q=q: gl.gap(domain, q["known"], q["target"]))
    return out


# ---- conceptbook -----------------------------------------------------------------------------------------------

def conceptbook_graph(case: dict) -> nx.DiGraph:
    """The nx.DiGraph the ConceptBook functions expect: dependency -> dependent, `kind` on declared nodes only."""
    G = nx.DiGraph()
    for p in case["primitives"]:
        G.add_node(p, kind="primitive")
    for n in case["nodes"]:
        G.add_node(n["id"], kind=n.get("kind", "concept"))
    for n in case["nodes"]:
        for dep in n["deps"]:
            G.add_edge(dep, n["id"])           # an undeclared dep becomes a node without `kind`, as in the sources
    return G


def run_conceptbook(case: dict, gl, has_strict: bool) -> dict:
    G = conceptbook_graph(case)
    prims = list(case["primitives"]) + list(case.get("listed_only", []))
    out: dict[str, Any] = {
        "acyclic": _record(lambda: gl.acyclic(G)),
        "reducible": _record(lambda: gl.reducible(G, prims)),
        "productivity_order_w1": _record(lambda: gl.productivity_order(G, 1.0)),
        "productivity_order_w2": _record(lambda: gl.productivity_order(G, 2.0)),
        "applications_of": {n: _record(lambda n=n: gl.applications_of(G, n)) for n in sorted(G.nodes)},
    }
    if has_strict:
        out["reducible_strict"] = _record(lambda: gl.reducible(G, prims, strict=True))
    for i, q in enumerate(case["queries"]):
        out[f"ancestors_{i}"] = _record(lambda q=q: gl.ancestors(G, q["target"]))
        out[f"gap_{i}"] = _record(lambda q=q: gl.gap(G, q["target"], q["known"]))
        out[f"learning_path_{i}"] = _record(lambda q=q: gl.learning_path(G, q["target"], q["known"]))
    return out


# ---- driver ----------------------------------------------------------------------------------------------------

def generate() -> dict[str, dict]:
    v1 = _load_module("cb_v1_graph_lib", SOURCES_DIR / "concept-book" / "spl" / "graph_lib.py")
    v2 = _load_module("cb_v2_graph_lib", SOURCES_DIR / "conceptbook-app" / "spl" / "graph_lib.py")
    result = {
        "graph_code": {"_source": f"graph-code@{_commit('graph-code')}", "cases": {}},
        "conceptbook_v1": {"_source": f"concept-book@{_commit('concept-book')}", "cases": {}},
        "conceptbook_v2": {"_source": f"conceptbook-app@{_commit('conceptbook-app')}", "cases": {}},
    }
    for case in CASES:
        name = case["name"]
        if "graph_code" in case.get("sources", ("graph_code", "conceptbook")):
            result["graph_code"]["cases"][name] = run_graph_code(case)
        if "conceptbook" in case.get("sources", ("graph_code", "conceptbook")):
            result["conceptbook_v1"]["cases"][name] = run_conceptbook(case, v1, has_strict=True)
            result["conceptbook_v2"]["cases"][name] = run_conceptbook(case, v2, has_strict=False)
    return result


# Functions with the same meaning in more than one source, for the divergence report.
COMPARABLE = ["acyclic", "reducible", "productivity_order_w1", "productivity_order_w2", "learning_path", "gap"]


def divergences(result: dict[str, dict]) -> str:
    lines = [
        "# Where the existing copies disagree",
        "",
        "Generated by `generate.py`; do not edit by hand. Each row is a case and function where the sources",
        "give different answers on the same graph. These are the places where zinet has to choose a behaviour,",
        "or offer a parameter, instead of silently picking one.",
        "",
        "Sources: " + ", ".join(f"`{k}` = {v['_source']}" for k, v in result.items()),
        "",
        "## Root causes",
        "",
        "Most rows below come from a few differences in meaning, not from many separate bugs:",
        "",
        "1. **Primitives.** graph-code treats primitives as already known: `learning_path`, `gap` and `productivity_order` leave them out.",
        "   ConceptBook keeps them (they are nodes of the graph), so its lists start with the primitives.",
        "2. **What `gap` returns.** graph-code: the ordered path to the target, *including* the target. ConceptBook: the set of",
        "   ancestors still unknown, *excluding* the target. The two also order differently (graph-code `learning_path` is a",
        "   plain topological order of the needed nodes; ConceptBook orders by reach).",
        "3. **`reducible` is three rules.** graph-code: every node needs at least one primitive ancestor, so a declared foundation",
        "   concept or an isolated concept fails, and an undeclared (dangling) dependency is not noticed. ConceptBook v1 and v2:",
        "   every root must be declared (a primitive, or a concept with its own entry), so foundation concepts pass and a dangling",
        "   reference fails. v1 adds `strict` (every root must be a named primitive). v1 and v2 differ only when a name is passed as a",
        "   primitive but the graph has no entry for it (case `listed_primitive`): v1 rejects it, v2 accepts it.",
        "4. **Failure modes.** A missing target raises `ToolFailed` in graph-code and a bare `NetworkXError` in ConceptBook. A cycle",
        "   raises `NetworkXUnfeasible` in graph-code's `learning_path` but gives a silent partial result in ConceptBook's",
        "   `productivity_order`. Both `acyclic` functions agree (graph-code raises, ConceptBook returns False).",
        "5. **Tie order** agrees on the cases here: both break ties by reach and then by id (see `ties_unsorted`), apart from the",
        "   primitives in the list. graph-code's `build_order` uses `nx.topological_sort` (insertion order), which is not alphabetical.",
        "",
        "## Rows",
        "",
        "| Case | Function | graph_code | conceptbook_v1 | conceptbook_v2 |",
        "|---|---|---|---|---|",
    ]
    count = 0
    for case in CASES:
        name = case["name"]
        per = {k: v["cases"].get(name) for k, v in result.items()}
        if not all(per.values()):
            continue
        keys = sorted({k for p in per.values() for k in p})
        for key in keys:
            base = key.rsplit("_", 1)[0] if key.rsplit("_", 1)[-1].isdigit() else key
            if base not in COMPARABLE and key not in COMPARABLE:
                continue
            vals = {s: per[s].get(key, "n/a") for s in per}
            comparable = {json.dumps(_norm(key, v), sort_keys=True) for v in vals.values() if v != "n/a"}
            if len(comparable) > 1:
                count += 1
                cells = " | ".join(f"`{json.dumps(vals[s])}`" for s in per)
                lines.append(f"| {name} | {key} | {cells} |")
    lines += ["", f"{count} differing result(s) over {len(CASES)} cases.", ""]
    return "\n".join(lines)


def _norm(key: str, value: Any) -> Any:
    """Make results of the same function comparable across sources."""
    if key == "acyclic":
        if isinstance(value, dict) and "raises" in value:
            return False
        return True if value in ("ok", True) else value
    return value


def main() -> int:
    sys.path.insert(0, str(HERE))
    import generate_engines
    import generate_roundtrip
    import generate_select

    result = generate()
    files = {GOLDEN / f"{k}.json": json.dumps(v, indent=1, sort_keys=True) + "\n" for k, v in result.items()}
    files[HERE / "divergences.md"] = divergences(result)
    files[HERE / "cases.json"] = json.dumps(CASES, indent=1) + "\n"
    files.update(generate_roundtrip.build(SOURCES_DIR, HERE))
    files.update(generate_engines.build(SOURCES_DIR, HERE))
    files.update(generate_select.build(SOURCES_DIR, HERE))
    if "--check" in sys.argv:
        stale = [p.name for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            print("out of date:", ", ".join(stale))
            return 1
        print("characterization files are up to date")
        return 0
    GOLDEN.mkdir(exist_ok=True)
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    print(f"wrote {len(files)} files; see divergences.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
