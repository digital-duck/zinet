"""zinet.vis on zinet's own graphs (agreement with GraphLang and work-graph is in test_vis_characterization)."""
import json
import re
import shutil
from pathlib import Path

import networkx as nx
import pytest

import zinet
from zinet import Graph
from zinet.vis import ENGINES, Style, render, select, to_ascii_text, to_dot, to_mermaid_text, zinet_style
from zinet.vis.cytoscape import cytoscape_html, elements


def sample() -> nx.DiGraph:
    graph = Graph.model_validate({
        "primitives": [{"id": "x", "label": "X"}, {"id": "y"}],
        "concepts": [{"id": "c", "deps": ["x", "y"], "edge_types": {"x": "constraint"}}],
        "applications": [{"id": "app", "label": "The app", "deps": ["c"]}],
    })
    return zinet.to_networkx(graph)


def page_data(page: str) -> list[dict]:
    return json.loads(re.search(r"const data = (\[.*?\]);\nconst OPTS", page, re.S).group(1).replace("<\\/", "</"))


def test_the_default_style_reads_what_to_networkx_writes():
    G, s = sample(), zinet_style()
    assert s.label("x", G.nodes["x"]) == "X" and s.label("y", G.nodes["y"]) == "y"
    assert s.shape("x", G.nodes["x"]) == "ellipse" and s.shape("app", G.nodes["app"]) == "round-rectangle"
    assert s.edge_dashed("x", "c", G.edges["x", "c"]) and not s.edge_dashed("y", "c", G.edges["y", "c"])
    assert s.edge_label("x", "c", G.edges["x", "c"]) == "constraint" and s.edge_label("y", "c", G.edges["y", "c"]) == ""
    assert [k for k, _ in s.legend(G)] == ["application", "concept", "primitive"]


def test_cytoscape_page_is_self_contained_and_complete(tmp_path):
    out = render(sample(), tmp_path / "g.html")
    page = out.read_text(encoding="utf-8")
    assert "cytoscape(" in page and 'src="http' not in page and "https://" not in page.split("<script>")[0]
    data = page_data(page)
    nodes = {e["data"]["id"]: e["data"] for e in data if "source" not in e["data"]}
    assert nodes["app"]["text"] == "The app\napplication" and nodes["x"]["shape"] == "ellipse"
    edges = [e["data"] for e in data if "source" in e["data"]]
    assert {(e["source"], e["target"]): e["dashed"] for e in edges} == {("x", "c"): True, ("y", "c"): False, ("c", "app"): False}
    assert "primitive" in page and "dependency" in page and "typed" in page          # legend


def test_positions_come_from_dot_when_installed_and_the_page_still_works_without(tmp_path, monkeypatch):
    if shutil.which("dot"):
        page = cytoscape_html(sample(), zinet_style())
        assert all("position" in e for e in page_data(page) if "source" not in e["data"]) and "<option>dot</option>" in page
    monkeypatch.setattr(shutil, "which", lambda name: None)
    page = cytoscape_html(sample(), zinet_style())
    assert not any("position" in e for e in page_data(page)) and "<option>dot</option>" not in page and "<option>cose</option>" in page


def test_groups_are_boxes_in_every_engine():
    G = sample()
    G.add_node("body", kind="concept", parent="c")
    G.add_edge("body", "app")
    s = zinet_style()
    assert 'subgraph "cluster_c"' in to_dot(G, s)
    assert 'subgraph n' in to_mermaid_text(G, s) and "end" in to_mermaid_text(G, s)
    assert any(e["data"].get("parent") == "c" for e in elements(G, s))
    assert [e["data"]["text"] for e in elements(G, s) if e["data"]["id"] == "c"] == ["c"]      # a box shows only its name


def test_mermaid_and_dot_text_for_a_zinet_graph():
    G, s = sample(), zinet_style()
    m = to_mermaid_text(G, s)
    assert m.startswith("flowchart LR") and "-.->|\"constraint\"|" in m and "classDef primitive" in m
    assert '((' in m                                            # ellipse
    d = to_dot(G, s)
    assert 'shape=ellipse' in d and 'style=dashed' in d and d.count("->") == 3
    assert "#quot;" in to_mermaid_text(nx.DiGraph([("a", 'say "hi"')]), Style())


def test_ascii_groups_by_depth_and_survives_a_cycle():
    text = to_ascii_text(sample(), zinet_style())
    assert text.splitlines()[0] == "Tier 0"
    assert "[primitive  ] X" in text and "[concept    ] c  <- X, y" in text and "Tier 2" in text
    cyclic = nx.DiGraph([("a", "b"), ("b", "a")])
    assert "has a cycle" in to_ascii_text(cyclic, Style())


def test_graphviz_engine_writes_an_image_or_dot_text(tmp_path):
    if shutil.which("dot"):
        assert render(sample(), tmp_path / "g.svg", "graphviz").read_text(encoding="utf-8").lstrip().startswith(("<?xml", "<svg"))
        assert render(sample(), tmp_path / "g.png", "graphviz").read_bytes()[:4] == b"\x89PNG"
    else:
        with pytest.raises(RuntimeError, match="dot is not installed"):
            render(sample(), tmp_path / "g.svg", "graphviz")
        assert (tmp_path / "g.dot").exists()


def test_mermaid_markdown_wrapper_and_ascii_file(tmp_path):
    assert render(sample(), tmp_path / "g.md", "mermaid").read_text(encoding="utf-8").startswith("```mermaid\nflowchart LR")
    assert render(sample(), tmp_path / "g.txt", "ascii").read_text(encoding="utf-8").startswith("Tier 0")


def test_optional_engines_work_or_say_what_to_install(tmp_path):
    for engine, extra in (("pyvis", "zinet[pyvis]"), ("graphify", "zinet[graphify]")):
        ready = ENGINES[engine]["ready"]()[0]
        if ready:
            assert render(sample(), tmp_path / f"{engine}.html", engine).stat().st_size > 1000
        else:
            with pytest.raises(RuntimeError, match=re.escape(extra)):
                render(sample(), tmp_path / f"{engine}.html", engine)


def test_render_errors_are_clear(tmp_path):
    with pytest.raises(ValueError, match="unknown engine"):
        render(sample(), tmp_path / "x", "nope")
    with pytest.raises(ValueError, match="no nodes"):
        render(nx.DiGraph(), tmp_path / "x.html")


def test_the_engine_registry():
    assert set(ENGINES) == {"cytoscape", "graphviz", "mermaid", "ascii", "pyvis", "graphify"}
    assert {e for e, s in ENGINES.items() if s.get("required")} == {"pyvis", "graphify"}


def test_zinet_render_cli_has_html_and_ascii(tmp_path, capsys):
    from zinet.cli import main
    fixture = Path(__file__).parent / "fixtures" / "solver_problem.yaml"
    assert main(["render", str(fixture), "--format", "ascii"]) == 0
    assert capsys.readouterr().out.startswith("Tier 0")
    out = tmp_path / "g.html"
    assert main(["render", str(fixture), "--format", "html", "-o", str(out)]) == 0
    assert "cytoscape(" in out.read_text(encoding="utf-8")


# ---- select ------------------------------------------------------------------------------------------------------

def big() -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_edges_from([("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")])
    G.add_node("lonely")
    G.nodes["c"]["kind"] = "noise"
    return G


def test_select_neighbourhood_cap_and_isolated_nodes():
    G = big()
    sub, note = select(G)
    assert "lonely" not in sub and sorted(sub) == ["a", "b", "c", "d", "e"] and note == ""
    sub, note = select(G, node="b", hops=1)
    assert sorted(sub) == ["a", "b", "c"] and note == "1 hop(s) around b"
    sub, note = select(G, max_nodes=2)
    assert sub.number_of_nodes() == 2 and "best-connected" in note
    with pytest.raises(ValueError, match="no node"):
        select(G, node="zzz")


def test_select_hidden_kinds_and_dropped_edges():
    G = big()
    hidden = lambda n, d: d.get("kind") == "noise"  # noqa: E731
    assert "c" not in select(G, hidden=hidden)[0]
    assert "c" in select(G, hidden=hidden, show_hidden=True)[0]
    sub, _ = select(G, drop_edge=lambda g, u, v, d: (u, v) == ("a", "b"))
    assert not sub.has_edge("a", "b") and "a" not in sub                    # a is isolated once its only edge goes


def test_a_force_style_draws_sized_nodes_with_a_force_layout_and_marks(tmp_path, monkeypatch):
    G = nx.DiGraph([("a", "b"), ("a", "c"), ("b", "c")])
    style = Style(node_size=lambda g, n, d: 10 + 4 * g.degree(n), arrangement="force", title="t")
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/dot")           # even with dot present, "force" does not use it
    page = cytoscape_html(G, style, mark={"b"})
    data = page_data(page)
    nodes = {e["data"]["id"]: e for e in data if "source" not in e["data"]}
    assert nodes["a"]["data"]["size"] == 18 and nodes["a"]["data"]["sized"] is True and nodes["a"]["data"]["text"] == "a"
    assert nodes["b"]["data"]["mark"] == 1 and "mark" not in nodes["a"]["data"]
    assert not any("position" in e for e in data) and "<option>dot</option>" not in page
    assert page.index("<option>cose</option>") < page.index("<option>grid</option>")
    assert "node[mark]" in page and "node[?sized]" in page


def test_the_flow_arrangement_is_the_default_and_unsized():
    style = zinet_style()
    assert style.arrangement == "flow" and style.node_size is None
    data = page_data(cytoscape_html(sample(), style))
    assert all("sized" not in e["data"] and "mark" not in e["data"] for e in data if "source" not in e["data"])


def test_pyvis_uses_a_force_layout_for_force_styles(tmp_path):
    if not ENGINES["pyvis"]["ready"]()[0]:
        pytest.skip("pyvis not installed")
    G = nx.DiGraph([("a", "b"), ("b", "c")])
    flow = render(G, tmp_path / "flow.html", "pyvis", Style()).read_text(encoding="utf-8")
    force = render(G, tmp_path / "force.html", "pyvis", Style(node_size=lambda g, n, d: 20, arrangement="force")).read_text(encoding="utf-8")
    # the page inlines the whole vis-network library, so look for the options this engine writes, not for a word
    assert '"direction": "LR"' in flow and '"springLength": 140' not in flow
    assert '"direction": "LR"' not in force and '"springLength": 140' in force


def test_show_kind_false_leaves_only_the_label_on_nodes_in_every_engine(tmp_path):
    G = sample()
    on, off = zinet_style(), zinet_style()
    off.show_kind = False
    text = lambda s: {e["data"]["id"]: e["data"]["text"] for e in elements(G, s) if "source" not in e["data"]}  # noqa: E731
    assert text(on)["app"] == "The app\napplication" and text(off)["app"] == "The app"
    assert "application" in to_mermaid_text(G, on).split("classDef")[0] and "<br/>" not in to_mermaid_text(G, off)
    assert "\\napplication" in to_dot(G, on) and "\\napplication" not in to_dot(G, off)
    assert off.legend(G) == on.legend(G)                                     # the legend still names the kinds
