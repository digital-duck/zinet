"""`gir` command-line tool: validate, diff, slice, and render graph.yaml files.

Exit codes: 0 success, 1 validation errors or differences found, 2 usage, load, or render failure.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .io import dump_graph, load_graph, to_yaml
from .render import BINARY_FORMATS, FORMATS, render
from .transforms import diff_graphs, slice_to
from .validator import validate


def _cmd_validate(args: argparse.Namespace) -> int:
    graph = load_graph(args.file, resolve_imports=not args.no_imports)
    issues = validate(graph)
    for issue in issues:
        print(f"{args.file}: {issue}")
    if not issues:
        print(f"{args.file}: ok ({len(graph.nodes())} nodes)")
    return 1 if any(issue.severity == "error" for issue in issues) else 0


def _cmd_diff(args: argparse.Namespace) -> int:
    result = diff_graphs(load_graph(args.old), load_graph(args.new))
    if result.is_empty:
        print("no differences")
        return 0
    for node_id in result.added:
        print(f"+ {node_id}")
    for node_id in result.removed:
        print(f"- {node_id}")
    for node_id, delta in result.changed.items():
        for name, (old, new) in delta.items():
            print(f"~ {node_id}.{name}: {old!r} -> {new!r}")
    return 1


def _cmd_slice(args: argparse.Namespace) -> int:
    graph = slice_to(load_graph(args.file), args.target)
    if args.output:
        dump_graph(graph, args.output)
    else:
        sys.stdout.write(to_yaml(graph))
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    if args.format in BINARY_FORMATS and not args.output:
        raise ValueError(f"--format {args.format} is binary; pass -o FILE")
    graph = load_graph(args.file, resolve_imports=not args.no_imports)
    data = render(graph, args.format)
    if args.output:
        Path(args.output).write_bytes(data)
    else:
        sys.stdout.buffer.write(data)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gir", description="graph.yaml intermediate representation tools")
    parser.add_argument("--version", action="version", version=f"gir {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_diff = sub.add_parser("diff", help="show node-level differences between two graphs")
    p_diff.add_argument("old")
    p_diff.add_argument("new")
    p_diff.set_defaults(handler=_cmd_diff)

    p_slice = sub.add_parser("slice", help="extract a target node and its prerequisites")
    p_slice.add_argument("file")
    p_slice.add_argument("target")
    p_slice.add_argument("-o", "--output", help="write to this file instead of stdout")
    p_slice.set_defaults(handler=_cmd_slice)

    p_render = sub.add_parser("render", help="visualize a graph as svg, png, pdf, or mermaid")
    p_render.add_argument("file")
    p_render.add_argument("--format", choices=FORMATS, default="svg", help="output format (default: svg)")
    p_render.add_argument("-o", "--output", help="write to this file instead of stdout")
    p_render.add_argument("--no-imports", action="store_true", help="do not resolve imports")
    p_render.set_defaults(handler=_cmd_render)

    p_validate = sub.add_parser("validate", help="check a graph.yaml for structural errors")
    p_validate.add_argument("file")
    p_validate.add_argument("--no-imports", action="store_true", help="do not resolve imports")
    p_validate.set_defaults(handler=_cmd_validate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except KeyError as exc:
        print(f"gir: error: {exc.args[0]}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"gir: error: {exc}", file=sys.stderr)
        return 2
