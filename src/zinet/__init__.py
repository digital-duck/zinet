"""zinet: the shared graph.yaml intermediate representation.

Primitives -> concepts -> applications, with typed dependency edges, a structural
validator, and graph transforms reused by every ZiNets back-end (spl3, mg, cba, gfc, solver).
"""

from .algorithms import (
    applications_of,
    build_order,
    ensure_acyclic,
    gap,
    is_acyclic,
    learning_path,
    mandatory_subgraph,
    productivity_order,
    reducible,
    restrict,
    to_networkx,
)
from .dag import CycleError, UnknownNodeError, ancestors, topological_order
from .io import dump_graph, load_graph, to_yaml
from .render import render, to_dot, to_mermaid
from .schema import EdgeType, Graph, Layer, Node
from .transforms import GraphDiff, diff_graphs, slice_to
from .validator import Issue, validate

__version__ = "0.2.0"

__all__ = [
    "CycleError",
    "EdgeType",
    "Graph",
    "GraphDiff",
    "Issue",
    "Layer",
    "Node",
    "UnknownNodeError",
    "ancestors",
    "applications_of",
    "build_order",
    "diff_graphs",
    "dump_graph",
    "ensure_acyclic",
    "gap",
    "is_acyclic",
    "learning_path",
    "load_graph",
    "mandatory_subgraph",
    "productivity_order",
    "reducible",
    "render",
    "restrict",
    "slice_to",
    "to_dot",
    "to_mermaid",
    "to_networkx",
    "to_yaml",
    "topological_order",
    "validate",
]
