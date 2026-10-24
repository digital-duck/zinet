"""Characterize work-graph's viz.select (pick a readable subgraph: filters, neighbourhood, hub edges, node cap)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import networkx as nx


def graph() -> nx.MultiDiGraph:
    """The graph work-graph's own tests use, plus a second node labelled like another to test ambiguity."""
    M = nx.MultiDiGraph()
    M.add_node("project:p", label="p", kind="project", layer="repo")
    M.add_node("repo:a.py", label="a.py", kind="file", layer="repo", project="p")
    M.add_node("repo:b.py", label="b.py", kind="file", layer="repo", project="p")
    M.add_node("repo:c.py", label="c.py", kind="file", layer="repo", project="q", stages=["design"])
    M.add_node("repo:dup1", label="dup", kind="file", layer="repo", project="p")
    M.add_node("repo:dup2", label="dup", kind="file", layer="repo", project="p")
    M.add_node("sym", label="sym", kind="symbol", layer="repo", project="p")
    M.add_node("product:x", label="X", kind="product", layer="product")
    M.add_edge("repo:a.py", "repo:b.py", relation="imports", confidence="EXTRACTED")
    M.add_edge("repo:b.py", "repo:c.py", relation="imports", confidence="INFERRED")
    M.add_edge("repo:a.py", "project:p", relation="belongs_to", confidence="EXTRACTED")
    M.add_edge("repo:a.py", "sym", relation="contains", confidence="EXTRACTED")
    M.add_edge("product:x", "repo:a.py", relation="part_of", confidence="EXTRACTED")
    M.add_edge("repo:dup1", "repo:dup2", relation="imports", confidence="EXTRACTED")
    return M


CALLS = {
    "default": {},
    "everything": {"include_code": True, "hubs": True},
    "layer_product": {"layer": "product"},
    "project_q": {"project": "q"},
    "kind_file": {"kind": "file"},
    "stage_design": {"stage": "design"},
    "node_by_label_1hop": {"node": "a.py", "hops": 1},
    "node_by_id_2hops": {"node": "repo:a.py", "hops": 2},
    "node_with_code": {"node": "repo:a.py", "hops": 1, "include_code": True},
    "capped": {"max_nodes": 2},
    "unknown_node": {"node": "nope"},
    "ambiguous_label": {"node": "dup"},
}


def build(sources_dir: Path, here: Path) -> dict[Path, str]:
    sys.path.insert(0, str(sources_dir / "work-graph" / "src"))
    from workgraph import viz

    M = graph()
    out: dict[str, Any] = {}
    for name, kwargs in CALLS.items():
        try:
            sub, note = viz.select(M, **kwargs)
            out[name] = {"nodes": sorted(sub.nodes),
                         "edges": sorted([u, v, d.get("relation")] for u, v, d in sub.edges(data=True)),
                         "note": note}
        except ValueError as exc:
            out[name] = {"raises": "ValueError", "message": str(exc)}
    commit = subprocess.run(["git", "-C", str(sources_dir / "work-graph"), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip() or "unknown"
    doc = {"_source": f"work-graph@{commit}", "calls": CALLS,
           "graph": {"nodes": [[n, dict(d)] for n, d in M.nodes(data=True)],
                     "edges": [[u, v, dict(d)] for u, v, d in M.edges(data=True)]},
           "cases": out}
    return {here / "golden" / "workgraph_select.json": json.dumps(doc, indent=1, sort_keys=True) + "\n"}
