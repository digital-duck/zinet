"""Pick a readable subgraph of a big graph: filters, a neighbourhood around one node, hidden kinds, hub edges, a node cap."""
from __future__ import annotations

from collections import deque
from collections.abc import Callable

import networkx as nx

DEFAULT_MAX_NODES = 400
NodePredicate = Callable[[str, dict], bool]
EdgePredicate = Callable[[nx.Graph, str, str, dict], bool]


def select(
    G: nx.MultiDiGraph | nx.DiGraph,
    *,
    keep: NodePredicate | None = None,
    hidden: NodePredicate | None = None,
    show_hidden: bool = False,
    drop_edge: EdgePredicate | None = None,
    node: str | None = None,
    hops: int = 2,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> tuple[nx.MultiDiGraph | nx.DiGraph, str]:
    """A readable subgraph of G and a one-line note on what was cut.

    - `keep(id, attrs)`: filter; nodes it rejects are dropped (the `node` itself always stays).
    - `hidden(id, attrs)`: nodes that are noise by default (symbols, rationale nodes); dropped unless `show_hidden`.
    - `drop_edge(graph, u, v, attrs)`: edges to drop, e.g. the edges from every file to a few hub nodes, which bury the real
      structure. Applied to the selection; `drop_edge=None` keeps every edge.
    - `node` (an id or an exact label) with `hops`: only the neighbourhood of that node, edges read as undirected.
    - `max_nodes`: past that, the best-connected nodes are kept.
    Isolated nodes are removed unless they are the `node` or the only one left. Raises ValueError for an unknown or ambiguous `node`.
    """
    notes: list[str] = []
    is_hidden = (lambda n, d: False) if (hidden is None or show_hidden) else hidden
    if node is not None:
        if node not in G:
            by_label = [n for n, d in G.nodes(data=True) if d.get("label") == node]
            if len(by_label) != 1:
                raise ValueError(f"no node {node!r}" if not by_label else f"{node!r} matches {len(by_label)} nodes; use the id")
            node = by_label[0]
        seen, queue = {node: 0}, deque([node])
        while queue:
            u = queue.popleft()
            if seen[u] >= hops:
                continue
            neighbours = set(G.successors(u)) | set(G.predecessors(u))
            for v in neighbours:
                if v not in seen and not is_hidden(v, G.nodes[v]):
                    seen[v] = seen[u] + 1
                    queue.append(v)
        pool = set(seen)
        notes.append(f"{hops} hop(s) around {G.nodes[node].get('label', node)}")
    else:
        pool = set(G.nodes)

    def ok(n: str) -> bool:
        if n == node:
            return True
        d = G.nodes[n]
        return not is_hidden(n, d) and (keep is None or keep(n, d))

    sub = G.subgraph({n for n in pool if ok(n)}).copy()
    if drop_edge is not None:
        if sub.is_multigraph():
            sub.remove_edges_from([(u, v, k) for u, v, k, d in sub.edges(keys=True, data=True) if drop_edge(sub, u, v, d)])
        else:
            sub.remove_edges_from([(u, v) for u, v, d in sub.edges(data=True) if drop_edge(sub, u, v, d)])
    if sub.number_of_nodes() > max_nodes:
        top = sorted(sub.nodes, key=lambda n: (n == node, sub.degree(n)), reverse=True)[:max_nodes]
        notes.append(f"showing the {max_nodes} best-connected of {sub.number_of_nodes()} nodes (raise --max-nodes, or filter)")
        sub = sub.subgraph(top).copy()
    sub.remove_nodes_from([n for n in list(sub) if sub.degree(n) == 0 and n != node and sub.number_of_nodes() > 1])
    return sub, "; ".join(notes)
