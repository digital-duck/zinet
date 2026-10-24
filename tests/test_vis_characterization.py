"""zinet.vis reproduces GraphLang's drawing output and work-graph's subgraph picker (golden files in tests/characterization).

The inputs are stored in the golden files, so these tests need neither GraphLang nor work-graph installed. Each app is
reproduced through a `Style` (or the `select` predicates) that reads that app's own attribute names.
"""
import json
from pathlib import Path

import networkx as nx
import pytest

from zinet.vis import Style, select
from zinet.vis.cytoscape import elements
from zinet.vis.dot import to_dot
from zinet.vis.mermaid import to_mermaid_text

GOLDEN = Path(__file__).parent / "characterization" / "golden"


def load(name):
    return json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))


def to_graph(doc, cls=nx.MultiDiGraph):
    G = cls()
    for n, attrs in doc["nodes"]:
        G.add_node(n, **attrs)
    for u, v, attrs in doc["edges"]:
        G.add_edge(u, v, **attrs)
    return G


# ---- GraphLang --------------------------------------------------------------------------------------------------

ROUND = {"INPUT", "OUTPUT", "EMIT"}
DIAMOND = {"EVALUATE", "ASSERT", "GUARD"}
HEXAGON = {"FORK", "JOIN"}


def graphlang_style(title: str) -> Style:
    return Style(
        label=lambda n, d: d["label"], kind=lambda n, d: d["kind"], color=lambda n, d: d["color"],
        shape=lambda n, d: ("round-rectangle" if d["kind"] in ROUND else "diamond" if d["kind"] in DIAMOND
                            else "hexagon" if d["kind"] in HEXAGON else "rectangle"),
        group=lambda n, d: d.get("parent"), info=lambda n, d: d["info"],
        edge_label=lambda u, v, d: d["label"], edge_kind=lambda u, v, d: d["relation"],
        edge_dashed=lambda u, v, d: d["relation"] == "binds", edge_info=lambda u, v, d: f"{d['sport']} → {d['tport']}",
        edge_legend=(("control", False), ("data", True)), title=title)


GL = load("graphlang_engines")["cases"]


@pytest.mark.parametrize("name", sorted(GL))
def test_text_engines_match_graphlang(name):
    g = GL[name]
    G = to_graph(g["graph"])
    style = graphlang_style(f"{name} (GraphLang)")
    assert to_mermaid_text(G, style) == g["mermaid"]
    assert to_dot(G, style) == g["dot"]
    assert to_dot(G, style, fixed_size=True) == g["dot_fixed_size"]


@pytest.mark.parametrize("name", sorted(GL))
def test_cytoscape_elements_match_graphlang(name):
    g = GL[name]
    got = elements(to_graph(g["graph"]), graphlang_style(name))
    assert len(got) == len(g["cytoscape_elements"])
    for mine, theirs in zip(got, g["cytoscape_elements"]):
        a, b = mine["data"], theirs["data"]
        if "source" in b:                                          # an edge
            assert {k: a[k] for k in ("id", "source", "target", "relation", "label")} == {k: b[k] for k in ("id", "source", "target", "relation", "label")}
            assert a["info"] == f"{b['sport']} → {b['tport']}" and a["dashed"] == (b["relation"] == "binds")
        else:                                                      # a node: every field GraphLang had is reproduced
            assert a == b


# ---- work-graph select ------------------------------------------------------------------------------------------

WG = load("workgraph_select")
HIDDEN_KINDS = {"symbol", "external", "rationale"}
STRUCTURE_KINDS = {"stage", "project", "process"}
HUB_RELATIONS = {"in_stage", "belongs_to"}


def workgraph_select(M, *, layer=None, project=None, kind=None, stage=None, node=None, hops=2, include_code=False,
                     hubs=False, max_nodes=400):
    """work-graph's viz.select, expressed with zinet.vis.select."""
    return select(
        M,
        keep=lambda n, d: ((not layer or d.get("layer") == layer) and (not project or d.get("project") == project)
                           and (not kind or d.get("kind") == kind) and (not stage or stage in d.get("stages", []))),
        hidden=lambda n, d: d.get("kind") in HIDDEN_KINDS, show_hidden=include_code,
        drop_edge=None if hubs else (lambda G, u, v, d: d.get("relation") in HUB_RELATIONS and G.nodes[v].get("kind") in STRUCTURE_KINDS),
        node=node, hops=hops, max_nodes=max_nodes)


@pytest.mark.parametrize("name", sorted(WG["cases"]))
def test_select_matches_workgraph(name):
    expected, kwargs = WG["cases"][name], WG["calls"][name]
    M = to_graph(WG["graph"])
    if "raises" in expected:
        with pytest.raises(ValueError) as info:
            workgraph_select(M, **kwargs)
        assert str(info.value) == expected["message"]
        return
    sub, note = workgraph_select(M, **kwargs)
    assert sorted(sub.nodes) == expected["nodes"]
    assert sorted([u, v, d.get("relation")] for u, v, d in sub.edges(data=True)) == expected["edges"]
    assert note == expected["note"]
