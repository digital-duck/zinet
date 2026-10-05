import pytest
from pydantic import ValidationError

from graph_ir import EdgeType, Graph, Node


def test_typed_edge_must_refer_to_a_dependency():
    with pytest.raises(ValidationError, match="non-dependencies"):
        Node(id="c", deps=["a"], edge_types={"b": EdgeType.CONSTRAINT})


def test_unknown_top_level_key_is_rejected():
    with pytest.raises(ValidationError):
        Graph.model_validate({"primitves": [{"id": "a"}]})


def test_index_rejects_duplicate_ids():
    graph = Graph.model_validate({"primitives": [{"id": "a"}], "concepts": [{"id": "a"}]})
    with pytest.raises(ValueError, match="duplicate node id"):
        graph.index()
