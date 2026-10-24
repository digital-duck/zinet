"""zinet.vis: draw and select from a `networkx` graph. Engines, `select`, and the `Style` that tells them how to read your attributes.

    from zinet.vis import render, select, zinet_style
    G = zinet.to_networkx(zinet.load_graph("graph.yaml"))
    render(G, "graph.html")                      # interactive page; engine="mermaid" | "graphviz" | "ascii" | ...

Apps with their own attribute names pass a `Style` (see `zinet.vis.style`).
"""

from .ascii import to_ascii_text
from .cytoscape import cytoscape_html, elements
from .dot import dot_positions, graphviz_ready, to_dot
from .engines import DEFAULT_ENGINE, ENGINES, render
from .extras import graphify_ready, pyvis_ready
from .mermaid import to_mermaid_text
from .select import DEFAULT_MAX_NODES, select
from .style import Style, zinet_style

__all__ = [
    "DEFAULT_ENGINE", "DEFAULT_MAX_NODES", "ENGINES", "Style",
    "cytoscape_html", "dot_positions", "elements", "graphify_ready", "graphviz_ready", "pyvis_ready",
    "render", "select", "to_ascii_text", "to_dot", "to_mermaid_text", "zinet_style",
]
