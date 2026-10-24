"""The interactive page: its options, its layout data, and (where Node / Chrome are installed) that its JavaScript runs and behaves.

The behaviour tests drive the real page in headless Chrome and read the result back; they are skipped when no Chrome is found.
The syntax test runs the page's own script through `node --check`; it is skipped without Node. Python alone cannot tell that a
template with a stray newline in a JavaScript string is broken, which is how this test came to exist."""
import html as htmllib
import json
import re
import shutil
import subprocess

import networkx as nx
import pytest

from zinet.vis import Style
from zinet.vis.cytoscape import cytoscape_html, elements
from zinet.vis.dot import dot_layouts

CHROME = next((c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)


def workflow() -> nx.DiGraph:
    """s -> a -> grp[b -> c] -> e, with dashed data edges (s->a, a->e, b->c) next to the control edges: a multigraph, like GraphLang's."""
    G = nx.MultiDiGraph()
    for n in ("s", "a", "e"):
        G.add_node(n)
    G.add_node("grp")
    G.add_node("b", parent="grp")
    G.add_node("c", parent="grp")
    for u, v in (("s", "a"), ("a", "grp"), ("grp", "e")):
        G.add_edge(u, v)
    G.add_edge("b", "c")
    for u, v in (("s", "a"), ("a", "e"), ("b", "c")):
        G.add_edge(u, v, data=True)
    return G


def style(**kw) -> Style:
    return Style(group=lambda n, d: d.get("parent"), edge_dashed=lambda u, v, d: bool(d.get("data")),
                 edge_legend=(("control", False), ("data", True)), title="t", **kw)


def script_of(page: str) -> str:
    """The page's own script: the last <script> block (the one before it is the bundled library)."""
    return re.findall(r"<script>(.*?)</script>", page, re.S)[-1]


def page_opts(page: str) -> dict:
    return json.loads(re.search(r"const OPTS = (\{.*?\});", page).group(1))


# ---- options and controls ---------------------------------------------------------------------------------------

def test_plain_style_shows_everything_and_offers_the_controls():
    page = cytoscape_html(workflow(), style())
    assert page_opts(page) == {"dataHidden": False, "collapsed": False}
    assert 'id="showdata" checked' in page and "show data edges" in page
    assert 'id="collapseall"' in page and 'id="expandall"' in page


def test_secondary_hidden_and_collapsed_are_options_of_the_style():
    page = cytoscape_html(workflow(), style(secondary_hidden=True, groups_collapsed=True))
    assert page_opts(page) == {"dataHidden": True, "collapsed": True}
    assert 'id="showdata"' in page and 'id="showdata" checked' not in page


def test_no_dashed_edges_and_no_groups_means_no_extra_controls():
    G = nx.DiGraph([("a", "b")])
    page = cytoscape_html(G, Style(secondary_hidden=True, groups_collapsed=True))
    assert page_opts(page) == {"dataHidden": False, "collapsed": False}                      # nothing to hide or collapse
    assert 'id="showdata"' not in page and 'id="collapseall"' not in page


def test_the_toggle_is_named_after_the_dashed_kind_in_the_legend():
    page = cytoscape_html(workflow(), Style(group=lambda n, d: d.get("parent"), edge_dashed=lambda u, v, d: bool(d.get("data")),
                                           edge_legend=(("dependency", False), ("typed", True))))
    assert "show typed edges" in page


# ---- layout data --------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which("dot"), reason="Graphviz not installed")
def test_dot_layouts_give_an_expanded_and_a_collapsed_arrangement_and_group_centres():
    G, s = workflow(), style()
    lay = dot_layouts(G, s)
    assert set(lay["expanded"]) == {"s", "a", "e", "b", "c"}                    # the group is a box around b and c: no own position
    assert set(lay["collapsed"]) == {"s", "a", "grp", "e"}                      # contracted: the group is one node, b and c are gone
    cx, cy = lay["centers"]["grp"]["x"], lay["centers"]["grp"]["y"]
    xs, ys = [lay["expanded"][n]["x"] for n in "bc"], [lay["expanded"][n]["y"] for n in "bc"]
    assert min(xs) <= cx <= max(xs) and min(ys) <= cy <= max(ys)


@pytest.mark.skipif(not shutil.which("dot"), reason="Graphviz not installed")
def test_elements_carry_the_layouts_only_when_asked():
    G, s = workflow(), style()
    plain = {e["data"]["id"]: e["data"] for e in elements(G, s) if "source" not in e["data"]}
    assert all(not ({"pos", "posc", "center"} & d.keys()) for d in plain.values())
    lay = dot_layouts(G, s)
    full = {e["data"]["id"]: e["data"] for e in elements(G, s, lay["expanded"], layouts=lay) if "source" not in e["data"]}
    assert full["b"]["pos"] == lay["expanded"]["b"] and "posc" not in full["b"]
    assert full["grp"]["posc"] == lay["collapsed"]["grp"] and full["grp"]["center"] == lay["centers"]["grp"] and "pos" not in full["grp"]


# ---- the script itself -----------------------------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which("node"), reason="Node not installed")
def test_the_pages_javascript_is_valid(tmp_path):
    for s in (style(), style(secondary_hidden=True, groups_collapsed=True), Style()):
        f = tmp_path / "page.js"
        f.write_text(script_of(cytoscape_html(workflow(), s)), encoding="utf-8")
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


# ---- behaviour in a real browser ---------------------------------------------------------------------------------

SCENARIO = """<script>
const out = [];
const snap = label => out.push({label, nodes: cy.nodes().length,
  shown: cy.edges().filter(e => e.style('display') !== 'none').length, all: cy.edges().length,
  collapsed: cy.nodes('.collapsed').map(n => n.id()), faded: cy.elements('.faded').length,
  text: cy.getElementById('grp').data('text'), checked: document.getElementById('showdata').checked});
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  snap('initial');
  cy.getElementById('a').emit('mouseover'); snap('hover a'); cy.getElementById('a').emit('mouseout'); snap('after hover');
  cy.getElementById('grp').emit('tap'); await wait(600); snap('expanded');
  cy.getElementById('grp').emit('dbltap'); await wait(600); snap('collapsed again');
  const box = document.getElementById('showdata'); box.checked = true; box.onchange(); snap('data on');
  document.getElementById('expandall').onclick(); await wait(600); snap('expand all');
  document.getElementById('collapseall').onclick(); await wait(600); snap('collapse all');
  box.checked = false; box.onchange(); snap('data off');
  document.body.insertAdjacentHTML('beforeend', '<pre id="res">' + JSON.stringify(out) + '</pre>');
})();
</script>"""


def run_in_chrome(page: str, tmp_path) -> list[dict]:
    f = tmp_path / "p.html"
    f.write_text(page.replace("</body>", SCENARIO + "</body>"), encoding="utf-8")
    r = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=20000",
                        "--dump-dom", f"file://{f}"], capture_output=True, text=True, timeout=120)
    m = re.search(r'<pre id="res">(\[.*?\])</pre>', r.stdout, re.S)       # the array, not the scenario's own source text
    if not m:
        pytest.skip("Chrome did not run the scenario in this environment")
    return json.loads(htmllib.unescape(m.group(1)))


@pytest.mark.skipif(not CHROME, reason="no Chrome / Chromium installed")
def test_the_page_starts_collapsed_with_data_edges_hidden_and_responds(tmp_path):
    rows = {r["label"]: r for r in run_in_chrome(cytoscape_html(workflow(), style(secondary_hidden=True, groups_collapsed=True)), tmp_path)}
    first = rows["initial"]
    assert first["nodes"] == 4 and first["collapsed"] == ["grp"] and first["text"] == "grp\n2 nodes"   # s, a, grp, e: the loop is one box
    assert first["all"] == 5 and first["shown"] == 3 and first["checked"] is False                    # the 3 control edges; data edges hidden
    assert rows["hover a"]["shown"] == 5 and rows["hover a"]["faded"] > 0                              # a's two data edges appear, the rest fades
    assert rows["after hover"]["shown"] == 3 and rows["after hover"]["faded"] == 0                     # back to the first view
    assert rows["expanded"]["nodes"] == 6 and rows["expanded"]["collapsed"] == []                      # a click opens the group
    assert rows["collapsed again"]["collapsed"] == ["grp"] and rows["collapsed again"]["nodes"] == 4  # a double click closes it
    assert rows["data on"]["shown"] == rows["data on"]["all"] == 5 and rows["data on"]["checked"] is True
    assert rows["expand all"]["nodes"] == 6 and rows["expand all"]["shown"] == rows["expand all"]["all"] == 7
    assert rows["collapse all"]["collapsed"] == ["grp"]
    assert rows["data off"]["shown"] < rows["data off"]["all"]


@pytest.mark.skipif(not CHROME, reason="no Chrome / Chromium installed")
def test_the_default_style_starts_expanded_with_everything_shown(tmp_path):
    first = run_in_chrome(cytoscape_html(workflow(), style()), tmp_path)[0]
    assert first["nodes"] == 6 and first["collapsed"] == [] and first["shown"] == first["all"] == 7 and first["checked"] is True
