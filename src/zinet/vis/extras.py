"""Engines that need an optional package: pyvis (`pip install zinet[pyvis]`) and graphify (`pip install zinet[graphify]`)."""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from .dot import CONTROL_COLOR, DATA_COLOR
from .style import Style

_PYVIS_SHAPES = {"diamond": "diamond", "hexagon": "hexagon", "ellipse": "ellipse"}


def pyvis_ready() -> tuple[bool, str]:
    try:
        import pyvis  # noqa: F401
        return True, "pyvis installed"
    except ImportError:
        return False, "needs pyvis: pip install 'zinet[pyvis]'"


PYVIS_OPTIONS = json.dumps({
    "layout": {"hierarchical": {"enabled": True, "direction": "LR", "sortMethod": "directed", "levelSeparation": 200,
                                "nodeSpacing": 120}},
    "physics": {"enabled": False},
    "edges": {"smooth": {"type": "cubicBezier"}, "font": {"size": 11, "align": "middle"}},
})


def to_pyvis(G: nx.Graph, out: Path, style: Style, note: str = "") -> None:
    from pyvis.network import Network
    net = Network(height="100vh", width="100%", directed=True, notebook=False, cdn_resources="in_line")
    for n, d in G.nodes(data=True):
        group, kind = style.group(n, d), style.kind(n, d)
        color = style.color(n, d)
        label = f"{style.label(n, d)}\n{kind}" if kind else style.label(n, d)
        shape = style.shape(n, d)
        if style.node_size is not None:                # circles sized by the style, the label below (a force-layout graph)
            net.add_node(n, label=style.label(n, d), title=style.info(n, d), color=color,
                         size=style.node_size(G, n, d) / 2, shape="diamond" if shape == "diamond" else "dot")
            continue
        net.add_node(n, label=label, title=style.info(n, d) + (f"\nin: {group}" if group else ""),
                     color={"background": color, "border": color}, shape=_PYVIS_SHAPES.get(shape, "box"),
                     shapeProperties={"borderDashes": [5, 5]} if group else {})
    for u, v, d in G.edges(data=True):
        dashed = bool(style.edge_dashed(u, v, d))
        net.add_edge(u, v, label=style.edge_label(u, v, d), title=f"{style.edge_kind(u, v, d)} {style.edge_info(u, v, d)}".strip(),
                     arrows="to", dashes=dashed, color=DATA_COLOR if dashed else CONTROL_COLOR)
    if style.arrangement == "force":
        net.barnes_hut(spring_length=140)
    else:
        net.set_options(PYVIS_OPTIONS)
    net.write_html(str(out), notebook=False)


def graphify_ready() -> tuple[bool, str]:
    try:
        import graphify.export  # noqa: F401
        return True, "graphify installed"
    except ImportError:
        return False, "needs graphify: pip install 'zinet[graphify]'"


def to_graphify(G: nx.Graph, out: Path, style: Style, note: str = "") -> None:
    """graphify's community-coloured export. It is undirected, so it shows structure only (no edge kinds, no groups)."""
    from graphify.cluster import cluster
    from graphify.export import to_html
    U = nx.Graph()
    for n, d in G.nodes(data=True):
        U.add_node(n, label=style.label(n, d), kind=style.kind(n, d), source_file=style.info(n, d))
    for u, v, d in G.edges(data=True):
        U.add_edge(u, v, relation=style.edge_kind(u, v, d), confidence="INFERRED" if style.edge_dashed(u, v, d) else "EXTRACTED")
    communities = cluster(U) if U.number_of_nodes() else {}
    if not to_html(U, communities, str(out)):
        raise RuntimeError("graphify declined to export this graph")
