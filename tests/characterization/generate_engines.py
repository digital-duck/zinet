"""Characterize GraphLang's drawing code (graphlang/grafv) on its bundled example workflows.

What is frozen: the Mermaid text, the DOT text (with and without fixed node sizes), and the cytoscape elements
(ids, labels, colours, shapes, groups, edge relations and labels). Node positions are not frozen: they come from
Graphviz and change with its version.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def build(sources_dir: Path, here: Path) -> dict[Path, str]:
    from graphlang.grafr.runtime import load_graph
    from graphlang.grafv import engines
    from graphlang.grafv.model import build as build_model

    cookbook = sources_dir / "graflang" / "cookbook"
    graphs = {p.name.removesuffix(".graph.yaml"): p for p in sorted(cookbook.glob("*/*.graph.yaml"))}
    out: dict[str, Any] = {}
    for name, path in graphs.items():
        G, note = build_model(load_graph(path))
        page = engines.cytoscape_html(G, note)
        data = json.loads(re.search(r"const data = (\[.*?\]);\nconst dark", page, re.S).group(1).replace("<\\/", "</"))
        for el in data:
            el.pop("position", None)                           # layout-dependent
        out[name] = {
            "nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "note": note,
            # the input, so zinet's tests can rebuild the graph without GraphLang installed
            "graph": {"nodes": [[n, dict(d)] for n, d in G.nodes(data=True)],        # a list: order matters
                      "edges": [[u, v, dict(d)] for u, v, d in G.edges(data=True)]},
            "mermaid": engines.to_mermaid_text(G),
            "dot": engines.to_dot(G),
            "dot_fixed_size": engines.to_dot(G, fixed_size=True),
            "cytoscape_elements": data,
        }
    return {here / "golden" / "graphlang_engines.json": json.dumps({"_source": f"graflang@{_commit(sources_dir / 'graflang')}",
                                                                    "cases": out}, indent=1, sort_keys=True) + "\n"}


def _commit(repo: Path) -> str:
    import subprocess
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or "unknown"
