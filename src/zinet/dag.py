"""DAG algorithms over an id -> dependency-ids mapping, built on networkx.

Kept free of node types so any domain back-end can reuse them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import networkx as nx


class CycleError(ValueError):
    """Raised when a dependency cycle exists. `members` lists nodes stuck in or behind it."""

    def __init__(self, members: list[str]):
        self.members = members
        super().__init__(f"dependency cycle among: {', '.join(members)}")


def _dependency_graph(deps: Mapping[str, Iterable[str]]) -> nx.DiGraph:
    """Edges run dependency -> dependent, so a topological order lists dependencies first."""
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


def topological_order(deps: Mapping[str, Iterable[str]]) -> list[str]:
    """Return every id with its dependencies before it. Ties break alphabetically.

    Every dependency id must itself be a key of `deps`; callers filter unknown ids first.
    Raises CycleError when the mapping is not a DAG.
    """
    graph = _dependency_graph(deps)
    try:
        return list(nx.lexicographical_topological_sort(graph))
    except nx.NetworkXUnfeasible:
        raise CycleError(_cycle_members(graph)) from None


def ancestors(deps: Mapping[str, Iterable[str]], target: str) -> set[str]:
    """All ids `target` transitively depends on (excluding `target` itself)."""
    if target not in deps:
        raise KeyError(target)
    return set(nx.ancestors(_dependency_graph(deps), target))
