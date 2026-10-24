"""The interactive page: one self-contained HTML file (Cytoscape.js is bundled, so it works offline)."""
from __future__ import annotations

import html
import json
from importlib import resources
from pathlib import Path

import networkx as nx

from .dot import dot_positions, groups_of
from .style import Style

CYTOSCAPE_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
  html,body{margin:0;height:100%;font:16px system-ui,sans-serif;background:#fff;color:#222}
  #bar{display:flex;gap:12px;align-items:center;padding:8px 12px;min-height:34px;border-bottom:1px solid #ddd;flex-wrap:wrap}
  #cy{position:absolute;top:52px;bottom:0;left:0;right:340px}
  #side{position:absolute;top:52px;bottom:0;right:0;width:340px;font-size:15px;overflow:auto;border-left:1px solid #ddd;padding:8px;box-sizing:border-box}
  .sw{display:inline-block;width:12px;height:12px;border-radius:3px;margin:0 3px 0 8px}
  .ln{display:inline-block;width:22px;border-top:2px solid #6b7280;vertical-align:middle;margin:0 3px 0 8px}
  .ln.d{border-top-style:dashed;border-color:#4f8ef7}
  button{font-size:15px;min-width:34px;padding:2px 8px;cursor:pointer}
  pre{white-space:pre-wrap;word-break:break-word;margin:4px 0}
  @media (prefers-color-scheme: dark){html,body{background:#16181d;color:#e6e6e6}#bar,#side{border-color:#333}input,select{font-size:15px;background:#222;color:#eee;border:1px solid #444}}
</style></head><body>
<div id="bar"><b>__TITLE__</b><input id="q" placeholder="find a node" size="18" style="font-size:15px">
 <select id="layout" style="font-size:15px">__LAYOUTS__</select>
 <button id="zin" title="Zoom in">+</button><button id="zout" title="Zoom out">&minus;</button><button id="zfit" title="Fit the whole graph">Fit</button><button id="reset" title="Clear the selection, the highlight and the search">Reset</button>
 <span>__LEGEND__</span><span style="opacity:.7">__NOTE__</span></div>
<div id="cy"></div><div id="side"><i>Click a node.</i></div>
<script>__CYTOSCAPE__</script>
<script>
const data = __DATA__;
const dark = matchMedia('(prefers-color-scheme: dark)').matches;
const cy = cytoscape({container: document.getElementById('cy'), elements: data, layout: {name: 'preset'}, wheelSensitivity: 0.08, minZoom: 0.05, maxZoom: 4,
  style: [
    {selector:'node', style:{'background-color':'data(color)', 'background-opacity':0.85, shape:'data(shape)', label:'data(text)',
      'text-wrap':'wrap', 'font-size':13, 'min-zoomed-font-size':5, width:130, height:48, color:'#111',
      'text-valign':'center', 'text-halign':'center', 'border-width':1, 'border-color':'data(color)'}},
    {selector:'node[shape="diamond"]', style:{width:150, height:70}},
    {selector:':parent', style:{'background-opacity':0.07, 'border-style':'dashed', 'border-width':2, 'text-valign':'top',
      'text-halign':'center', 'padding':20, shape:'round-rectangle', color: dark?'#ddd':'#333', 'font-weight':'bold'}},
    {selector:'edge', style:{width:2, 'line-color':'#6b7280', 'target-arrow-color':'#6b7280', 'target-arrow-shape':'triangle',
      'curve-style':'bezier', label:'data(label)', 'font-size':11, color: dark?'#bbb':'#555',
      'text-background-color': dark?'#16181d':'#fff', 'text-background-opacity':0.9, 'text-background-padding':2}},
    {selector:'edge[?dashed]', style:{'line-style':'dashed', width:1.5, 'line-color':'#4f8ef7', 'target-arrow-color':'#4f8ef7'}},
    {selector:'.faded', style:{opacity:0.12}},
    {selector:'node:selected', style:{'border-width':4, 'border-color':'#e5484d'}}]});
function layout(){
  const name = document.getElementById('layout').value === 'dot' ? 'preset' : document.getElementById('layout').value;
  const l = cy.layout({name, animate:false, padding:30, directed:true, spacingFactor:1.25, nodeRepulsion: 9000,
                       nodeDimensionsIncludeLabels:true, fit:true});
  l.on('layoutstop', () => cy.fit(undefined, 30));
  l.run(); cy.fit(undefined, 30);
}
layout();
window.addEventListener('resize', () => cy.fit(undefined, 30));
document.getElementById('layout').onchange = layout;
function zoomBy(f){ cy.zoom({level: cy.zoom() * f, renderedPosition: {x: cy.width() / 2, y: cy.height() / 2}}); }
document.getElementById('zin').onclick = () => zoomBy(1.3);
document.getElementById('zout').onclick = () => zoomBy(1 / 1.3);
document.getElementById('zfit').onclick = () => cy.fit(undefined, 30);
document.getElementById('reset').onclick = () => {
  cy.elements().unselect().removeClass('faded');
  document.getElementById('q').value = '';
  document.getElementById('side').innerHTML = '<i>Click a node.</i>';
};
cy.on('tap','node', e => {
  const n = e.target, nb = n.closedNeighborhood();
  cy.elements().addClass('faded'); nb.removeClass('faded');
  const d = n.data(), esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  const other = x => (x.source().id()===n.id() ? x.target() : x.source()).data('label');
  const rows = n.connectedEdges().map(x => (x.source().id()===n.id() ? '→ ' : '← ') + esc(x.data('relation')) + ' ' +
    esc(other(x)) + (x.data('info') ? '  (' + esc(x.data('info')) + ')' : '')).sort();
  document.getElementById('side').innerHTML = '<b>' + esc(d.label) + '</b><pre>' + esc(d.info) + '</pre><b>Links</b><pre>' + rows.join('\\n') + '</pre>';
});
cy.on('tap', e => { if (e.target === cy) { cy.elements().removeClass('faded'); } });
document.getElementById('q').oninput = e => {
  const t = e.target.value.toLowerCase(); cy.elements().removeClass('faded');
  if (!t) return;
  const hit = cy.nodes().filter(n => n.data('label').toLowerCase().includes(t));
  cy.elements().not(hit).addClass('faded'); if (hit.length) cy.fit(hit, 60);
};
</script></body></html>
"""


def _legend(G: nx.Graph, style: Style) -> str:
    boxes = "".join(f'<span class="sw" style="background:{c}"></span>{html.escape(k)}' for k, c in style.legend(G))
    lines = "".join(f'<span class="ln{" d" if dashed else ""}"></span>{html.escape(name)}' for name, dashed in style.edge_legend)
    return boxes + lines


def elements(G: nx.Graph, style: Style, positions: dict | None = None) -> list[dict]:
    """The Cytoscape element list for G. `positions` (id -> {x, y}) is optional; nodes without one are placed by a layout."""
    members = groups_of(G, style)
    out = []
    for n, d in G.nodes(data=True):
        label, kind = style.label(n, d), style.kind(n, d)
        data = {"id": n, "label": label, "text": label if (n in members or not kind) else f"{label}\n{kind}",
                "color": style.color(n, d), "info": style.info(n, d), "shape": style.shape(n, d)}
        if style.group(n, d) is not None:
            data["parent"] = style.group(n, d)
        el = {"data": data}
        if positions and n in positions:
            el = {"position": positions[n], **el}
        out.append(el)
    for i, (u, v, d) in enumerate(G.edges(data=True)):
        out.append({"data": {"id": f"e{i}", "source": u, "target": v, "relation": style.edge_kind(u, v, d),
                             "label": style.edge_label(u, v, d), "dashed": bool(style.edge_dashed(u, v, d)),
                             "info": style.edge_info(u, v, d)}})
    return out


def cytoscape_html(G: nx.Graph, style: Style, note: str = "") -> str:
    """The self-contained page for G. Node positions come from `dot` when it is installed (it lays out clusters properly)."""
    pos = dot_positions(G, style)
    layouts = (["dot"] if pos else []) + ["cose", "breadthfirst", "concentric", "circle", "grid"]
    js = (resources.files("zinet.vis") / "data" / "cytoscape.min.js").read_text(encoding="utf-8")
    return (CYTOSCAPE_PAGE.replace("__TITLE__", html.escape(style.title)).replace("__NOTE__", html.escape(note))
            .replace("__LEGEND__", _legend(G, style))
            .replace("__LAYOUTS__", "".join(f"<option>{l}</option>" for l in layouts))
            .replace("__DATA__", json.dumps(elements(G, style, pos)).replace("</", "<\\/"))
            .replace("__CYTOSCAPE__", js.replace("</script", "<\\/script")))


def to_cytoscape(G: nx.Graph, out: Path, style: Style, note: str = "") -> None:
    out.write_text(cytoscape_html(G, style, note), encoding="utf-8")
