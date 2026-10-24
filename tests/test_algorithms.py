"""The graph algorithms on plain networkx graphs (their agreement with graph-code and ConceptBook is in test_algorithms_characterization)."""
import networkx as nx
import pytest

import zinet
from zinet import CycleError, Graph, UnknownNodeError


def chain() -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_node("p", kind="primitive")
    for n in ("a", "b"):
        G.add_node(n, kind="concept")
    G.add_node("app", kind="application")
    G.add_edges_from([("p", "a"), ("a", "b"), ("b", "app")])
    return G


def test_to_networkx_carries_kind_label_and_edge_type():
    graph = Graph.model_validate({
        "primitives": [{"id": "x", "label": "X"}],
        "concepts": [{"id": "c", "deps": ["x", "ghost"], "edge_types": {"x": "constraint"}}],
    })
    G = zinet.to_networkx(graph)
    assert G.nodes["x"] == {"kind": "primitive", "label": "X"} and G.nodes["c"]["kind"] == "concept"
    assert G.edges["x", "c"]["edge_type"] == "constraint" and G.edges["ghost", "c"]["edge_type"] == "depends_on"
    assert "kind" not in G.nodes["ghost"]                      # an undefined dependency is an undeclared node


def test_dag_functions_accept_a_digraph_and_keep_their_mapping_behaviour():
    G = chain()
    assert zinet.topological_order(G) == ["p", "a", "b", "app"]
    assert zinet.ancestors(G, "b") == {"p", "a"}
    assert zinet.topological_order({"b": ["a"], "a": []}) == ["a", "b"]


def test_unknown_node_is_a_keyerror_so_old_callers_still_work():
    with pytest.raises(KeyError) as info:
        zinet.ancestors({"a": []}, "nope")
    assert isinstance(info.value, UnknownNodeError) and info.value.node == "nope" and "nope" in str(info.value)
    for call in (lambda: zinet.learning_path(chain(), "nope"), lambda: zinet.gap(chain(), "nope"),
                 lambda: zinet.applications_of(chain(), "nope")):
        with pytest.raises(UnknownNodeError):
            call()


def test_ensure_acyclic_names_the_nodes_on_the_cycle():
    G = chain()
    assert zinet.is_acyclic(G)
    zinet.ensure_acyclic(G)
    G.add_edge("app", "a")
    assert not zinet.is_acyclic(G)
    with pytest.raises(CycleError) as info:
        zinet.ensure_acyclic(G)
    assert info.value.members == ["a", "app", "b"]


def test_a_cycle_in_what_is_being_ordered_raises_in_every_ordering_function():
    G = chain()
    G.add_edge("app", "a")
    for call in (lambda: zinet.build_order(G), lambda: zinet.productivity_order(G), lambda: zinet.learning_path(G, "app")):
        with pytest.raises(CycleError):
            call()


def test_orders_agree_on_a_chain_and_differ_on_ties_as_documented():
    G = chain()
    assert zinet.build_order(G) == ["a", "b", "app"]
    assert zinet.build_order(G, include_primitives=True) == ["p", "a", "b", "app"]
    T = nx.DiGraph()                                           # inserted out of alphabetical order
    for n in ("zeta", "alpha", "omega"):
        T.add_node(n, kind="concept")
    T.add_edges_from([("zeta", "omega"), ("alpha", "omega")])
    assert zinet.build_order(T) == ["zeta", "alpha", "omega"]                      # insertion order, as graph-code
    assert zinet.build_order(T, order="alphabetical") == ["alpha", "zeta", "omega"]  # like zinet.topological_order


def test_learning_path_and_gap_options():
    G = chain()
    assert zinet.learning_path(G, "app", ["a"]) == ["b", "app"]
    assert zinet.learning_path(G, "app", include_target=False) == ["a", "b"]
    assert zinet.learning_path(G, "app", include_primitives=True) == ["p", "a", "b", "app"]
    assert zinet.learning_path(G, "app", ["a", "b", "app"]) == []
    assert zinet.learning_path(G, "p") == []                                       # a primitive is always available
    assert zinet.gap(G, "app", ["a"]) == ["b", "app"]
    assert zinet.learning_path(G, "app", order="reach", include_primitives=True) == ["p", "a", "b", "app"]


def test_explicit_primitives_override_the_kind_attribute():
    G = chain()
    assert zinet.learning_path(G, "app", primitives=["p", "a"]) == ["b", "app"]


def test_mandatory_subgraph_drops_optional_edges_only():
    G = chain()
    G.add_edge("p", "app", optional=True)
    M = zinet.mandatory_subgraph(G, lambda u, v, d: not d.get("optional"))
    assert not M.has_edge("p", "app") and M.has_edge("a", "b") and set(M) == set(G)


def test_restrict_returns_an_independent_copy():
    G = chain()
    R = zinet.restrict(G, ["a", "b"])
    assert set(R) == {"a", "b"} and list(R.edges) == [("a", "b")]
    R.add_node("new")
    assert "new" not in G


def test_productivity_order_unlocks_the_hub_first_and_weights_applications():
    G = nx.DiGraph()
    G.add_node("p", kind="primitive")
    for n in ("hub", "side", "x", "y", "z"):
        G.add_node(n, kind="concept")
    G.add_node("app", kind="application")
    G.add_edges_from([("p", "hub"), ("p", "side"), ("hub", "x"), ("hub", "y"), ("side", "z"), ("z", "app")])
    # after the hub and `side`, `z` goes before the leaves x and y because it unlocks `app`
    assert zinet.productivity_order(G) == ["hub", "side", "z", "app", "x", "y"]
    assert zinet.productivity_order(G, include_primitives=True)[0] == "p"
    # application-heavy branch overtakes once applications are weighted (ConceptBook style)
    plain = zinet.productivity_order(G, 5.0, weighted_applications=True, seed_by_reach=True)
    assert plain.index("side") < plain.index("hub")


@pytest.mark.parametrize("rule, expected", [
    ("primitive_ancestry", False),      # `root` has no primitive ancestor
    ("declared", True),                 # `root` was declared
    ("declared_or_listed", True),
    ("named_primitives", False),        # the only root besides p is `root`, which is not a primitive
])
def test_reducible_rules_on_a_foundation_concept(rule, expected):
    G = nx.DiGraph()
    G.add_node("p", kind="primitive")
    G.add_node("root", kind="concept")
    G.add_node("a", kind="concept")
    G.add_edges_from([("root", "a"), ("p", "a")])
    assert zinet.reducible(G, rule=rule) is expected


def test_reducible_roots_restrict_which_primitives_count():
    G = nx.DiGraph()
    for p in ("x", "m"):
        G.add_node(p, kind="primitive")
    G.add_node("v", kind="concept")
    G.add_edges_from([("x", "v"), ("m", "v")])
    assert zinet.reducible(G) is True
    assert zinet.reducible(G, roots=["x"]) is False


def test_reducible_rejects_an_unknown_rule():
    with pytest.raises(ValueError, match="unknown reducible rule"):
        zinet.reducible(chain(), rule="nonsense")  # type: ignore[arg-type]
