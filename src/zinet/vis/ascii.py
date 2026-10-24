"""A plain-text outline, readable in any terminal and easy to diff: nodes grouped by depth, each with what it depends on."""
from __future__ import annotations

from pathlib import Path

import networkx as nx

from .style import Style


def to_ascii_text(G: nx.Graph, style: Style) -> str:
    """Tier 0 holds the nodes with no dependencies, tier N the nodes whose longest chain of dependencies has N links.
    A graph with a cycle has no tiers, so it is listed as one block."""
    tiers: dict[int, list[str]] = {}
    if nx.is_directed_acyclic_graph(G):
        for generation, nodes in enumerate(nx.topological_generations(G)):
            tiers[generation] = sorted(nodes)
    else:
        tiers[0] = sorted(G)
    width = max([len(str(style.kind(n, d) or "?")) for n, d in G.nodes(data=True)] or [1])
    lines: list[str] = []
    for tier in sorted(tiers):
        lines.append(f"Tier {tier}" if len(tiers) > 1 or nx.is_directed_acyclic_graph(G) else "Nodes (the graph has a cycle)")
        for n in tiers[tier]:
            d = G.nodes[n]
            deps = sorted(style.label(p, G.nodes[p]) for p in G.predecessors(n))
            arrow = f"  <- {', '.join(deps)}" if deps else ""
            lines.append(f"  [{str(style.kind(n, d) or '?'):{width}}] {style.label(n, d)}{arrow}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def to_ascii(G: nx.Graph, out: Path, style: Style, note: str = "") -> None:
    out.write_text(to_ascii_text(G, style), encoding="utf-8")
