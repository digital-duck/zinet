from pathlib import Path

import pytest

from zinet import Graph, load_graph, validate

FIXTURES = Path(__file__).parent / "fixtures"


def build(**layers) -> Graph:
    return Graph.model_validate({"version": "1.0", **layers})


def codes(issues, severity: str) -> list[str]:
    return sorted(issue.code for issue in issues if issue.severity == severity)


@pytest.mark.parametrize("name", sorted(p.name for p in FIXTURES.glob("*.yaml")))
def test_bundled_fixtures_are_valid(name):
    assert codes(validate(load_graph(FIXTURES / name)), "error") == []


def test_duplicate_id():
    graph = build(primitives=[{"id": "a"}, {"id": "a"}])
    assert codes(validate(graph), "error") == ["duplicate_id"]


def test_unknown_dependency():
    graph = build(primitives=[{"id": "a"}], concepts=[{"id": "c", "deps": ["ghost"]}])
    assert "unknown_dep" in codes(validate(graph), "error")


def test_primitive_must_be_a_leaf():
    graph = build(primitives=[{"id": "a", "deps": ["b"]}, {"id": "b"}])
    assert "primitive_has_deps" in codes(validate(graph), "error")


def test_nothing_may_depend_on_an_application():
    graph = build(applications=[{"id": "app"}], concepts=[{"id": "c", "deps": ["app"]}])
    assert "layer_violation" in codes(validate(graph), "error")


def test_cycle_is_detected():
    graph = build(concepts=[{"id": "x", "deps": ["y"]}, {"id": "y", "deps": ["x"]}])
    assert "cycle" in codes(validate(graph), "error")


def test_self_loop_is_a_cycle():
    graph = build(concepts=[{"id": "x", "deps": ["x"]}])
    assert "cycle" in codes(validate(graph), "error")


def test_isolated_nodes_are_warnings_not_errors():
    graph = build(primitives=[{"id": "p"}], applications=[{"id": "a"}])
    issues = validate(graph)
    assert codes(issues, "error") == []
    assert codes(issues, "warning") == ["orphan", "orphan"]
