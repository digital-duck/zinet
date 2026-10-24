"""`zinet` command-line tool: validate, diff, slice, render, prettify, and schema for graph.yaml files.

Exit codes: 0 success, 1 validation errors, differences found, or a file needing prettify,
2 usage, load, or render failure.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .io import dump_graph, load_graph, to_yaml
from .prettify import prettify_file
from .roundtrip import CommentStore, json_to_yaml, yaml_to_json
from .render import BINARY_FORMATS, FORMATS, render
from .schema import json_schema_text
from .transforms import diff_graphs, slice_to
from .validator import OPTIONAL_CHECKS, validate


def _cmd_validate(args: argparse.Namespace) -> int:
    graph = load_graph(args.file, resolve_imports=not args.no_imports)
    issues = validate(graph, checks=OPTIONAL_CHECKS if args.strict else args.check)
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


def _cmd_convert(args: argparse.Namespace) -> int:
    src = Path(args.file)
    to_json = src.suffix.lower() in (".yaml", ".yml")
    if not to_json and src.suffix.lower() != ".json":
        raise ValueError("convert takes a .yaml, .yml or .json file")
    dst = Path(args.output) if args.output else src.with_suffix(".json" if to_json else ".yaml")
    with CommentStore(args.store) as store:
        info = (yaml_to_json if to_json else json_to_yaml)(src, dst, store)
    note = f" ({info['comments']} comment(s) kept in {store.path}" + (f", {info['orphans']} orphaned)" if info.get("orphans") else ")")
    print(f"{src} -> {dst}{note}")
    return 0


def _cmd_prettify(args: argparse.Namespace) -> int:
    result = prettify_file(args.file)
    if not result.changed:
        print(f"{args.file}: already formatted")
        return 0
    if args.write:
        if not result.comments_preserved:
            raise ValueError(f"{args.file} has comments that could not be kept in place, so it was not rewritten")
        Path(args.file).write_text(result.formatted, encoding="utf-8")
        print(f"{args.file}: rewritten")
        return 0
    if not result.comments_preserved:
        print(f"note: {args.file} has comments that could not be kept in place; --write would not rewrite it", file=sys.stderr)
    sys.stdout.writelines(
        difflib.unified_diff(
            result.original.splitlines(keepends=True),
            result.formatted.splitlines(keepends=True),
            fromfile=args.file,
            tofile=f"{args.file} (prettified)",
        )
    )
    return 1


def _cmd_schema(args: argparse.Namespace) -> int:
    text = json_schema_text()
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zinet", description="graph.yaml intermediate representation tools")
    parser.add_argument("--version", action="version", version=f"zinet {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_diff = sub.add_parser("diff", help="show node-level differences between two graphs")
    p_diff.add_argument("old")
    p_diff.add_argument("new")
    p_diff.set_defaults(handler=_cmd_diff)

    p_prettify = sub.add_parser("prettify", help="show or apply the canonical formatting of a graph.yaml")
    p_prettify.add_argument("file")
    p_prettify.add_argument("--write", action="store_true", help="rewrite the file in place instead of printing a diff")
    p_prettify.set_defaults(handler=_cmd_prettify)

    p_render = sub.add_parser("render", help="visualize a graph as svg, png, pdf, or mermaid")
    p_render.add_argument("file")
    p_render.add_argument("--format", choices=FORMATS, default="svg", help="output format (default: svg)")
    p_render.add_argument("-o", "--output", help="write to this file instead of stdout")
    p_render.add_argument("--no-imports", action="store_true", help="do not resolve imports")
    p_render.set_defaults(handler=_cmd_render)

    p_convert = sub.add_parser("convert", help="convert a graph between YAML and JSON, keeping the YAML comments in a small database")
    p_convert.add_argument("file", help="a .yaml or .yml file (to JSON) or a .json file (to YAML)")
    p_convert.add_argument("-o", "--output", help="output file (default: the same name with the other extension)")
    p_convert.add_argument("--store", help="comment database (default: $ZINET_HOME/comments.db, or ~/.zinet/comments.db)")
    p_convert.set_defaults(handler=_cmd_convert)

    p_schema = sub.add_parser("schema", help="print the JSON Schema for graph.yaml")
    p_schema.add_argument("-o", "--output", help="write to this file instead of stdout")
    p_schema.set_defaults(handler=_cmd_schema)

    p_slice = sub.add_parser("slice", help="extract a target node and its prerequisites")
    p_slice.add_argument("file")
    p_slice.add_argument("target")
    p_slice.add_argument("-o", "--output", help="write to this file instead of stdout")
    p_slice.set_defaults(handler=_cmd_slice)

    p_validate = sub.add_parser("validate", help="check a graph.yaml for structural errors")
    p_validate.add_argument("file")
    p_validate.add_argument("--no-imports", action="store_true", help="do not resolve imports")
    p_validate.add_argument("--check", action="append", default=[], choices=OPTIONAL_CHECKS, metavar="NAME",
                            help=f"also run an optional check (repeatable): {', '.join(OPTIONAL_CHECKS)}")
    p_validate.add_argument("--strict", action="store_true", help="run every optional check")
    p_validate.set_defaults(handler=_cmd_validate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except KeyError as exc:
        print(f"zinet: error: {exc.args[0]}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"zinet: error: {exc}", file=sys.stderr)
        return 2
