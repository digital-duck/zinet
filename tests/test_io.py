from pathlib import Path

import pytest

from graph_ir import dump_graph, load_graph

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_fixture():
    graph = load_graph(FIXTURES / "solver_problem.yaml")
    assert len(graph.nodes()) == 8
    assert graph.imports == []


def test_imports_are_merged_relative_to_importing_file(tmp_path):
    (tmp_path / "base.yaml").write_text("primitives:\n  - id: a\n")
    (tmp_path / "main.yaml").write_text(
        "imports: [base.yaml]\nconcepts:\n  - id: c\n    deps: [a]\n"
    )
    graph = load_graph(tmp_path / "main.yaml")
    assert sorted(n.id for n in graph.nodes()) == ["a", "c"]
    assert graph.imports == []


def test_import_cycle_is_an_error(tmp_path):
    (tmp_path / "a.yaml").write_text("imports: [b.yaml]\n")
    (tmp_path / "b.yaml").write_text("imports: [a.yaml]\n")
    with pytest.raises(ValueError, match="import cycle"):
        load_graph(tmp_path / "a.yaml")


def test_duplicate_id_across_files_is_an_error(tmp_path):
    (tmp_path / "base.yaml").write_text("primitives:\n  - id: a\n")
    (tmp_path / "main.yaml").write_text("imports: [base.yaml]\nprimitives:\n  - id: a\n")
    with pytest.raises(ValueError, match="duplicate node id 'a'"):
        load_graph(tmp_path / "main.yaml")


def test_dump_then_load_round_trips(tmp_path):
    graph = load_graph(FIXTURES / "spl_pipeline.yaml")
    target = tmp_path / "out.yaml"
    dump_graph(graph, target)
    assert load_graph(target) == graph
