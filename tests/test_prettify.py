from pathlib import Path

from zinet import load_graph
from zinet.cli import main
from zinet.prettify import has_comments, prettify_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_formatting_is_idempotent(tmp_path, capsys):
    # Hand-written fixtures use flow-style lists, so prettify rewrites them; its own output must not change.
    first = tmp_path / "first.yaml"
    first.write_text(prettify_file(FIXTURES / "solver_problem.yaml").formatted)
    assert main(["prettify", str(first)]) == 0
    assert "already formatted" in capsys.readouterr().out


def test_unformatted_file_prints_diff_and_exit_1(tmp_path, capsys):
    source = tmp_path / "messy.yaml"
    source.write_text("primitives:\n  - meta: {x: 1}\n    id: a\n")
    assert main(["prettify", str(source)]) == 1
    out = capsys.readouterr().out
    assert "--- " in out and "+version: '1.0'" in out
    assert source.read_text().startswith("primitives:")  # plain run never writes


def test_write_rewrites_in_place(tmp_path):
    source = tmp_path / "messy.yaml"
    source.write_text("primitives:\n  - meta: {x: 1}\n    id: a\n")
    assert main(["prettify", str(source), "--write"]) == 0
    assert source.read_text().startswith("version: '1.0'")
    assert main(["prettify", str(source)]) == 0  # now stable


def test_write_refuses_files_with_comments(tmp_path, capsys):
    source = tmp_path / "commented.yaml"
    original = "# keep me\nprimitives:\n  - id: a  # note\n"
    source.write_text(original)
    assert main(["prettify", str(source), "--write"]) == 2
    assert source.read_text() == original
    assert "would drop them" in capsys.readouterr().err


def test_prettify_does_not_inline_imports(tmp_path):
    (tmp_path / "base.yaml").write_text("primitives:\n  - id: a\n")
    main_file = tmp_path / "main.yaml"
    main_file.write_text("imports: [base.yaml]\nconcepts:\n  - id: c\n    deps: [a]\n")
    result = prettify_file(main_file)
    assert "- id: a" not in result.formatted
    assert "imports:" in result.formatted


def test_has_comments_detects_inline_and_full_line():
    assert has_comments("# top\nprimitives: []\n")
    assert has_comments("primitives:\n  - id: a  # inline\n")
    assert not has_comments("primitives:\n  - id: a\n")


def test_prettify_keeps_graph_semantics(tmp_path):
    source = FIXTURES / "spl_pipeline.yaml"
    result = prettify_file(source)
    tmp_out = tmp_path / "out.yaml"
    tmp_out.write_text(result.formatted)
    assert load_graph(tmp_out) == load_graph(source)
