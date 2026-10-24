"""zinet's algorithms reproduce what graph-code and the two ConceptBook copies do (golden files in tests/characterization).

Each source is reproduced with the options that select its behaviour. The only differences from the golden results are
the ones we decided on: a missing node raises `UnknownNodeError` and a cycle in what is being ordered raises
`CycleError`, where the copies raised assorted errors or, for `productivity_order` on a cycle, silently dropped the
nodes on it (graph-code returns a short list, ConceptBook returns the part before the cycle).
"""
import importlib.util
import json
from pathlib import Path

import networkx as nx
import pytest

import zinet
from zinet import CycleError, UnknownNodeError

DIR = Path(__file__).parent / "characterization"


def _cases():
    spec = importlib.util.spec_from_file_location("zinet_characterization_cases", DIR / "cases.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CASES


CASES = {c["name"]: c for c in _cases()}


def golden(name):
    return json.loads((DIR / "golden" / f"{name}.json").read_text(encoding="utf-8"))["cases"]


def build(case, *, optional=False):
    """The case as a DiGraph (dependency -> dependent). Optional edges carry `optional=True`."""
    G = nx.DiGraph()
    for p in case["primitives"]:
        G.add_node(p, kind="primitive")
    for n in case["nodes"]:
        G.add_node(n["id"], kind=n.get("kind", "concept"))
    for n in case["nodes"]:
        for dep in n["deps"]:
            G.add_edge(dep, n["id"])
        for dep in n.get("optional", []):
            G.add_edge(dep, n["id"], optional=True)
    return G


def mandatory(G):
    return zinet.mandatory_subgraph(G, lambda u, v, d: not d.get("optional"))


def check(expected, call, *, errors):
    """Compare a golden result with a zinet call. `errors` maps the golden's exception name to zinet's."""
    if isinstance(expected, dict) and "raises" in expected:
        with pytest.raises(errors[expected["raises"]]):
            call()
    else:
        assert call() == expected


# ---- graph-code -------------------------------------------------------------------------------------------------

GC_ERRORS = {"ToolFailed": UnknownNodeError, "NetworkXUnfeasible": CycleError}
GC = golden("graph_code")


@pytest.mark.parametrize("name", sorted(GC))
def test_graph_code(name):
    case, g = CASES[name], GC[name]
    G = build(case)
    M = mandatory(G)
    cyclic = name == "cycle"

    # graph-code's acyclic looks at every edge, optional ones included
    if g["acyclic"] == "ok":
        zinet.ensure_acyclic(G)
    else:
        with pytest.raises(CycleError):
            zinet.ensure_acyclic(G)

    assert zinet.reducible(M, rule="primitive_ancestry") == g["reducible"]
    assert zinet.reducible(M, rule="primitive_ancestry", roots=case.get("first_radical", [])) == g["reducible_first_radical_only"]

    for key, weight in (("productivity_order_w1", 1.0), ("productivity_order_w2", 2.0)):
        if cyclic:                                   # graph-code silently drops the nodes on the cycle; zinet raises
            with pytest.raises(CycleError):
                zinet.productivity_order(M, weight)
        else:
            assert zinet.productivity_order(M, weight) == g[key]

    if cyclic:
        with pytest.raises(CycleError):
            zinet.build_order(M)
    else:
        assert zinet.build_order(M) == g["build_order"]

    for i, q in enumerate(case["queries"]):
        check(g[f"learning_path_{i}"], lambda q=q: zinet.learning_path(M, q["target"], q["known"]), errors=GC_ERRORS)
        check(g[f"gap_{i}"], lambda q=q: zinet.gap(M, q["target"], q["known"]), errors=GC_ERRORS)


# ---- ConceptBook ------------------------------------------------------------------------------------------------

CB_ERRORS = {"NetworkXError": UnknownNodeError}
CB = {"conceptbook_v1": golden("conceptbook_v1"), "conceptbook_v2": golden("conceptbook_v2")}
CB_CASES = sorted(CB["conceptbook_v1"])


@pytest.mark.parametrize("source", sorted(CB))
@pytest.mark.parametrize("name", CB_CASES)
def test_conceptbook(source, name):
    case, g = CASES[name], CB[source][name]
    G = build(case)
    prims = list(case["primitives"]) + list(case.get("listed_only", []))
    cyclic = name == "cycle"

    assert zinet.is_acyclic(G) == g["acyclic"]
    rule = "declared" if source == "conceptbook_v1" else "declared_or_listed"
    assert zinet.reducible(G, prims, rule=rule) == g["reducible"]
    if source == "conceptbook_v1":
        assert zinet.reducible(G, prims, rule="named_primitives") == g["reducible_strict"]

    reach = dict(include_primitives=True, weighted_applications=True, seed_by_reach=True)
    for key, weight in (("productivity_order_w1", 1.0), ("productivity_order_w2", 2.0)):
        if cyclic:                                   # ConceptBook silently returns part of the order; zinet raises
            with pytest.raises(CycleError):
                zinet.productivity_order(G, weight, **reach)
        else:
            assert zinet.productivity_order(G, weight, **reach) == g[key]

    for node, expected in g["applications_of"].items():
        assert zinet.applications_of(G, node) == expected

    for i, q in enumerate(case["queries"]):
        check(g[f"ancestors_{i}"], lambda q=q: sorted(zinet.ancestors(G, q["target"])), errors=CB_ERRORS)
        gap_call = lambda q=q: sorted(zinet.gap(G, q["target"], q["known"], include_primitives=True, include_target=False))  # noqa: E731
        path_call = lambda q=q: zinet.learning_path(G, q["target"], q["known"], include_primitives=True,  # noqa: E731
                                                    include_target=False, order="reach")
        # in the `cycle` case the cycle runs through the target, which ConceptBook's path leaves out, so what is left
        # is acyclic and both give the golden answer
        check(g[f"gap_{i}"], gap_call, errors=CB_ERRORS)
        check(g[f"learning_path_{i}"], path_call, errors=CB_ERRORS)
