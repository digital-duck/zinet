"""Subgraph extraction."""

from __future__ import annotations

from ..dag import ancestors
from ..schema import Graph, Layer


def slice_to(graph: Graph, target: str) -> Graph:
    """Return the subgraph made of `target` and everything it transitively depends on.

    For a concept-graph this is the prerequisite closure of the target. Raises KeyError
    if `target` is not a node id.
    """
    index = graph.index()
    if target not in index:
        raise KeyError(f"unknown node: {target!r}")
    deps = {node_id: node.deps for node_id, (_, node) in index.items()}
    keep = ancestors(deps, target) | {target}
    return Graph(
        version=graph.version,
        **{
            layer.value: [node for node in getattr(graph, layer.value) if node.id in keep]
            for layer in Layer
        },
    )
