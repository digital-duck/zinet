"""Characterize work-graph's convert.py (comment-preserving YAML round-trip) on the texts in roundtrip_cases.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from roundtrip_cases import CASES


def build(sources_dir: Path, here: Path) -> dict[Path, str]:
    sys.path.insert(0, str(sources_dir / "work-graph" / "src"))
    from workgraph import convert

    out: dict[str, Any] = {}
    safe = YAML(typ="safe")
    for name, text in CASES.items():
        doc = convert._plain(safe.load(text))
        comments = convert.harvest(text)
        rewritten, orphans = convert.attach(convert.dump_yaml(doc), comments)
        again = convert.harvest(rewritten)
        entry: dict[str, Any] = {
            "harvest": comments,
            "dump_yaml": convert.dump_yaml(doc),
            "round_trip_text": rewritten,
            "round_trip_orphans": orphans,
            "harvest_is_stable": again == comments,
        }
        # delete node b from the document, then re-attach: its comments become orphans, written as a trailing block
        trimmed = {**doc, "nodes": [n for n in doc.get("nodes", []) if n.get("id") != "b"],
                   "edges": [e for e in doc.get("edges", []) if e.get("target") != "b"]}
        text2, orphans2 = convert.attach(convert.dump_yaml(trimmed), comments)
        entry["after_removing_b"] = {"text": text2, "orphans": orphans2, "harvest": convert.harvest(text2)}
        out[name] = entry
    meta = {"_source": "work-graph@" + _commit(sources_dir / "work-graph")}
    return {here / "golden" / "workgraph_roundtrip.json": json.dumps({**meta, "cases": out}, indent=1, sort_keys=True) + "\n"}


def _commit(repo: Path) -> str:
    import subprocess
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or "unknown"
