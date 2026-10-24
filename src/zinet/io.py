"""Load, resolve, and dump graph.yaml files."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .formats import explain_foreign
from .schema import Graph, Layer


def load_graph(path: str | Path, resolve_imports: bool = True) -> Graph:
    """Load a graph.yaml. With `resolve_imports`, merge every file listed under `imports:`.

    Import paths are relative to the importing file. Imported nodes keep their ids (no
    namespacing); a duplicate id across files is an error. The returned graph has no `imports`.
    This does not run `validate`; call that separately for structural checks.
    """
    source = Path(path)
    graph = _read(source)
    if resolve_imports:
        graph = _resolve(graph, source, stack=())
    return graph


class _IndentedDumper(yaml.SafeDumper):
    """Indents list items under their parent key ("  - id: a") instead of PyYAML's flush style."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def to_yaml(graph: Graph) -> str:
    data = graph.model_dump(mode="json", exclude_defaults=True)
    data = {"version": graph.version, **data}  # always written, first, even when default
    return yaml.dump(data, Dumper=_IndentedDumper, sort_keys=False, allow_unicode=True)


def dump_graph(graph: Graph, path: str | Path) -> None:
    Path(path).write_text(to_yaml(graph), encoding="utf-8")


SUPPORTED_VERSIONS = ("1.0",)


def _read(path: Path) -> Graph:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    foreign = explain_foreign(data)
    if foreign:
        raise ValueError(f"{path}: {foreign}")
    if str(data.get("version", "1.0")) not in SUPPORTED_VERSIONS:
        raise ValueError(f"{path}: unsupported graph version {data['version']!r}; supported: {', '.join(SUPPORTED_VERSIONS)}")
    try:
        return Graph.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"{path}: {exc}") from exc


def _resolve(graph: Graph, source: Path, stack: tuple[Path, ...]) -> Graph:
    key = source.resolve()
    if key in stack:
        chain = " -> ".join(str(p) for p in (*stack, key))
        raise ValueError(f"import cycle: {chain}")

    merged: dict[Layer, list] = {layer: [] for layer in Layer}
    origin: dict[str, Path] = {}

    def add(layer: Layer, node, where: Path) -> None:
        if node.id in origin:
            raise ValueError(f"duplicate node id {node.id!r}: defined in {origin[node.id]} and {where}")
        origin[node.id] = where
        merged[layer].append(node)

    base = source.parent
    for imp in graph.imports:
        child_path = base / imp
        child = _resolve(_read(child_path), child_path, stack=(*stack, key))
        for layer, node in child.layered_nodes():
            add(layer, node, child_path)
    for layer, node in graph.layered_nodes():
        add(layer, node, source)

    return Graph(
        version=graph.version,
        primitives=merged[Layer.PRIMITIVES],
        concepts=merged[Layer.CONCEPTS],
        applications=merged[Layer.APPLICATIONS],
    )
