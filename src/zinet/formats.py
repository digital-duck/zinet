"""Which kind of graph YAML is this? Several tools write a `graph.yaml` or `*.graph.yaml`, and the file name never decides.

  zinet graph          `primitives:` / `concepts:` / `applications:` as lists of nodes with `deps`
  ConceptBook graph    the same three layers as mappings keyed by id, with `composed_of` / `needs` (ConceptBook, graph-code)
  GraphLang workflow   `workflow:` with `nodes:` and `edges:` (typed nodes with ports; run by the `graf` command)

`load_graph` uses `explain_foreign` to say what a file is when it is not a zinet graph, instead of a schema error.
"""
from __future__ import annotations

from typing import Any

ZINET, CONCEPTBOOK, GRAPHLANG, UNKNOWN = "zinet", "conceptbook", "graphlang", "unknown"
LAYERS = ("primitives", "concepts", "applications")


def detect(data: Any) -> str:
    """'zinet', 'conceptbook', 'graphlang' or 'unknown' for an already-parsed YAML document."""
    if not isinstance(data, dict):
        return UNKNOWN
    if "workflow" in data or ("nodes" in data and "edges" in data) or str(data.get("version", "")).endswith("-graph"):
        return GRAPHLANG
    layers = [data[k] for k in LAYERS if k in data]
    if layers:
        return CONCEPTBOOK if any(isinstance(v, dict) for v in layers) else ZINET
    return UNKNOWN


def explain_foreign(data: Any) -> str | None:
    """A sentence saying what the document is and what to use instead, or None if it looks like a zinet graph (or nothing known)."""
    kind = detect(data)
    if kind == GRAPHLANG:
        return ("this is a GraphLang workflow (workflow:, nodes:, edges:), not a zinet graph. "
                "Check, draw or run it with `graf validate|vis|run FILE`.")
    if kind == CONCEPTBOOK:
        layers = ", ".join(k for k in LAYERS if k in data)
        return (f"this is a ConceptBook / graph-code graph ({layers} written as mappings with composed_of / needs), "
                "which zinet cannot read yet: zinet expects each layer as a list of nodes with `deps`. "
                "Check it with `grafcode validate FILE` or the ConceptBook tools.")
    return None
