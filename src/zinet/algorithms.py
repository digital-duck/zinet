"""Graph algorithms over a plain `networkx.DiGraph`: order, reachability, learning paths, reducibility.

The input is a `DiGraph` whose edges point from a dependency to its dependent (so a topological order lists
dependencies first), and whose nodes may carry a `kind` attribute:

    "primitive"                 an irreducible leaf
    "concept", "application"    declared nodes (any other non-empty string counts as declared too)
    no `kind`                   a name that is only referenced, never declared (a dangling dependency)

`to_networkx(graph)` builds such a graph from a zinet `Graph`. Apps with their own graph (graph-code, ConceptBook)
pass theirs after mapping the `kind` attribute. The options on each function select the behaviour of the existing
copies of this code; `tests/characterization/` holds what each copy does, and `divergences.md` there says where they differ.
Defaults follow graph-code. Failures are always `UnknownNodeError` (missing node) or `CycleError` (cycle).
"""

from __future__ import annotations

import heapq
from collections.abc import Callable, Iterable
from typing import Literal

import networkx as nx

from .dag import CycleError, UnknownNodeError, _cycle_members
from .schema import Graph

PRIMITIVE = "primitive"
Order = Literal["topological", "alphabetical"]
ReducibleRule = Literal["primitive_ancestry", "declared", "declared_or_listed", "named_primitives"]

_KIND_OF_LAYER = {"primitives": "primitive", "concepts": "concept", "applications": "application"}


def to_networkx(graph: Graph) -> nx.DiGraph:
    """A zinet graph as a DiGraph: nodes carry `kind` (from the layer) and `label`, edges carry `edge_type`.

    A dependency on an id the graph does not define becomes a node without `kind`, as in the apps' own graphs.
    """
    G = nx.DiGraph()
    for layer, node in graph.layered_nodes():
        G.add_node(node.id, kind=_KIND_OF_LAYER[layer.value], label=node.label)
    for _, node in graph.layered_nodes():
        for dep in node.deps:
            edge_type = node.edge_types.get(dep)
            G.add_edge(dep, node.id, edge_type=edge_type.value if edge_type else "depends_on")
    return G


def mandatory_subgraph(G: nx.DiGraph, keep_edge: Callable[[str, str, dict], bool]) -> nx.DiGraph:
    """A copy of G with only the edges `keep_edge(u, v, data)` accepts (every node is kept).

    For graphs with optional edges (graph-code's `optionally_depends_on`), so the algorithms see mandatory edges only.
    """
    H = nx.DiGraph()
    H.add_nodes_from(G.nodes(data=True))
    H.add_edges_from((u, v, d) for u, v, d in G.edges(data=True) if keep_edge(u, v, d))
    return H


def _kind(G: nx.DiGraph, node: str) -> str | None:
    return G.nodes[node].get("kind")


def _primitives(G: nx.DiGraph, primitives: Iterable[str] | None) -> set[str]:
    return set(primitives) if primitives is not None else {n for n in G if _kind(G, n) == PRIMITIVE}


def _declared(G: nx.DiGraph) -> set[str]:
    """Nodes that were declared and are not primitives: the things an app builds, teaches or orders."""
    return {n for n in G if _kind(G, n) not in (None, PRIMITIVE)}


def _require(G: nx.DiGraph, node: str) -> None:
    if node not in G:
        raise UnknownNodeError(node)


def is_acyclic(G: nx.DiGraph) -> bool:
    return nx.is_directed_acyclic_graph(G)


def ensure_acyclic(G: nx.DiGraph) -> None:
    """Raise CycleError (with the nodes on a cycle) unless G is a DAG. Linear time, unlike enumerating every cycle."""
    if not nx.is_directed_acyclic_graph(G):
        raise CycleError(_cycle_members(G))


def _sorted(G: nx.DiGraph, nodes: set[str], order: Order) -> list[str]:
    """`nodes` in dependency order. "topological" is networkx's order (it follows insertion order, as graph-code does);
    "alphabetical" breaks ties by id, like `zinet.topological_order`."""
    sub = G.subgraph(nodes)
    try:
        if order == "alphabetical":
            return list(nx.lexicographical_topological_sort(sub))
        return list(nx.topological_sort(sub))
    except nx.NetworkXUnfeasible:
        raise CycleError(_cycle_members(sub)) from None


def restrict(G: nx.DiGraph, nodes: Iterable[str]) -> nx.DiGraph:
    """The subgraph induced by `nodes`, as an independent copy."""
    return G.subgraph(set(nodes)).copy()


def applications_of(G: nx.DiGraph, target: str) -> list[str]:
    """Applications that directly depend on `target`."""
    _require(G, target)
    return [n for n in G.successors(target) if _kind(G, n) == "application"]


def build_order(G: nx.DiGraph, *, include_primitives: bool = False, order: Order = "topological") -> list[str]:
    """Every declared node, dependencies first. Primitives and undeclared names are left out unless `include_primitives`."""
    ordered = _sorted(G, set(G), order)
    return ordered if include_primitives else [n for n in ordered if n in _declared(G)]


def learning_path(
    G: nx.DiGraph,
    target: str,
    known: Iterable[str] = (),
    *,
    primitives: Iterable[str] | None = None,
    include_primitives: bool = False,
    include_target: bool = True,
    order: Literal["topological", "alphabetical", "reach"] = "topological",
    weight: float = 1.0,
) -> list[str]:
    """What still has to be learned (or built) to reach `target`, in an order that respects dependencies.

    `known` and, unless `include_primitives`, the primitives are taken as already available.
    `include_target=False` stops short of the target itself. `order="reach"` puts the nodes that unlock the most others
    first (see `productivity_order`, to which `weight` applies); the other orders are those of `build_order`.
    Defaults reproduce graph-code. ConceptBook's version is `include_primitives=True, include_target=False, order="reach"`.
    """
    _require(G, target)
    known_set = set(known)
    prims = _primitives(G, primitives)
    needed = set(nx.ancestors(G, target)) | ({target} if include_target else set())
    needed -= known_set
    if not include_primitives:
        needed -= prims
    if not needed:
        return []
    if order == "reach":
        return productivity_order(restrict(G, needed), weight, include_primitives=True, weighted_applications=True,
                                  seed_by_reach=True)
    return _sorted_within(G, needed, known_set | prims, order)


def _sorted_within(G: nx.DiGraph, needed: set[str], context: set[str], order: Order) -> list[str]:
    """`needed` in dependency order, computed on `needed` plus the already-known context that links them."""
    nodes = {n for n in needed | context if n in G}
    return [n for n in _sorted(G, nodes, order) if n in needed]


def gap(
    G: nx.DiGraph,
    target: str,
    known: Iterable[str] = (),
    *,
    primitives: Iterable[str] | None = None,
    include_primitives: bool = False,
    include_target: bool = True,
    order: Literal["topological", "alphabetical"] = "topological",
) -> list[str]:
    """The nodes on the way to `target` that are not in `known`: `learning_path` without the nodes already known.

    Same options and defaults as `learning_path`. ConceptBook's version is `include_primitives=True, include_target=False`
    (its result is a set; compare sorted).
    """
    known_set = set(known)
    path = learning_path(G, target, known_set, primitives=primitives, include_primitives=include_primitives,
                         include_target=include_target, order=order)
    return [n for n in path if n not in known_set]


def productivity_order(
    G: nx.DiGraph,
    weight: float = 1.0,
    *,
    include_primitives: bool = False,
    weighted_applications: bool = False,
    seed_by_reach: bool = False,
) -> list[str]:
    """Dependency order that puts the nodes unlocking the most others as early as the dependencies allow.

    Kahn's algorithm with a heap: among nodes that are ready, the one with the highest reach goes first, then the lowest id.
    reach(n) counts n's descendants. Options, by the copy they reproduce:

    - graph-code (default): every declared descendant counts once, scaled by `weight`; the first nodes are taken in id order;
      primitives and undeclared names are left out of the result unless `include_primitives`.
    - ConceptBook: `weighted_applications=True` counts concept descendants once and application descendants `weight` times;
      `seed_by_reach=True` orders the first nodes by reach too; `include_primitives=True` keeps every node.
    """
    declared = _declared(G)
    reach: dict[str, float] = {}
    for n in G:
        desc = nx.descendants(G, n)
        if weighted_applications:
            concepts = sum(1 for d in desc if _kind(G, d) == "concept")
            apps = sum(1 for d in desc if _kind(G, d) == "application")
            reach[n] = concepts + weight * apps
        else:
            reach[n] = len(desc & declared) * weight
    in_degree = dict(G.in_degree())
    heap: list[tuple[float, str]] = [((-reach[n] if seed_by_reach else 0.0), n) for n in G if in_degree[n] == 0]
    heapq.heapify(heap)
    emitted: list[str] = []
    while heap:
        _, node = heapq.heappop(heap)
        emitted.append(node)
        for succ in G.successors(node):
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                heapq.heappush(heap, (-reach[succ], succ))
    if len(emitted) != G.number_of_nodes():
        raise CycleError(_cycle_members(G))
    return emitted if include_primitives else [n for n in emitted if n in declared]


def reducible(
    G: nx.DiGraph,
    primitives: Iterable[str] | None = None,
    *,
    rule: ReducibleRule = "primitive_ancestry",
    roots: Iterable[str] | None = None,
) -> bool:
    """Does everything reduce to the primitives? There are four rules, because the existing copies use different ones:

    - "primitive_ancestry" (graph-code, default): every declared node has at least one primitive ancestor, and all its
      primitive ancestors are in `roots` (default: all primitives; graph-code's two-radical check passes the first radical).
    - "declared" (ConceptBook): every root (a node with no dependencies) above a node is declared, i.e. has a `kind`.
      A concept with no dependencies that was given its own entry is accepted; a name that is only referenced is not.
    - "declared_or_listed" (older ConceptBook): as "declared", but a root named in `primitives` is also accepted.
    - "named_primitives" (ConceptBook `strict`): every root must be named in `primitives`.

    `primitives` defaults to the nodes whose `kind` is "primitive".
    """
    prims = _primitives(G, primitives)
    if rule == "primitive_ancestry":
        allowed = set(roots) if roots is not None else prims
        for node in _declared(G):
            found = nx.ancestors(G, node) & prims
            if not found or not found <= allowed:
                return False
        return True
    for node in G:
        if _kind(G, node) == PRIMITIVE:
            continue
        sources = {n for n in nx.ancestors(G, node) if G.in_degree(n) == 0}
        if rule == "named_primitives":
            if not sources <= prims:
                return False
        elif rule == "declared_or_listed":
            if any(n not in prims and _kind(G, n) is None for n in sources):
                return False
        elif rule == "declared":
            if any(_kind(G, n) is None for n in sources):
                return False
        else:
            raise ValueError(f"unknown reducible rule: {rule!r}")
    return True
