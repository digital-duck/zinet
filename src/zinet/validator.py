"""Structural checks that apply to any domain's graph.yaml, with no domain logic."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

import networkx as nx

from .dag import CycleError, topological_order
from .schema import Graph, Layer

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    message: str
    node: str | None = None

    def __str__(self) -> str:
        where = f" [{self.node}]" if self.node else ""
        return f"{self.severity}: {self.code}{where}: {self.message}"


OPTIONAL_CHECKS = ("reducible", "connected")


def validate(graph: Graph, *, checks: Iterable[str] = ()) -> list[Issue]:
    """Return all structural problems. Errors make a graph invalid; warnings are advisory.

    Errors: duplicate_id, unknown_dep, primitive_has_deps, layer_violation, cycle.
    Warnings: orphan (a node with no dependencies and no dependents).

    `checks` turns on more checks, which are off by default so that a graph that is valid today stays valid:

    - "reducible": every concept and application traces back to at least one primitive (error: not_reducible).
      Applies only when the graph has primitives and no cycle.
    - "connected": the graph is one piece when edges are read as undirected (warning: disconnected).
    """
    wanted = set(checks)
    if wanted - set(OPTIONAL_CHECKS):
        raise ValueError(f"unknown check(s) {sorted(wanted - set(OPTIONAL_CHECKS))}; choose from {list(OPTIONAL_CHECKS)}")
    issues: list[Issue] = []
    nodes = graph.nodes()

    for node_id, count in Counter(node.id for node in nodes).items():
        if count > 1:
            issues.append(Issue("error", "duplicate_id", f"id appears {count} times", node_id))

    layer_of: dict[str, Layer] = {}
    for layer, node in graph.layered_nodes():
        layer_of.setdefault(node.id, layer)

    for layer, node in graph.layered_nodes():
        if layer is Layer.PRIMITIVES and node.deps:
            issues.append(
                Issue("error", "primitive_has_deps", f"primitives are leaves but depend on {node.deps}", node.id)
            )
        for dep in node.deps:
            if dep not in layer_of:
                issues.append(Issue("error", "unknown_dep", f"depends on undefined id {dep!r}", node.id))
            elif layer_of[dep] is Layer.APPLICATIONS:
                issues.append(
                    Issue("error", "layer_violation", f"depends on application {dep!r}; applications are capstones", node.id)
                )

    known_deps = {node.id: [dep for dep in node.deps if dep in layer_of] for node in nodes}
    try:
        topological_order(known_deps)
    except CycleError as exc:
        issues.append(Issue("error", "cycle", str(exc)))

    referenced = {dep for node in nodes for dep in node.deps}
    if len(nodes) > 1:
        for node in nodes:
            if not node.deps and node.id not in referenced:
                issues.append(Issue("warning", "orphan", "not connected to any other node", node.id))

    if wanted:
        issues += _optional_issues(graph, wanted, has_cycle=any(i.code == "cycle" for i in issues))
    return issues


def _optional_issues(graph: Graph, wanted: set[str], has_cycle: bool) -> list[Issue]:
    layer_of = {node.id: layer for layer, node in graph.layered_nodes()}
    G = nx.DiGraph()
    G.add_nodes_from(layer_of)
    G.add_edges_from((dep, node.id) for node in graph.nodes() for dep in node.deps if dep in layer_of)
    issues: list[Issue] = []
    primitives = {n for n, layer in layer_of.items() if layer is Layer.PRIMITIVES}
    if "reducible" in wanted and primitives and not has_cycle:
        for node_id in [n for n in layer_of if n not in primitives]:
            if not nx.ancestors(G, node_id) & primitives:
                issues.append(Issue("error", "not_reducible", "does not trace back to any primitive", node_id))
    if "connected" in wanted and G.number_of_nodes() > 1:
        parts = sorted(sorted(c) for c in nx.weakly_connected_components(G))
        if len(parts) > 1:
            issues.append(Issue("warning", "disconnected", f"graph is in {len(parts)} separate pieces: " + "; ".join(", ".join(p) for p in parts)))
    return issues
