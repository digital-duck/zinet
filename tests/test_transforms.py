from pathlib import Path

import pytest

from graph_ir import Node, diff_graphs, load_graph, slice_to

FIXTURES = Path(__file__).parent / "fixtures"


def test_slice_keeps_only_prerequisite_closure():
    graph = load_graph(FIXTURES / "spl_pipeline.yaml")
    sliced = slice_to(graph, "step_summarize")
    assert sorted(n.id for n in sliced.nodes()) == ["step_summarize", "tool_cache_get", "tool_llm_call"]


def test_slice_unknown_target_raises():
    with pytest.raises(KeyError):
        slice_to(load_graph(FIXTURES / "spl_pipeline.yaml"), "nope")


def test_identical_graphs_have_empty_diff():
    graph = load_graph(FIXTURES / "concept_book.yaml")
    assert diff_graphs(graph, graph.model_copy(deep=True)).is_empty


def test_diff_reports_added_removed_and_changed():
    old = load_graph(FIXTURES / "spl_pipeline.yaml")
    new = old.model_copy(deep=True)
    new.concepts[0].label = "summarize v2"
    new.applications.clear()
    new.primitives.append(Node(id="tool_new"))

    result = diff_graphs(old, new)
    assert result.added == ["tool_new"]
    assert result.removed == ["recipe_build_concept_book"]
    assert result.changed == {"step_summarize": {"label": (None, "summarize v2")}}
