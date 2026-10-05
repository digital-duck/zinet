"""graph-ir: the shared graph.yaml intermediate representation.

Primitives -> concepts -> applications, with typed dependency edges, a structural
validator, and graph transforms reused by every ZiNets back-end (spl3, mg, cba, gfc, solver).
"""

from .dag import CycleError, ancestors, topological_order
from .io import dump_graph, load_graph, to_yaml
from .render import render, to_dot, to_mermaid
from .schema import EdgeType, Graph, Layer, Node
from .transforms import GraphDiff, diff_graphs, slice_to
from .validator import Issue, validate

__version__ = "0.1.0"

__all__ = [
    "CycleError",
    "EdgeType",
    "Graph",
    "GraphDiff",
    "Issue",
    "Layer",
    "Node",
    "ancestors",
    "diff_graphs",
    "dump_graph",
    "load_graph",
    "render",
    "slice_to",
    "to_dot",
    "to_mermaid",
    "to_yaml",
    "topological_order",
    "validate",
]
