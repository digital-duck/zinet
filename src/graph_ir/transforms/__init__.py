"""Graph-level operations shared by all back-ends."""

from .diff import GraphDiff, diff_graphs
from .slice import slice_to

__all__ = ["GraphDiff", "diff_graphs", "slice_to"]
