import shutil
from pathlib import Path

import pytest

from graph_ir import load_graph, render, to_dot, to_mermaid
from graph_ir.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
SOLVER = FIXTURES / "solver_problem.yaml"


def test_dot_has_layer_clusters_and_typed_edges():
    dot = to_dot(load_graph(SOLVER))
    assert dot.startswith("digraph graph_ir {")
    assert 'subgraph "cluster_primitives"' in dot
    assert '"max_units" -> "capacity_constraint" [label="constraint"];' in dot
    assert '"unit_cost" -> "total_cost";' in dot


def test_mermaid_uses_layer_shapes_and_edge_labels():
    text = to_mermaid(load_graph(SOLVER))
    assert text.startswith("flowchart LR")
    assert "subgraph primitives" in text
    assert "-->|constraint|" in text


def test_mermaid_escapes_quotes_in_labels(tmp_path):
    source = tmp_path / "g.yaml"
    source.write_text('primitives:\n  - id: a\n    label: say "hi"\n')
    assert "say #quot;hi#quot;" in to_mermaid(load_graph(source))


def test_mermaid_declares_dangling_dependencies(tmp_path):
    source = tmp_path / "g.yaml"
    source.write_text("concepts:\n  - id: c\n    deps: [ghost]\n")
    text = to_mermaid(load_graph(source))
    assert '["ghost"]' in text


@pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz not installed")
def test_svg_and_pdf_render_via_dot():
    graph = load_graph(SOLVER)
    assert b"<svg" in render(graph, "svg")
    assert render(graph, "pdf").startswith(b"%PDF")


def test_unknown_format_is_rejected():
    with pytest.raises(ValueError, match="unknown format"):
        render(load_graph(SOLVER), "gif")


def test_cli_mermaid_to_stdout(capfd):
    assert main(["render", str(SOLVER), "--format", "mermaid"]) == 0
    assert "flowchart LR" in capfd.readouterr().out


def test_cli_binary_format_requires_output(capsys):
    assert main(["render", str(SOLVER), "--format", "png"]) == 2
    assert "pass -o FILE" in capsys.readouterr().err


@pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz not installed")
def test_cli_png_to_file(tmp_path):
    target = tmp_path / "solver.png"
    assert main(["render", str(SOLVER), "--format", "png", "-o", str(target)]) == 0
    assert target.read_bytes().startswith(b"\x89PNG")
