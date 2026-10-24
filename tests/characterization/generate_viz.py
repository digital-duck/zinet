"""Characterize work-graph's interactive page (viz.cytoscape_html): node and edge data, sizes, marks and the legend.

Positions do not exist on this page (it uses a force layout), so everything that matters is in the data frozen here.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from generate_select import graph

CASES = {
    "default": {"select": {}, "mark": [], "title": "workgraph"},
    "marked_neighbourhood": {"select": {"node": "repo:a.py", "hops": 1, "include_code": True}, "mark": ["repo:a.py"], "title": "around a.py"},
    "everything": {"select": {"include_code": True, "hubs": True}, "mark": [], "title": "workgraph"},
}


def build(sources_dir: Path, here: Path) -> dict[Path, str]:
    sys.path.insert(0, str(sources_dir / "work-graph" / "src"))
    from workgraph import viz

    M = graph()
    out: dict[str, Any] = {}
    for name, case in CASES.items():
        sub, note = viz.select(M, **case["select"])
        page = viz.cytoscape_html(sub, note, mark=set(case["mark"]), title=case["title"])
        data = json.loads(re.search(r"const data = (\[.*?\]);\nconst dark", page, re.S).group(1).replace("<\\/", "</"))
        legend = re.findall(r'<span class="sw" style="background:(#[0-9a-f]{6})"></span>([^<]*)', page)
        out[name] = {"case": case, "note": note, "legend": [[label, color] for color, label in legend],
                     "graph": {"nodes": [[n, dict(d)] for n, d in sub.nodes(data=True)],
                               "edges": [[u, v, dict(d)] for u, v, d in sub.edges(data=True)]},
                     "elements": data}
    commit = subprocess.run(["git", "-C", str(sources_dir / "work-graph"), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip() or "unknown"
    return {here / "golden" / "workgraph_viz.json": json.dumps({"_source": f"work-graph@{commit}", "cases": out}, indent=1, sort_keys=True) + "\n"}
