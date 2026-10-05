"""Visualization: graph.yaml -> Graphviz DOT, Mermaid, and (via `dot`) SVG / PNG / PDF.

Mermaid is pure text and needs nothing installed. SVG, PNG, and PDF shell out to the
Graphviz `dot` binary, which must be on PATH.
"""

from __future__ import annotations

import shutil
import subprocess

from .schema import EdgeType, Graph, Layer

FORMATS = ("svg", "png", "pdf", "mermaid")
BINARY_FORMATS = ("png", "pdf")
_GRAPHVIZ_FORMATS = ("svg", "png", "pdf")

_DOT_SHAPE = {
    Layer.PRIMITIVES: "ellipse",
    Layer.CONCEPTS: "box",
    Layer.APPLICATIONS: "doubleoctagon",
}


def _dot_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _mermaid_text(text: str) -> str:
    return text.replace('"', "#quot;")


def to_dot(graph: Graph) -> str:
    """Graphviz DOT source: one cluster per layer, edges point from dependency to dependent."""
    lines = [
        "digraph graph_ir {",
        "  rankdir=LR;",
        '  node [fontname="Helvetica"];',
    ]
    for layer in Layer:
        nodes = getattr(graph, layer.value)
        if not nodes:
            continue
        lines.append(f'  subgraph "cluster_{layer.value}" {{')
        lines.append(f'    label={_dot_quote(layer.value)}; style=rounded; color=gray;')
        for node in nodes:
            label = node.label or node.id
            lines.append(f"    {_dot_quote(node.id)} [label={_dot_quote(label)} shape={_DOT_SHAPE[layer]}];")
        lines.append("  }")

    for node in graph.nodes():
        for dep in node.deps:
            kind = node.edge_types.get(dep)
            attrs = f" [label={_dot_quote(kind.value)}]" if kind and kind is not EdgeType.DEPENDS_ON else ""
            lines.append(f"  {_dot_quote(dep)} -> {_dot_quote(node.id)}{attrs};")
    lines.append("}")
    return "\n".join(lines) + "\n"


_MERMAID_BRACKETS = {
    Layer.PRIMITIVES: ("([", "])"),
    Layer.CONCEPTS: ("[", "]"),
    Layer.APPLICATIONS: ("{{", "}}"),
}


def to_mermaid(graph: Graph) -> str:
    """Mermaid flowchart (LR), one subgraph per layer. Renders in GitHub and most Markdown viewers."""
    names: dict[str, str] = {}
    for index, (_, node) in enumerate(graph.layered_nodes()):
        names.setdefault(node.id, f"n{index}")

    lines = ["flowchart LR"]
    for layer in Layer:
        nodes = getattr(graph, layer.value)
        if not nodes:
            continue
        lines.append(f"  subgraph {layer.value}")
        open_, close = _MERMAID_BRACKETS[layer]
        for node in nodes:
            label = _mermaid_text(node.label or node.id)
            lines.append(f'    {names[node.id]}{open_}"{label}"{close}')
        lines.append("  end")

    for node in graph.nodes():
        for dep in node.deps:
            if dep not in names:  # dangling reference: declare it so the edge still draws
                names[dep] = f"n{len(names)}"
                lines.append(f'  {names[dep]}["{_mermaid_text(dep)}"]')
            kind = node.edge_types.get(dep)
            arrow = f"-->|{kind.value}|" if kind and kind is not EdgeType.DEPENDS_ON else "-->"
            lines.append(f"  {names[dep]} {arrow} {names[node.id]}")
    return "\n".join(lines) + "\n"


def render(graph: Graph, fmt: str) -> bytes:
    """Render `graph` in `fmt` and return the raw bytes (UTF-8 text for svg and mermaid)."""
    if fmt == "mermaid":
        return to_mermaid(graph).encode("utf-8")
    if fmt not in _GRAPHVIZ_FORMATS:
        raise ValueError(f"unknown format {fmt!r}; choose from {', '.join(FORMATS)}")
    return _run_dot(to_dot(graph), fmt)


def _run_dot(source: str, fmt: str) -> bytes:
    if shutil.which("dot") is None:
        raise RuntimeError("Graphviz 'dot' not found on PATH; install graphviz (e.g. apt install graphviz)")
    proc = subprocess.run(
        ["dot", f"-T{fmt}"],
        input=source.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dot failed: {proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout
