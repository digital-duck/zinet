"""How a graph looks: a `Style` is a set of small functions that read a node's or edge's attributes.

The engines never look at attribute names themselves, so work-graph (colour by `layer`, dashed `INFERRED` edges),
GraphLang (colour by node type, dashed data edges, a LOOP drawn as a box) and zinet's own layers each plug in a style
instead of renaming attributes. `zinet_style()` is the default: it reads what `zinet.to_networkx` writes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

# Shapes every engine understands (the names are Cytoscape's).
SHAPES = ("rectangle", "round-rectangle", "diamond", "hexagon", "ellipse")
OTHER_COLOR = "#8a8f98"

NodeFn = Callable[[str, dict], Any]
EdgeFn = Callable[[str, str, dict], Any]
SizeFn = Callable[[Any, str, dict], int]          # (graph, node id, attributes) -> diameter in pixels

# zinet's layers
LAYER_COLORS = {"primitive": "#2fa84f", "concept": "#4f8ef7", "application": "#e0a21e"}
LAYER_SHAPES = {"primitive": "ellipse", "concept": "rectangle", "application": "round-rectangle"}


@dataclass
class Style:
    """Functions with the signature (node id, node attributes) for nodes and (source, target, edge attributes) for edges."""

    label: NodeFn = lambda n, d: str(d.get("label") or n)
    kind: NodeFn = lambda n, d: d.get("kind")                 # shown under the label, and used for the legend
    color: NodeFn = lambda n, d: d.get("color") or OTHER_COLOR
    shape: NodeFn = lambda n, d: "rectangle"
    group: NodeFn = lambda n, d: d.get("parent")              # id of the box this node is drawn inside, or None
    info: NodeFn = lambda n, d: str(d.get("info") or "")      # text of the click panel
    edge_label: EdgeFn = lambda u, v, d: str(d.get("label") or "")
    edge_kind: EdgeFn = lambda u, v, d: str(d.get("relation") or d.get("edge_type") or "")
    edge_dashed: EdgeFn = lambda u, v, d: False
    edge_info: EdgeFn = lambda u, v, d: ""
    edge_legend: tuple[tuple[str, bool], ...] = ()            # e.g. (("control", False), ("data", True))
    title: str = "graph"
    kind_colors: dict[str, str] = field(default_factory=dict)  # fixes the legend order and colours when given
    # How the picture is arranged. "flow" suits a pipeline or a dependency graph: labelled boxes in dependency order (laid out by
    # Graphviz when it is installed). "force" suits a big knowledge graph: circles pulled together by a force layout. With
    # `node_size` set, nodes are drawn as sized shapes with the label below them (bigger = more connected, for example).
    arrangement: Literal["flow", "force"] = "flow"
    node_size: SizeFn | None = None
    # The interactive page. `secondary_hidden`: dashed edges (the data wiring, the typed or inferred edges) start hidden behind a
    # checkbox, so the first view is the main flow; they always show for the node you hover or select. `groups_collapsed`: a group
    # (a LOOP) starts as one box; click it to expand, double-click an expanded group to collapse it.
    secondary_hidden: bool = False
    groups_collapsed: bool = False

    def legend(self, G) -> list[tuple[str, str]]:
        """(kind, colour) for every kind present, in kind order."""
        seen: dict[str, str] = {}
        for n, d in G.nodes(data=True):
            k = self.kind(n, d)
            if k and k not in seen:
                seen[k] = self.kind_colors.get(k) or self.color(n, d)
        return sorted(seen.items())


def zinet_style(title: str = "graph") -> Style:
    """The style for graphs from `zinet.to_networkx`: colour and shape by layer, `edge_type` on the edges."""
    return Style(
        color=lambda n, d: LAYER_COLORS.get(d.get("kind"), OTHER_COLOR),
        shape=lambda n, d: LAYER_SHAPES.get(d.get("kind"), "rectangle"),
        edge_dashed=lambda u, v, d: d.get("edge_type") not in (None, "depends_on"),
        edge_label=lambda u, v, d: "" if d.get("edge_type") in (None, "depends_on") else str(d["edge_type"]),
        edge_legend=(("dependency", False), ("typed", True)),
        title=title,
    )
