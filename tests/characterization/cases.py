"""The graphs the characterization run uses. Small on purpose: each case isolates one behaviour.

A case is {name, primitives, nodes: [{id, kind?, deps, optional?}], first_radical?, queries: [{known, target}]}.
`deps` point from a dependency to the node that lists it (the same direction as zinet). `optional` dependencies are
graph-code's `optionally_depends_on` (a mandatory-edge filter in graph-code, ignored by ConceptBook), so a case with
them lists only `graph_code` in `sources`.
"""
from __future__ import annotations

CASES = [
    {   # the plain case: every function agrees on a straight line
        "name": "chain",
        "primitives": ["p"],
        "nodes": [
            {"id": "a", "deps": ["p"]}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["b"]},
            {"id": "z", "kind": "application", "deps": ["c"]},
        ],
        "queries": [
            {"known": [], "target": "z"}, {"known": ["a"], "target": "z"}, {"known": ["a", "b", "c"], "target": "z"},
            {"known": [], "target": "a"}, {"known": ["p"], "target": "b"},
        ],
    },
    {   # two primitives feeding a diamond
        "name": "diamond",
        "primitives": ["p1", "p2"],
        "nodes": [
            {"id": "a", "deps": ["p1", "p2"]}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["a"]},
            {"id": "d", "deps": ["b", "c"]},
        ],
        "queries": [{"known": [], "target": "d"}, {"known": ["b"], "target": "d"}],
    },
    {   # equal reach everywhere, ids declared out of alphabetical order: exposes how ties are broken
        "name": "ties_unsorted",
        "primitives": ["zp", "ap"],
        "nodes": [
            {"id": "zeta", "deps": ["zp"]}, {"id": "alpha", "deps": ["ap"]}, {"id": "mid", "deps": ["zp"]},
            {"id": "beta", "deps": ["ap"]},
            {"id": "omega", "kind": "application", "deps": ["zeta", "alpha"]},
            {"id": "theta", "kind": "application", "deps": ["mid", "beta"]},
        ],
        "queries": [{"known": [], "target": "omega"}, {"known": [], "target": "theta"}],
    },
    {   # one hub concept unlocks many others and some applications: reach and the application weight matter
        "name": "reach_weighting",
        "primitives": ["p"],
        "nodes": [
            {"id": "a", "deps": ["p"]}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["a"]}, {"id": "d", "deps": ["a"]},
            {"id": "e", "deps": ["p"]},
            {"id": "x", "kind": "application", "deps": ["b"]}, {"id": "y", "kind": "application", "deps": ["c", "e"]},
        ],
        "queries": [{"known": [], "target": "y"}, {"known": ["a"], "target": "x"}],
    },
    {   # `ghost` is referenced but never declared (a misspelled or dangling dependency)
        "name": "dangling",
        "primitives": ["p"],
        "nodes": [{"id": "a", "deps": ["p", "ghost"]}, {"id": "b", "deps": ["a"]}],
        "queries": [{"known": [], "target": "b"}],
    },
    {   # `q` is passed as a primitive but the graph has no entry for it: the two ConceptBook `reducible` rules differ here
        "name": "listed_primitive",
        "sources": ["conceptbook"],
        "primitives": ["p"],
        "listed_only": ["q"],
        "nodes": [{"id": "a", "deps": ["p", "q"]}],
        "queries": [{"known": [], "target": "a"}],
    },
    {   # a declared concept with no dependencies: a foundation concept, or a missing link to a primitive?
        "name": "foundation_concept",
        "primitives": ["p"],
        "nodes": [{"id": "root", "deps": []}, {"id": "a", "deps": ["root"]}, {"id": "b", "deps": ["a", "p"]}],
        "queries": [{"known": [], "target": "b"}],
    },
    {   # a loop
        "name": "cycle",
        "primitives": ["p"],
        "nodes": [{"id": "a", "deps": ["p", "c"]}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["b"]}],
        "queries": [{"known": [], "target": "c"}],
    },
    {   # optionally_depends_on is dropped from the mandatory graph by graph-code
        "name": "optional_edges",
        "sources": ["graph_code"],
        "primitives": ["p"],
        "nodes": [{"id": "a", "deps": ["p"]}, {"id": "e", "deps": ["p"]}, {"id": "b", "deps": ["a"], "optional": ["e"]}],
        "queries": [{"known": [], "target": "b"}],
    },
    {   # graph-code's two-radical rule: which primitives a node may rest on
        "name": "first_radical",
        "sources": ["graph_code"],
        "primitives": ["x", "t", "m"],
        "first_radical": ["x", "t"],
        "nodes": [{"id": "v", "deps": ["x", "t"]}, {"id": "a", "deps": ["v", "t"]}, {"id": "p", "deps": ["m", "v"]}],
        "queries": [{"known": [], "target": "p"}, {"known": ["v"], "target": "a"}],
    },
    {   # a concept nobody depends on and that depends on nothing
        "name": "isolated",
        "primitives": ["p"],
        "nodes": [{"id": "a", "deps": ["p"]}, {"id": "lonely", "deps": []}, {"id": "z", "kind": "application", "deps": ["a"]}],
        "queries": [{"known": [], "target": "z"}],
    },
    {   # query edge cases: a primitive as the target, a missing target, a target that is already known
        "name": "query_edges",
        "primitives": ["p"],
        "nodes": [{"id": "a", "deps": ["p"]}, {"id": "b", "deps": ["a"]}],
        "queries": [
            {"known": [], "target": "p"}, {"known": [], "target": "nope"},
            {"known": ["b"], "target": "b"}, {"known": ["a", "b"], "target": "b"},
        ],
    },
]
