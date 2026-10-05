"""Semantic diff between two graphs, matched by node id."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..schema import Graph

_FIELDS = ("layer", "label", "deps", "edge_types", "meta")


@dataclass(frozen=True)
class GraphDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    # node id -> {field name: (old value, new value)}
    changed: dict[str, dict[str, tuple[Any, Any]]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)


def diff_graphs(old: Graph, new: Graph) -> GraphDiff:
    """Compare two graphs node by node. Dependency order is ignored; only the set matters."""
    before = _describe(old)
    after = _describe(new)
    changed: dict[str, dict[str, tuple[Any, Any]]] = {}
    for node_id in sorted(before.keys() & after.keys()):
        delta = {
            name: (before[node_id][name], after[node_id][name])
            for name in _FIELDS
            if before[node_id][name] != after[node_id][name]
        }
        if delta:
            changed[node_id] = delta
    return GraphDiff(
        added=sorted(after.keys() - before.keys()),
        removed=sorted(before.keys() - after.keys()),
        changed=changed,
    )


def _describe(graph: Graph) -> dict[str, dict[str, Any]]:
    return {
        node_id: {
            "layer": layer.value,
            "label": node.label,
            "deps": sorted(node.deps),
            "edge_types": {dep: kind.value for dep, kind in node.edge_types.items()},
            "meta": node.meta,
        }
        for node_id, (layer, node) in graph.index().items()
    }
