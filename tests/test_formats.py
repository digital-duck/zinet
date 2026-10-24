"""zinet says what a graph file is when it is not a zinet graph (the file name never decides)."""
import pytest

from zinet import load_graph
from zinet.cli import main
from zinet.formats import CONCEPTBOOK, GRAPHLANG, UNKNOWN, ZINET, detect, explain_foreign

GRAPHLANG_YAML = 'version: "1.0-graph"\nworkflow: {name: w}\nnodes: []\nedges: []\n'
CONCEPTBOOK_YAML = "domain: demo\nprimitives:\n  p: {tier: 0}\nconcepts:\n  a: {composed_of: [p]}\n"


@pytest.mark.parametrize("data, kind", [
    ({"version": "1.0-graph", "workflow": {"name": "w"}, "nodes": [], "edges": []}, GRAPHLANG),
    ({"nodes": [], "edges": []}, GRAPHLANG),
    ({"version": "1.0", "primitives": [], "concepts": []}, ZINET),
    ({"applications": [{"id": "a"}]}, ZINET),
    ({"primitives": None, "concepts": []}, ZINET),
    ({"domain": "x", "primitives": {"p": {}}, "concepts": {"a": {"composed_of": ["p"]}}}, CONCEPTBOOK),
    ({}, UNKNOWN), ({"hello": 1}, UNKNOWN), ([1], UNKNOWN), (None, UNKNOWN),
])
def test_detect(data, kind):
    assert detect(data) == kind


def test_a_zinet_graph_has_nothing_to_explain():
    assert explain_foreign({"primitives": [{"id": "a"}]}) is None and explain_foreign({"version": "1.0"}) is None


@pytest.mark.parametrize("name", ["graph.yaml", "workflow.graph.yaml", "anything.yaml"])
def test_a_graphlang_workflow_is_named_whatever_the_file_is_called(tmp_path, name):
    f = tmp_path / name
    f.write_text(GRAPHLANG_YAML)
    with pytest.raises(ValueError, match=r"GraphLang workflow.*graf validate\|vis\|run") as info:
        load_graph(f)
    assert "unsupported graph version" not in str(info.value) and name in str(info.value)


def test_a_conceptbook_graph_is_named_and_not_called_a_validation_error(tmp_path):
    f = tmp_path / "graph.yaml"
    f.write_text(CONCEPTBOOK_YAML)
    with pytest.raises(ValueError, match=r"ConceptBook / graph-code graph.*cannot read yet") as info:
        load_graph(f)
    assert "valid list" not in str(info.value)


@pytest.mark.parametrize("command", [["validate"], ["render"], ["prettify"], ["convert"]])
def test_every_command_reports_it_with_exit_2(tmp_path, capsys, command):
    f = tmp_path / "graph.yaml"
    f.write_text(GRAPHLANG_YAML)
    assert main([*command, str(f)]) == 2
    assert "GraphLang workflow" in capsys.readouterr().err
