import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from zinet import EdgeType, Graph, Node
from zinet.cli import main
from zinet.schema import json_schema_text

COMMITTED = Path(__file__).resolve().parent.parent / "schemas" / "graph.schema.json"


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


def test_committed_json_schema_matches_models():
    # If this fails, regenerate with: zinet schema -o schemas/graph.schema.json
    assert COMMITTED.read_text(encoding="utf-8") == json_schema_text()


def test_json_schema_names_the_layers_and_edge_types():
    schema = json.loads(json_schema_text())
    assert {"primitives", "concepts", "applications"} <= set(schema["properties"])
    edge_enum = schema["$defs"]["EdgeType"]["enum"]
    assert set(edge_enum) == {"depends_on", "data_flow", "prerequisite", "constraint", "inheritance"}


def test_cli_schema_to_stdout(capfd):
    assert main(["schema"]) == 0
    assert json.loads(capfd.readouterr().out)["title"] == "Graph"
