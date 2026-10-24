"""DAG algorithms over an id -> dependency-ids mapping, or over a plain `networkx.DiGraph`.

Kept free of node types so any domain back-end can reuse them. A `DiGraph` must point from a dependency to its
dependent (the same direction as a zinet graph), so a topological order lists dependencies first.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import networkx as nx


class UnknownNodeError(KeyError):
    """Raised when an algorithm is asked about a node that is not in the graph. A KeyError, so older callers still work."""

    def __init__(self, node: str):
        self.node = node
        super().__init__(node)

    def __str__(self) -> str:
        return f"unknown node: {self.node!r}"


class CycleError(ValueError):
    """Raised when a dependency cycle exists. `members` lists nodes stuck in or behind it."""

    def __init__(self, members: list[str]):
        self.members = members
        super().__init__(f"dependency cycle among: {', '.join(members)}")


def _dependency_graph(deps: Mapping[str, Iterable[str]] | nx.DiGraph) -> nx.DiGraph:
    """Edges run dependency -> dependent, so a topological order lists dependencies first. A DiGraph is used as is."""
    if isinstance(deps, nx.DiGraph):
        return deps
    graph = nx.DiGraph()
    graph.add_nodes_from(deps)
    for node, parents in deps.items():
        graph.add_edges_from((parent, node) for parent in parents)
    return graph


def _cycle_members(graph: nx.DiGraph) -> list[str]:
    """Nodes that sit on a cycle: members of a multi-node strongly connected component, or self-loops."""
    members = {node for scc in nx.strongly_connected_components(graph) if len(scc) > 1 for node in scc}
    members |= {node for node in graph if graph.has_edge(node, node)}
    return sorted(members)


def topological_order(deps: Mapping[str, Iterable[str]] | nx.DiGraph) -> list[str]:
    """Return every id with its dependencies before it. Ties break alphabetically.

    `deps` is an id -> dependency-ids mapping or a `networkx.DiGraph` (dependency -> dependent edges). Every dependency
    id must itself be a key of the mapping; callers filter unknown ids first.
    Raises CycleError when the input is not a DAG.
    """
    graph = _dependency_graph(deps)
    try:
        return list(nx.lexicographical_topological_sort(graph))
    except nx.NetworkXUnfeasible:
        raise CycleError(_cycle_members(graph)) from None


def ancestors(deps: Mapping[str, Iterable[str]] | nx.DiGraph, target: str) -> set[str]:
    """All ids `target` transitively depends on (excluding `target` itself).

    Raises UnknownNodeError (a KeyError) when `target` is not in `deps`.
    """
    if target not in deps:
        raise UnknownNodeError(target)
    return set(nx.ancestors(_dependency_graph(deps), target))
