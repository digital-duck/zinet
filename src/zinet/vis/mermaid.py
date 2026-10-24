"""Mermaid flowchart text: pastes into GitHub, mkdocs or mermaid.live, and needs nothing installed."""
from __future__ import annotations

from pathlib import Path

import networkx as nx

from .dot import groups_of
from .style import Style

MERMAID_SHAPES = {"round-rectangle": ("([", "])"), "diamond": ("{", "}"), "hexagon": ("{{", "}}"),
                  "rectangle": ("[", "]"), "ellipse": ("((", "))")}


def to_mermaid_text(G: nx.Graph, style: Style) -> str:
    """A flowchart: a group is a `subgraph` (edges to the group point at the box); a dashed edge is `-.->`."""
    ids = {n: f"n{i}" for i, n in enumerate(G)}
    q = lambda s: str(s).replace('"', "#quot;")  # noqa: E731
    members = groups_of(G, style)
    lines = ["flowchart LR"]

    def emit(parent, pad: str) -> None:
        for n in [n for n in G if style.group(n, G.nodes[n]) == parent]:
            d = G.nodes[n]
            if n in members:
                lines.append(f'{pad}subgraph {ids[n]}["{q(style.label(n, d))} ({style.kind(n, d) or "group"})"]')
                emit(n, pad + "  ")
                lines.append(f"{pad}end")
            else:
                left, right = MERMAID_SHAPES[style.shape(n, d)]
                kind = style.kind(n, d)
                text = f"{q(style.label(n, d))}<br/>{kind}" if kind else q(style.label(n, d))
                lines.append(f'{pad}{ids[n]}{left}"{text}"{right}')

    emit(None, "  ")
    for u, v, d in G.edges(data=True):
        arrow = "-.->" if style.edge_dashed(u, v, d) else "-->"
        label = style.edge_label(u, v, d)
        lines.append(f'  {ids[u]} {arrow}{f"|{chr(34)}{q(label)}{chr(34)}|" if label else ""} {ids[v]}')
    by_kind: dict[str, list[str]] = {}
    colors: dict[str, str] = {}
    for n, d in G.nodes(data=True):
        kind = style.kind(n, d)
        if kind and n not in members:
            by_kind.setdefault(kind, []).append(ids[n])
            colors.setdefault(kind, style.kind_colors.get(kind) or style.color(n, d))
    for kind in sorted(by_kind):
        c = colors[kind]
        lines += [f"  classDef {kind} fill:{c}55,stroke:{c},color:#222;", f"  class {','.join(by_kind[kind])} {kind};"]
    return "\n".join(lines) + "\n"


def to_mermaid(G: nx.Graph, out: Path, style: Style, note: str = "") -> None:
    text = to_mermaid_text(G, style)
    out.write_text(f"```mermaid\n{text}```\n" if out.suffix == ".md" else text, encoding="utf-8")
