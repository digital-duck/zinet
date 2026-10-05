"""Structural checks that apply to any domain's graph.yaml, with no domain logic."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

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


def validate(graph: Graph) -> list[Issue]:
    """Return all structural problems. Errors make a graph invalid; warnings are advisory.

    Errors: duplicate_id, unknown_dep, primitive_has_deps, layer_violation, cycle.
    Warnings: orphan (a node with no dependencies and no dependents).
    """
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

    return issues
