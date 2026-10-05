"""Canonical formatting for graph.yaml files (`zinet prettify`).

The canonical form is what `to_yaml` writes: `version` first, layers in order, keys in model
field order, and defaults omitted. Formatting works on one file only and never resolves imports,
so imported nodes are not copied into the file being formatted.

YAML comments are not preserved, because PyYAML does not expose them. `has_comments` lets the
CLI refuse to rewrite a file that would lose them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .io import load_graph, to_yaml

_INLINE_COMMENT = re.compile(r"(^|\s)#")


@dataclass(frozen=True)
class Prettified:
    original: str
    formatted: str
    has_comments: bool

    @property
    def changed(self) -> bool:
        return self.original != self.formatted


def has_comments(text: str) -> bool:
    """True if any line looks like it carries a YAML comment. Conservative: a `#` inside a quoted
    string also counts, which only makes the check refuse more often, never less."""
    return any(_INLINE_COMMENT.search(line) for line in text.splitlines())


def prettify_file(path: str | Path) -> Prettified:
    source = Path(path)
    original = source.read_text(encoding="utf-8")
    graph = load_graph(source, resolve_imports=False)
    return Prettified(original=original, formatted=to_yaml(graph), has_comments=has_comments(original))
