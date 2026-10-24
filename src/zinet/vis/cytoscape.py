"""The interactive page: one self-contained HTML file (Cytoscape.js is bundled, so it works offline)."""
from __future__ import annotations

import html
import json
from importlib import resources
from pathlib import Path

import networkx as nx

from .dot import dot_layouts, groups_of
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
  label{font-size:15px;cursor:pointer;white-space:nowrap}
  pre{white-space:pre-wrap;word-break:break-word;margin:4px 0}
  .hint{opacity:.65;font-size:14px}
  @media (prefers-color-scheme: dark){html,body{background:#16181d;color:#e6e6e6}#bar,#side{border-color:#333}input,select{font-size:15px;background:#222;color:#eee;border:1px solid #444}}
</style></head><body>
<div id="bar"><b>__TITLE__</b><input id="q" placeholder="find a node" size="18" style="font-size:15px">
 <select id="layout" style="font-size:15px">__LAYOUTS__</select>
 <button id="zin" title="Zoom in">+</button><button id="zout" title="Zoom out">&minus;</button><button id="zfit" title="Fit the whole graph">Fit</button><button id="reset" title="Clear the selection, the highlight and the search">Reset</button>
 __CONTROLS__
 <span>__LEGEND__</span><span style="opacity:.7">__NOTE__</span></div>
<div id="cy"></div><div id="side"><i>Hover a node to see its connections; click it for details.</i></div>
<script>__CYTOSCAPE__</script>
<script>
const data = __DATA__;
const OPTS = __OPTS__;
const dark = matchMedia('(prefers-color-scheme: dark)').matches;
const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const cy = cytoscape({container: document.getElementById('cy'), elements: data, layout: {name: 'preset'}, wheelSensitivity: 0.08, minZoom: 0.05, maxZoom: 4,
  style: [
    {selector:'node', style:{'background-color':'data(color)', 'background-opacity':0.85, shape:'data(shape)', label:'data(text)',
      'text-wrap':'wrap', 'text-max-width':118, 'font-size':13, 'min-zoomed-font-size':5, width:130, height:48, color:'#111',
      'text-valign':'center', 'text-halign':'center', 'border-width':1, 'border-color':'data(color)'}},
    {selector:'node[shape="diamond"]', style:{width:150, height:70}},
    {selector:'node[?sized]', style:{width:'data(size)', height:'data(size)', 'background-opacity':1, 'border-width':0,
      color: dark?'#ddd':'#333', 'text-valign':'bottom', 'text-halign':'center', 'text-margin-y':3, 'min-zoomed-font-size':8}},
    {selector:':parent', style:{'background-opacity':0.07, 'border-style':'dashed', 'border-width':2, 'text-valign':'top',
      'text-halign':'center', 'padding':20, shape:'round-rectangle', color: dark?'#ddd':'#333', 'font-weight':'bold'}},
    {selector:'node.collapsed', style:{'background-opacity':0.35, 'border-style':'dashed', 'border-width':3, shape:'round-rectangle',
      width:170, height:58, 'font-weight':'bold', color: dark?'#ddd':'#222'}},
    {selector:'edge', style:{width:2, 'line-color':'#6b7280', 'target-arrow-color':'#6b7280', 'target-arrow-shape':'triangle',
      'curve-style':'bezier', label:'data(label)', 'font-size':11, color: dark?'#bbb':'#555',
      'text-background-color': dark?'#16181d':'#fff', 'text-background-opacity':0.9, 'text-background-padding':2}},
    {selector:'edge[?dashed]', style:{'line-style':'dashed', width:1.5, 'line-color':'#4f8ef7', 'target-arrow-color':'#4f8ef7'}},
    {selector:'edge.off', style:{display:'none'}},
    {selector:'.faded', style:{opacity:0.12}},
    {selector:'node[mark]', style:{'border-width':4, 'border-color':'#e5484d'}},
    {selector:'node:selected', style:{'border-width':4, 'border-color':'#e5484d'}}]});

// ---- state ------------------------------------------------------------------------------------------------------
let selected = null, hover = null, term = '';
let showData = !OPTS.dataHidden;                      // dashed edges (data wiring) are shown, or only for the node in focus
const store = {};                                     // collapsed group id -> its removed members (and their edges)
const GROUPS = cy.nodes().filter(n => n.isParent()).map(n => n.id());
const live = n => n && cy.getElementById(n.id()).length > 0;

function refresh(){
  const f = live(selected) ? selected : (live(hover) ? hover : null);
  cy.elements().removeClass('faded');
  cy.edges('[?dashed]').toggleClass('off', !showData);
  if (f) {                                            // the node in focus: its connections stand out, data edges included
    const nb = f.closedNeighborhood();
    nb.edges('[?dashed]').removeClass('off');
    cy.elements().not(nb).addClass('faded');
  } else if (term) {
    const hit = cy.nodes().filter(n => n.data('label').toLowerCase().includes(term));
    cy.elements().not(hit).addClass('faded');
  }
}

// ---- layout -----------------------------------------------------------------------------------------------------
const isDot = () => document.getElementById('layout').value === 'dot';
function layout(){
  if (isDot()) {
    cy.nodes().forEach(n => { if (n.data('pos') && !store[n.id()]) n.position(n.data('pos')); });
    applyPositions(false);
    return;
  }
  const l = cy.layout({name: document.getElementById('layout').value, animate:false, padding:30, directed:true, spacingFactor:1.25,
                       nodeRepulsion: 9000, nodeDimensionsIncludeLabels:true, fit:true});
  l.on('layoutstop', () => cy.fit(undefined, 30));
  l.run(); cy.fit(undefined, 30);
}
function applyPositions(animate){                     // the precomputed dot layouts: compact when every group is collapsed
  if (!isDot()) { cy.fit(undefined, 30); return; }
  const allCollapsed = GROUPS.length > 0 && GROUPS.every(id => store[id]);
  cy.nodes().forEach(n => {
    const p = allCollapsed && n.data('posc') ? n.data('posc') : (store[n.id()] ? n.data('center') : n.data('pos'));
    if (!p) return;
    if (animate) n.animate({position: p}, {duration: 250}); else n.position(p);
  });
  if (animate) setTimeout(() => cy.animate({fit: {padding: 30}}, {duration: 250}), 270); else cy.fit(undefined, 30);
}

// ---- collapsing groups ------------------------------------------------------------------------------------------
function collapse(g){
  if (store[g.id()] || !g.isParent()) return;
  const kids = g.descendants(), bb = kids.boundingBox();
  const at = g.data('center') || {x: (bb.x1 + bb.x2) / 2, y: (bb.y1 + bb.y2) / 2};
  g.data('text', g.data('label') + '\\n' + kids.nodes().length + ' nodes');
  store[g.id()] = kids.remove();
  g.addClass('collapsed'); g.position(at);
  if (selected && !live(selected)) selected = null;
}
function expand(g){
  if (!store[g.id()]) return;
  store[g.id()].restore(); delete store[g.id()];
  g.removeClass('collapsed'); g.data('text', g.data('label'));
}
function setAll(collapseThem){
  GROUPS.forEach(id => { const g = cy.getElementById(id); collapseThem ? collapse(g) : expand(g); });
  applyPositions(true); refresh();
}

// ---- events -----------------------------------------------------------------------------------------------------
function describe(n){
  const d = n.data();
  const other = x => (x.source().id()===n.id() ? x.target() : x.source()).data('label');
  const rows = n.connectedEdges().map(x => (x.source().id()===n.id() ? '→ ' : '← ') + esc(x.data('relation')) + ' ' +
    esc(other(x)) + (x.data('info') ? '  (' + esc(x.data('info')) + ')' : '')).sort();
  const hint = store[n.id()] ? '<div class="hint">Click it again to expand.</div>' : (n.isParent() ? '<div class="hint">Double-click to collapse.</div>' : '');
  document.getElementById('side').innerHTML = '<b>' + esc(d.label) + '</b><pre>' + esc(d.info) + '</pre>' + hint +
    '<b>Links</b><pre>' + rows.join('\\n') + '</pre>';
}
cy.on('mouseover', 'node', e => { hover = e.target; refresh(); });
cy.on('mouseout', 'node', () => { hover = null; refresh(); });
cy.on('tap', 'node', e => {
  const n = e.target;
  if (store[n.id()]) { expand(n); applyPositions(true); }          // a collapsed box opens on a click
  selected = n; describe(n); refresh();
});
cy.on('dbltap', 'node', e => {                                    // an open group closes on a double click
  const n = e.target;
  if (n.isParent()) { collapse(n); applyPositions(true); refresh(); describe(n); }
});
cy.on('tap', e => { if (e.target === cy) { selected = null; refresh(); } });
document.getElementById('q').oninput = e => {
  term = e.target.value.toLowerCase(); refresh();
  const hit = term ? cy.nodes().filter(n => n.data('label').toLowerCase().includes(term)) : null;
  if (hit && hit.length) cy.fit(hit, 60);
};
document.getElementById('layout').onchange = layout;
window.addEventListener('resize', () => cy.fit(undefined, 30));
function zoomBy(f){ cy.zoom({level: cy.zoom() * f, renderedPosition: {x: cy.width() / 2, y: cy.height() / 2}}); }
document.getElementById('zin').onclick = () => zoomBy(1.3);
document.getElementById('zout').onclick = () => zoomBy(1 / 1.3);
document.getElementById('zfit').onclick = () => cy.fit(undefined, 30);
document.getElementById('reset').onclick = () => {
  selected = hover = null; term = ''; document.getElementById('q').value = '';
  document.getElementById('side').innerHTML = '<i>Hover a node to see its connections; click it for details.</i>';
  refresh(); cy.fit(undefined, 30);
};
const dataBox = document.getElementById('showdata');
if (dataBox) dataBox.onchange = () => { showData = dataBox.checked; refresh(); };
const collapseAll = document.getElementById('collapseall'), expandAll = document.getElementById('expandall');
if (collapseAll) collapseAll.onclick = () => setAll(true);
if (expandAll) expandAll.onclick = () => setAll(false);

layout();
if (OPTS.collapsed && GROUPS.length) setAll(true); else refresh();
</script></body></html>
"""


def _legend(G: nx.Graph, style: Style) -> str:
    boxes = "".join(f'<span class="sw" style="background:{c}"></span>{html.escape(k)}' for k, c in style.legend(G))
    lines = "".join(f'<span class="ln{" d" if dashed else ""}"></span>{html.escape(name)}' for name, dashed in style.edge_legend)
    return boxes + lines


def _controls(style: Style, has_dashed: bool, has_groups: bool, hidden: bool) -> str:
    """The toolbar parts that only make sense when the graph has dashed edges or groups."""
    out = ""
    if has_dashed:
        name = next((n for n, dashed in style.edge_legend if dashed), "dashed")
        out += (f'<label title="Dashed edges are always shown for the node you hover or select">'
                f'<input type="checkbox" id="showdata"{"" if hidden else " checked"}> show {html.escape(name)} edges</label>')
    if has_groups:
        out += ('<button id="collapseall" title="Collapse every group to one box">Collapse groups</button>'
                '<button id="expandall" title="Open every group">Expand groups</button>')
    return out


def elements(G: nx.Graph, style: Style, positions: dict | None = None, mark: set[str] | None = None,
             layouts: dict | None = None) -> list[dict]:
    """The Cytoscape element list for G. `positions` (id -> {x, y}) is optional; nodes without one are placed by a layout.
    Nodes in `mark` get a red ring (the node a view is about). `layouts` (from `dot_layouts`) adds the data the page needs to
    switch between the expanded and the collapsed arrangement: `pos`, `posc` (collapsed) and, for a group, `center`."""
    members = groups_of(G, style)
    out = []
    for n, d in G.nodes(data=True):
        label, kind = style.label(n, d), style.kind(n, d)
        sized = style.node_size is not None
        data = {"id": n, "label": label, "text": label if (sized or n in members or not kind or not style.show_kind) else f"{label}\n{kind}",
                "color": style.color(n, d), "info": style.info(n, d), "shape": style.shape(n, d)}
        if sized:
            data["sized"], data["size"] = True, style.node_size(G, n, d)
        if mark and n in mark:
            data["mark"] = 1
        if style.group(n, d) is not None:
            data["parent"] = style.group(n, d)
        for key, source in (("pos", "expanded"), ("posc", "collapsed"), ("center", "centers")):
            if layouts and n in layouts.get(source, {}):
                data[key] = layouts[source][n]
        el = {"data": data}
        if positions and n in positions:
            el = {"position": positions[n], **el}
        out.append(el)
    for i, (u, v, d) in enumerate(G.edges(data=True)):
        out.append({"data": {"id": f"e{i}", "source": u, "target": v, "relation": style.edge_kind(u, v, d),
                             "label": style.edge_label(u, v, d), "dashed": bool(style.edge_dashed(u, v, d)),
                             "info": style.edge_info(u, v, d)}})
    return out


def cytoscape_html(G: nx.Graph, style: Style, note: str = "", mark: set[str] | None = None) -> str:
    """The self-contained page for G. In the "flow" arrangement the node positions come from `dot` when it is installed (it
    lays out clusters properly); in the "force" arrangement a force layout places the nodes. `mark` ids get a red ring."""
    placed = dot_layouts(G, style) if style.arrangement == "flow" else {}
    pos = placed.get("expanded", {})
    layouts = (["dot"] if pos else []) + ["cose", "breadthfirst", "concentric", "circle", "grid"]
    has_groups = bool(groups_of(G, style))
    dashed = [(u, v) for u, v, d in G.edges(data=True) if style.edge_dashed(u, v, d)]
    opts = {"dataHidden": bool(style.secondary_hidden and dashed), "collapsed": bool(style.groups_collapsed and has_groups)}
    js = (resources.files("zinet.vis") / "data" / "cytoscape.min.js").read_text(encoding="utf-8")
    return (CYTOSCAPE_PAGE.replace("__TITLE__", html.escape(style.title)).replace("__NOTE__", html.escape(note))
            .replace("__CONTROLS__", _controls(style, bool(dashed), has_groups, opts["dataHidden"]))
            .replace("__OPTS__", json.dumps(opts))
            .replace("__LEGEND__", _legend(G, style))
            .replace("__LAYOUTS__", "".join(f"<option>{l}</option>" for l in layouts))
            .replace("__DATA__", json.dumps(elements(G, style, pos, mark, placed)).replace("</", "<\\/"))
            .replace("__CYTOSCAPE__", js.replace("</script", "<\\/script")))


def to_cytoscape(G: nx.Graph, out: Path, style: Style, note: str = "") -> None:
    out.write_text(cytoscape_html(G, style, note), encoding="utf-8")
