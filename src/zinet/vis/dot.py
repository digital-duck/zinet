"""Graphviz: DOT text, an SVG through the `dot` program, and node positions for the interactive page."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import networkx as nx

from .style import Style

DOT_SHAPES = {"round-rectangle": "box", "diamond": "diamond", "hexagon": "hexagon", "rectangle": "box", "ellipse": "ellipse"}
CONTROL_COLOR, DATA_COLOR = "#6b7280", "#4f8ef7"


def groups_of(G: nx.Graph, style: Style) -> dict[str, list[str]]:
    """group id -> member ids, for the nodes that have members (they are drawn as boxes)."""
    members: dict[str, list[str]] = {}
    for n, d in G.nodes(data=True):
        g = style.group(n, d)
        if g is not None:
            members.setdefault(g, []).append(n)
    return members


def graphviz_ready() -> tuple[bool, str]:
    return (True, "dot found") if shutil.which("dot") else (False, "dot not found (install graphviz); DOT text is written instead")


def to_dot(G: nx.Graph, style: Style, fixed_size: bool = False) -> str:
    """DOT text: a group becomes a cluster; the group's own node sits inside it as the anchor for outer edges.
    `fixed_size` gives every node the size it has on the interactive page, so positions computed here fit there."""
    esc = lambda s: str(s).replace("\\", "/").replace('"', "'")  # noqa: E731
    members = groups_of(G, style)

    def node_line(n: str, pad: str) -> str:
        d = G.nodes[n]
        shape = DOT_SHAPES[style.shape(n, d)]
        node_style = "rounded,filled" if shape == "box" else "filled"
        color = style.color(n, d)
        kind = style.kind(n, d)
        label = f'{esc(style.label(n, d))}\\n{kind}' if kind else esc(style.label(n, d))
        size = ""
        if fixed_size:
            w, h = (150, 70) if shape == "diamond" else (130, 48)
            size = f", fixedsize=true, width={w / 72:.3f}, height={h / 72:.3f}"
        return f'{pad}"{esc(n)}" [label="{label}", shape={shape}, style="{node_style}", fillcolor="{color}55", color="{color}"{size}];'

    def emit(parent, pad: str) -> list[str]:
        lines: list[str] = []
        for n in [n for n in G if style.group(n, G.nodes[n]) == parent]:
            if n in members:
                color = style.color(n, G.nodes[n])
                lines += [f'{pad}subgraph "cluster_{esc(n)}" {{',
                          f'{pad}  label="{esc(style.label(n, G.nodes[n]))}"; style="dashed,rounded"; color="{color}";',
                          node_line(n, pad + "  ")]
                lines += emit(n, pad + "  ")
                lines.append(f"{pad}}}")
            else:
                lines.append(node_line(n, pad))
        return lines

    lines = ["digraph G {", "  rankdir=LR; compound=true; fontsize=11;", '  node [fontsize=11, fontcolor="#222"];']
    lines += emit(None, "  ")
    for u, v, d in G.edges(data=True):
        dashed = style.edge_dashed(u, v, d)
        color = DATA_COLOR if dashed else CONTROL_COLOR
        attrs = [f'label="{esc(style.edge_label(u, v, d))}"', "fontsize=9", f'color="{color}"', f'fontcolor="{color}"']
        if dashed:
            attrs += ["style=dashed", "constraint=false"]
        lines.append(f'  "{esc(u)}" -> "{esc(v)}" [{", ".join(attrs)}];')
    return "\n".join(lines + ["}"])


def dot_positions(G: nx.Graph, style: Style, canvas_aspect: float = 1.6) -> dict[str, dict[str, float]]:
    """Node centres (cytoscape pixels, y down) from `dot -Tjson`; {} when `dot` is missing or fails.

    Lays the graph out left-to-right and top-to-bottom and keeps the one whose shape is closer to the page's (a long
    pipeline is unreadable as one very wide row). A group is a box on the page, so its own (anchor) position is left
    out and the box wraps its members."""
    if not shutil.which("dot"):
        return {}
    anchors = set(groups_of(G, style))
    best: dict[str, dict[str, float]] = {}
    best_score: float | None = None
    for rankdir in ("LR", "TB"):
        text = to_dot(G, style, fixed_size=True).replace("rankdir=LR;", f"rankdir={rankdir}; nodesep=0.5; ranksep=0.9;")
        r = subprocess.run(["dot", "-Tjson"], input=text, text=True, capture_output=True)
        if r.returncode:
            continue
        try:
            j = json.loads(r.stdout)
            _, _, w, h = (float(v) for v in j["bb"].split(","))
            pos = {o["name"]: {"x": float(o["pos"].split(",")[0]), "y": -float(o["pos"].split(",")[1])}
                   for o in j.get("objects", []) if o.get("name") in G and o["name"] not in anchors and "pos" in o}
        except (ValueError, KeyError):
            continue
        score = abs(math.log((w / max(h, 1.0)) / canvas_aspect))
        if best_score is None or score < best_score:
            best, best_score = pos, score
    return best


def to_graphviz(G: nx.Graph, out: Path, style: Style, note: str = "") -> None:
    """SVG through `dot`; without it, the DOT text is written next to `out` and a RuntimeError says so."""
    dot = to_dot(G, style)
    if shutil.which("dot"):
        r = subprocess.run(["dot", f"-T{out.suffix.lstrip('.') or 'svg'}", "-o", str(out)], input=dot, text=True, capture_output=True)
        if r.returncode:
            raise RuntimeError(f"dot failed: {r.stderr.strip()[:200]}")
    else:
        out.with_suffix(".dot").write_text(dot, encoding="utf-8")
        raise RuntimeError(f"dot is not installed; wrote DOT text to {out.with_suffix('.dot')}")
