"""The engine registry and `render`.

Engines in the core install (nothing extra to install):
  cytoscape  one self-contained HTML file, works offline; node positions from Graphviz when `dot` is installed. Default.
  graphviz   an image through the `dot` program (svg, png or pdf by the file extension); DOT text if `dot` is missing.
  mermaid    Mermaid flowchart text (`.mmd`, or a fenced block when the file ends in `.md`).
  ascii      a plain-text outline by depth.
Optional:
  pyvis      interactive HTML via pyvis (`pip install zinet[pyvis]`).
  graphify   graphify's community-coloured HTML (`pip install zinet[graphify]`); undirected.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx

from .ascii import to_ascii
from .cytoscape import to_cytoscape
from .dot import graphviz_ready, to_graphviz
from .extras import graphify_ready, pyvis_ready, to_graphify, to_pyvis
from .mermaid import to_mermaid
from .style import Style, zinet_style

DEFAULT_ENGINE = "cytoscape"

ENGINES: dict[str, dict[str, Any]] = {
    "cytoscape": {"fn": to_cytoscape, "ext": ".html", "ready": lambda: (True, "bundled, works offline"),
                  "about": "interactive HTML (search, zoom, click a node for its details); no extra install"},
    "graphviz": {"fn": to_graphviz, "ext": ".svg", "ready": graphviz_ready, "about": "an image through `dot` (svg, png, pdf); good for docs"},
    "mermaid": {"fn": to_mermaid, "ext": ".mmd", "ready": lambda: (True, "plain text"), "open": False,
                "about": "Mermaid flowchart text for GitHub / docs / mermaid.live; -o FILE.md wraps it in a fenced block"},
    "ascii": {"fn": to_ascii, "ext": ".txt", "ready": lambda: (True, "plain text"), "open": False,
              "about": "a plain-text outline by depth, for a terminal or a diff"},
    "pyvis": {"fn": to_pyvis, "ext": ".html", "ready": pyvis_ready, "required": True,
              "about": "interactive HTML via pyvis, left to right (pip install 'zinet[pyvis]')"},
    "graphify": {"fn": to_graphify, "ext": ".html", "ready": graphify_ready, "required": True,
                 "about": "graphify's HTML export coloured by community; undirected (pip install 'zinet[graphify]')"},
}


def render(G: nx.Graph, out: str | Path, engine: str = DEFAULT_ENGINE, style: Style | None = None, note: str = "") -> Path:
    """Draw G with `engine` into `out` and return the path. Raises ValueError (unknown engine, empty graph) or RuntimeError
    (a missing optional package, or `dot` missing for the graphviz engine)."""
    if engine not in ENGINES:
        raise ValueError(f"unknown engine {engine!r}; choose from {sorted(ENGINES)}")
    if not G.number_of_nodes():
        raise ValueError("nothing to draw: the graph has no nodes")
    spec = ENGINES[engine]
    ok, why = spec["ready"]()
    if not ok and spec.get("required"):
        raise RuntimeError(why)
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    spec["fn"](G, target, style or zinet_style(), note)
    return target
