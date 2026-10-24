"""Comment-preserving YAML: harvest, attach, prettify, and the SQLite-backed YAML <-> JSON round trip."""
import json
import sqlite3
from pathlib import Path

import pytest

from zinet import load_graph
from zinet.cli import main
from zinet.roundtrip import (
    GRAPH_YAML,
    CommentStore,
    Layout,
    attach,
    default_store_path,
    file_key,
    format_keeping_comments,
    harvest,
    json_to_yaml,
    yaml_to_json,
)

GOLDEN = json.loads((Path(__file__).parent / "characterization" / "golden" / "workgraph_roundtrip.json").read_text(encoding="utf-8"))["cases"]

COMMENTED = """# header of the file
version: '1.0'
imports:
  - ./shared.yaml   # tools we reuse
# the leaves
primitives:
  # a unit of work
  - id: units   # trailing on the id line
    label: "Units # not a comment"
  - id: limit
concepts:
  - id: capacity
    deps:
      # why units
      - units   # required
      - limit
    meta:
      # inside meta
      expression: x <= y   # the rule
applications:
  - id: plan
    deps:
      - capacity
"""


# ---- the generalized code reproduces work-graph's frozen behaviour ---------------------------------------------

WORKGRAPH = Layout(("nodes", "edges"), lambda section, item: (
    f"{item.get('source')}|{item.get('relation')}|{item.get('target')}" if section == "edges" else str(item.get("id"))))


# ---- anchors -------------------------------------------------------------------------------------------------------

def anchors(text):
    return [(c["item_key"], c["key"], c["position"], c["text"]) for c in harvest(text)]


def test_harvest_pins_each_comment_to_a_node_a_key_or_a_section():
    got = anchors(COMMENTED)
    assert ("@file", None, "before", "header of the file") in got                    # the file header stays on top
    assert ("@section:imports", None, "trailing", "tools we reuse") in got        # a section that is not a list of nodes
    assert ("@section:primitives", None, "before", "the leaves") in got
    assert ("units", None, "before", "a unit of work") in got
    assert ("units", None, "trailing", "trailing on the id line") in got
    assert ("capacity", "deps[0]", "before", "why units") in got                    # an entry of a block list: deps[0], deps[1], ...
    assert ("capacity", "deps[0]", "trailing", "required") in got
    assert ("capacity", "meta", "before", "inside meta") in got
    assert ("capacity", "expression", "trailing", "the rule") not in got            # nested keys are part of `meta`
    assert ("capacity", "meta", "trailing", "the rule") in got
    assert all("not a comment" not in c[3] for c in got)                             # a '#' inside quotes is data


def test_attach_puts_comments_back_into_canonical_yaml():
    graph = load_graph_from_text(COMMENTED)
    merged, preserved = format_keeping_comments(COMMENTED, graph)
    assert preserved
    assert merged.startswith("# header of the file\nversion: '1.0'")
    assert "- id: units  # trailing on the id line" in merged and "# a unit of work" in merged
    assert harvest(merged) == harvest(COMMENTED)                                     # every comment, in order, same anchor
    again, preserved2 = format_keeping_comments(merged, load_graph_from_text(merged))
    assert preserved2 and again == merged                                            # its own output is stable


def load_graph_from_text(text):
    import tempfile
    f = Path(tempfile.mkdtemp()) / "g.yaml"
    f.write_text(text)
    return load_graph(f, resolve_imports=False)


def test_a_removed_node_orphans_its_comments_and_they_come_back_with_it():
    text = "primitives:\n  # about a\n  - id: a   # a trailing\n  - id: b\n"
    comments = harvest(text)
    without_a, orphans = attach("primitives:\n  - id: b\n", comments)
    assert len(orphans) == 2 and without_a.endswith("# [orphaned from a] about a\n# [orphaned from a] a trailing\n")
    with_a_again, orphans2 = attach("primitives:\n  - id: a\n  - id: b\n", harvest(without_a))
    # restored comments come back above the node (the orphan marker does not record "trailing")
    assert orphans2 == [] and "primitives:\n  # about a\n  # a trailing\n  - id: a\n" in with_a_again


def test_no_comments_means_no_change():
    plain = "version: '1.0'\nprimitives:\n  - id: a\n"
    assert attach(plain, [])[0] == plain and harvest(plain) == []


# ---- work-graph's layout: the same code, other sections --------------------------------------------------------

def test_the_workgraph_layout_reproduces_its_golden_comments():
    case = GOLDEN["with_comments"]
    import importlib.util
    spec = importlib.util.spec_from_file_location("roundtrip_cases", Path(__file__).parent / "characterization" / "roundtrip_cases.py")
    cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cases)
    WITH_COMMENTS = cases.WITH_COMMENTS
    assert harvest(WITH_COMMENTS, WORKGRAPH) == case["harvest"]
    text, orphans = attach(case["dump_yaml"], case["harvest"], WORKGRAPH)
    assert text == case["round_trip_text"] and orphans == case["round_trip_orphans"]
    assert harvest(text, WORKGRAPH) == case["harvest"] and case["harvest_is_stable"]
    assert len(case["after_removing_b"]["orphans"]) == 3 and "[orphaned from b]" in case["after_removing_b"]["text"]


# ---- prettify and convert --------------------------------------------------------------------------------------------

def test_prettify_write_keeps_the_comments(tmp_path):
    source = tmp_path / "g.yaml"
    source.write_text(COMMENTED)
    assert main(["prettify", str(source), "--write"]) == 0
    assert harvest(source.read_text()) == harvest(COMMENTED)
    assert load_graph(source, resolve_imports=False).index().keys() == {"units", "limit", "capacity", "plan"}


def test_yaml_to_json_and_back_keeps_comments_in_the_store(tmp_path):
    y = tmp_path / "g.yaml"
    y.write_text(COMMENTED)
    j, y2 = tmp_path / "g.json", tmp_path / "out.yaml"
    with CommentStore(tmp_path / "c.db") as store:
        assert yaml_to_json(y, j, store) == {"comments": len(harvest(COMMENTED))}
        data = json.loads(j.read_text())
        assert data["version"] == "1.0" and [n["id"] for n in data["primitives"]] == ["units", "limit"] and "#" not in j.read_text().replace('"Units # not a comment"', "")
        assert store.registered(y.with_suffix("")) is not None
        j.rename(tmp_path / "moved.json")                       # the store is keyed by name, so a copy next to the YAML works
        (tmp_path / "moved.json").rename(j)
        info = json_to_yaml(j, y2, store)
    assert info["orphans"] == 0 and info["comments"] == len(harvest(COMMENTED))
    assert harvest(y2.read_text()) == harvest(COMMENTED)
    assert load_graph(y2, resolve_imports=False) == load_graph(y, resolve_imports=False)


def test_comments_added_to_the_yaml_since_the_last_convert_are_kept(tmp_path):
    y, j = tmp_path / "g.yaml", tmp_path / "g.json"
    y.write_text("primitives:\n  - id: a   # first\n")
    with CommentStore(tmp_path / "c.db") as store:
        yaml_to_json(y, j, store)
        json_to_yaml(j, y, store)                               # writes the YAML back
        y.write_text(y.read_text().replace("# first", "# first\n  - id: b  # added by hand"))
        info = json_to_yaml(j, y, store)                        # the JSON does not have b; its comment is orphaned, not lost
    assert info["orphans"] == 1 and "# [orphaned from b] added by hand" in y.read_text() and "# first" in y.read_text()


def test_convert_cli_both_directions_and_errors(tmp_path, capsys):
    y = tmp_path / "g.yaml"
    y.write_text("primitives:\n  - id: a  # keep\nconcepts:\n  - id: c\n    deps: [a]\n")
    store = str(tmp_path / "s.db")
    assert main(["convert", str(y), "--store", store]) == 0
    assert "(1 comment(s) kept" in capsys.readouterr().out and (tmp_path / "g.json").exists()
    y.unlink()
    assert main(["convert", str(tmp_path / "g.json"), "--store", store]) == 0
    assert "- id: a  # keep" in y.read_text()
    assert main(["convert", str(tmp_path / "notes.txt"), "--store", store]) == 2


def test_store_location_and_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("ZINET_HOME", str(tmp_path / "home"))
    assert default_store_path() == tmp_path / "home" / "comments.db"
    assert file_key(tmp_path / "g.yaml") == file_key(tmp_path / "g.json") == str(tmp_path.resolve() / "g")
    with CommentStore() as store:
        store.replace_comments("f", [{"item_key": "a", "key": None, "position": "before", "text": "x"}])
        assert store.comments("f") == [{"item_key": "a", "key": None, "position": "before", "text": "x"}]
    assert sqlite3.connect(tmp_path / "home" / "comments.db").execute("SELECT COUNT(*) FROM comments").fetchone() == (1,)


def test_a_comment_on_a_dependency_stays_on_that_dependency():
    text = "concepts:\n  - id: c\n    deps:\n      - a   # needs a\n      - b   # and b\n      - d\n"
    out, orphans = attach(text.replace("   # needs a", "").replace("   # and b", ""), harvest(text))
    assert orphans == [] and "      - a  # needs a\n      - b  # and b\n      - d\n" in out


def test_a_dependency_comment_falls_back_to_the_key_when_the_entry_is_gone():
    comments = harvest("concepts:\n  - id: c\n    deps:\n      - a\n      - b   # about b\n")
    out, orphans = attach("concepts:\n  - id: c\n    deps:\n      - a\n", comments)      # deps[1] no longer exists
    assert orphans == [] and "    deps:  # about b\n" in out
