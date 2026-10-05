import pytest

from graph_ir import CycleError, ancestors, topological_order


def test_order_puts_dependencies_first():
    deps = {"app": ["mid"], "mid": ["leaf"], "leaf": []}
    assert topological_order(deps) == ["leaf", "mid", "app"]


def test_order_is_deterministic_for_ties():
    deps = {"b": [], "a": [], "c": ["a", "b"]}
    assert topological_order(deps) == ["a", "b", "c"]


def test_cycle_reports_only_nodes_on_the_cycle():
    deps = {"root": ["x"], "x": ["y"], "y": ["x"]}
    with pytest.raises(CycleError) as info:
        topological_order(deps)
    assert info.value.members == ["x", "y"]


def test_self_loop_is_reported():
    with pytest.raises(CycleError) as info:
        topological_order({"a": ["a"], "b": []})
    assert info.value.members == ["a"]


def test_ancestors_is_transitive_closure_without_target():
    deps = {"top": ["mid"], "mid": ["leaf"], "leaf": [], "other": []}
    assert ancestors(deps, "top") == {"mid", "leaf"}


def test_ancestors_unknown_target_raises():
    with pytest.raises(KeyError):
        ancestors({"a": []}, "missing")
