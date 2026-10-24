"""Comment-preserving YAML: keep the comments of a graph.yaml when the file is rewritten or converted to JSON and back.

PyYAML drops comments, so they are handled as text. `harvest` reads the comments of a YAML text and pins each one to what
it sits next to: a node (by `id`), a key of that node, or a top-level section. `attach` puts them back into freshly written
YAML (for example the canonical output of `zinet prettify`). A comment whose node no longer exists becomes an "orphan",
written at the end of the file as `# [orphaned from <id>] ...`, and is picked up again if the node comes back.

For the JSON round trip (`zinet convert`), the comments live in a small SQLite database (`CommentStore`, Python's built-in
`sqlite3`) because JSON has no comments: converting YAML to JSON stores them, converting JSON back to YAML re-attaches them.
This is the approach work-graph uses for its layer files; the harvest and attach logic is the same, generalized over a
`Layout` so it fits zinet's three layers (work-graph's `nodes` / `edges` layout is another `Layout`).

Differences from work-graph: a comment on an entry of a block list inside a node (`deps:`) is pinned to that entry (`deps[0]`,
`deps[1]`, ...) and falls back to the key, then to the node, if the entry is gone; a comment on any other line deeper than the
node's own keys is pinned to the key it belongs to; and a comment inside a section that is not a list of nodes (`imports:`) is
pinned to that section instead of the top of the file.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from .io import to_yaml
from .schema import Graph

ITEM_RE = re.compile(r"^(\s*)- ")
KEY_RE = re.compile(r"^\s*(?:- )?([\w.\-]+):(?:\s|$)")
SECTION_RE = re.compile(r"^([\w.\-]+):")
ORPHAN_RE = re.compile(r"^\[orphaned from (.+?)\] (.*)$")


@dataclass(frozen=True)
class Layout:
    """Which top-level keys hold lists of items, and how to name an item (its anchor)."""

    sections: tuple[str, ...]
    item_key: Callable[[str, dict], str]
    file_header: bool = False        # the comment block above the first line belongs to the file, not to the first section


# graph.yaml: the file header stays on top even though `prettify` writes `version` first
GRAPH_YAML = Layout(("primitives", "concepts", "applications"), lambda section, item: str(item.get("id")), file_header=True)


def _split_comment(line: str) -> tuple[str, str | None]:
    """(code part, comment text without '#') for a line; '#' inside quotes does not count."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip(), line[i + 1:].strip()
    return line, None


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _index(lines: list[str], layout: Layout) -> tuple[dict[int, tuple[str, str | None]], dict[str, dict]]:
    """Locate items in YAML text. Returns ({line: (anchor, key)}, {anchor: {"start": line, "keys": {key: line}}}).
    Anchors are the item names from `layout.item_key`, or `@section:<name>` for top-level keys."""
    chunks: list[tuple[str | None, int, int]] = []   # (section, first line, end line) per list item
    section: str | None = None
    indent: int | None = None
    start: int | None = None
    for i, ln in enumerate(lines + ["end:"]):
        code = _split_comment(ln)[0]
        if not code.strip():
            continue
        top = SECTION_RE.match(code)
        if top:
            if start is not None:
                chunks.append((section, start, i))
                start = None
            section, indent = top.group(1), None
            continue
        item = ITEM_RE.match(code)
        if item and section in layout.sections:
            indent = len(item.group(1)) if indent is None else indent
            if len(item.group(1)) == indent:
                if start is not None:
                    chunks.append((section, start, i))
                start = i
    info: dict[int, tuple[str, str | None]] = {}
    where: dict[str, dict] = {}
    covered: set[int] = set()
    for sec, a, b in chunks:
        body = "\n".join(_split_comment(x)[0] for x in lines[a:b]).replace("- ", "  ", 1)
        try:
            data = yaml.safe_load(body)
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        key = layout.item_key(sec or "", data)
        entry = where.setdefault(key, {"start": a, "keys": {}})
        current: str | None = None                    # the key a deeper line belongs to
        entry_indent: dict[str, int] = {}             # key -> indent of its block-list entries
        entry_count: dict[str, int] = {}
        for j in range(a, b):
            code = _split_comment(lines[j])[0]
            if not code.strip():
                continue
            km = KEY_RE.match(code)
            k = km.group(1) if km and (j == a or _indent(code) <= _indent(lines[a]) + 2) else None
            if k:
                current = k
            elif current and j > a and ITEM_RE.match(code) and entry_indent.setdefault(current, _indent(code)) == _indent(code):
                n = entry_count.get(current, 0)         # an entry of a block list under `current`: anchored as `current[n]`
                entry_count[current] = n + 1
                k = f"{current}[{n}]"
                entry["keys"].setdefault(k, j)
                info[j] = (key, k)
                covered.add(j)
                continue
            info[j] = (key, None) if j == a else (key, k or current)
            if k:
                entry["keys"].setdefault(k, j)
            covered.add(j)
    section = None
    for i, ln in enumerate(lines):
        code = _split_comment(ln)[0]
        if not code.strip():
            continue
        top = SECTION_RE.match(code)
        if top:
            section = top.group(1)
            where[f"@section:{section}"] = {"start": i, "keys": {}}
            info[i] = (f"@section:{section}", None)
        elif i not in covered and section is not None:
            info[i] = (f"@section:{section}", None)
    return info, where


def harvest(text: str, layout: Layout = GRAPH_YAML) -> list[dict]:
    """Comments in YAML text -> anchored comments: {item_key, key, position, text}."""
    lines = text.splitlines()
    info, _ = _index(lines, layout)
    out: list[dict] = []
    pending: list[str] = []
    seen_code = False
    for i, ln in enumerate(lines):
        code, comment = _split_comment(ln)
        if not code.strip():
            if comment is not None:
                pending.append(comment)
            continue
        anchor, key = info.get(i, ("@file", None))
        for c in pending:
            header = layout.file_header and not seen_code
            out.append({"item_key": "@file" if header else anchor, "key": None if header else key, "position": "before", "text": c})
        pending = []
        seen_code = True
        if comment is not None:
            out.append({"item_key": anchor, "key": key, "position": "trailing", "text": comment})
    for c in pending:
        m = ORPHAN_RE.match(c)    # an orphan written by `attach`: keep its original anchor so it can re-attach
        out.append({"item_key": m.group(1) if m else "@file", "key": None, "position": "before",
                    "text": m.group(2) if m else c})
    return out


def attach(text: str, comments: list[dict], layout: Layout = GRAPH_YAML) -> tuple[str, list[dict]]:
    """Re-attach comments to freshly written YAML. Returns (text, orphans)."""
    lines = text.splitlines()
    _, where = _index(lines, layout)
    before: dict[int, list[str]] = {}
    trailing: dict[int, list[str]] = {}
    orphans: list[dict] = []
    for c in comments:
        if c["item_key"] == "@file":
            before.setdefault(0, []).append(c["text"])
            continue
        w = where.get(c["item_key"])
        if not w:
            orphans.append(c)
            continue
        line = w["start"]
        if c["key"]:                                   # `deps[1]` falls back to `deps`, then to the node's first line
            line = w["keys"].get(c["key"], w["keys"].get(c["key"].split("[")[0], w["start"]))
        (before if c["position"] == "before" else trailing).setdefault(line, []).append(c["text"])
    out: list[str] = []
    for i, ln in enumerate(lines):
        pad = ln[:len(ln) - len(ln.lstrip())]
        out += [f"{pad}# {t}".rstrip() for t in before.get(i, [])]
        out.append(ln + "".join(f"  # {t}" for t in trailing.get(i, [])))
    out += [f"# [orphaned from {c['item_key']}] {c['text']}" for c in orphans]
    return "\n".join(out) + "\n", orphans


def format_keeping_comments(original: str, graph: Graph) -> tuple[str, bool]:
    """The canonical YAML of `graph` with the comments of `original` put back. The bool says whether every comment
    came back in place (False means some became orphans or moved, and the plain canonical text is returned instead)."""
    plain = to_yaml(graph)
    comments = harvest(original)
    if not comments:
        return plain, True
    merged, orphans = attach(plain, comments)
    if orphans or harvest(merged) != comments:
        return plain, False
    return merged, True


# ---- the SQLite store and the JSON round trip -----------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, json_sha256 TEXT, yaml_sha256 TEXT, updated_at REAL);
CREATE TABLE IF NOT EXISTS comments (file TEXT, item_key TEXT, key TEXT, position TEXT, text TEXT, seq INTEGER);
CREATE INDEX IF NOT EXISTS comments_file ON comments(file);
"""


def default_store_path() -> Path:
    """`$ZINET_HOME/comments.db`, or `~/.zinet/comments.db`."""
    return Path(os.environ.get("ZINET_HOME") or Path.home() / ".zinet") / "comments.db"


def file_key(path: str | Path) -> str:
    """How a graph file is named in the store: its absolute path without the extension, so `g.yaml` and `g.json` share it."""
    p = Path(path).resolve()
    return str(p.with_suffix(""))


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


class CommentStore:
    """Comments (and which YAML/JSON pair they belong to) in an SQLite file. Use as a context manager."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_store_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.executescript(DDL)

    def close(self) -> None:
        self.db.commit()
        self.db.close()

    def __enter__(self) -> "CommentStore":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def replace_comments(self, file: str, comments: list[dict]) -> None:
        self.db.execute("DELETE FROM comments WHERE file=?", (file,))
        self.db.executemany("INSERT INTO comments VALUES (?,?,?,?,?,?)",
                            [(file, c["item_key"], c["key"], c["position"], c["text"], i) for i, c in enumerate(comments)])
        self.db.commit()

    def comments(self, file: str) -> list[dict]:
        rows = self.db.execute("SELECT item_key, key, position, text FROM comments WHERE file=? ORDER BY seq", (file,))
        return [dict(item_key=r[0], key=r[1], position=r[2], text=r[3]) for r in rows]

    def register(self, base: Path) -> None:
        """Record a YAML/JSON pair (`base` without extension) and the hashes of both files as they are now."""
        self.db.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?)",
                        (file_key(base), _sha256(base.with_suffix(".json")), _sha256(base.with_suffix(".yaml")), time.time()))
        self.db.commit()

    def registered(self, base: Path) -> tuple[str | None, str | None] | None:
        """(json_sha256, yaml_sha256) recorded at the last convert of `base`, or None."""
        r = self.db.execute("SELECT json_sha256, yaml_sha256 FROM files WHERE path=?", (file_key(base),)).fetchone()
        return (r[0], r[1]) if r else None


def graph_to_json(graph: Graph) -> str:
    data = graph.model_dump(mode="json", exclude_defaults=True)
    return json.dumps({"version": graph.version, **data}, indent=2, ensure_ascii=False) + "\n"


def yaml_to_json(src: Path, dst: Path, store: CommentStore) -> dict:
    """Write `dst` (JSON) from `src` (YAML) and keep the YAML's comments in the store. Returns {"comments": n}."""
    from .io import load_graph
    text = src.read_text(encoding="utf-8")
    graph = load_graph(src, resolve_imports=False)
    store.replace_comments(file_key(src), harvest(text))
    dst.write_text(graph_to_json(graph), encoding="utf-8")
    store.register(src.with_suffix(""))
    return {"comments": len(store.comments(file_key(src)))}


def json_to_yaml(src: Path, dst: Path, store: CommentStore) -> dict:
    """Write `dst` (YAML) from `src` (JSON) with the stored comments put back. If `dst` already exists, comments added to it
    since the last convert are kept. Returns {"comments": n, "orphans": n}."""
    graph = Graph.model_validate(json.loads(src.read_text(encoding="utf-8")))
    base = file_key(src)
    if dst.exists():
        store.replace_comments(base, harvest(dst.read_text(encoding="utf-8")))
    text, orphans = attach(to_yaml(graph), store.comments(base))
    dst.write_text(text, encoding="utf-8")
    store.register(src.with_suffix(""))
    return {"comments": len(store.comments(base)), "orphans": len(orphans)}
