from pathlib import Path

from graph_ir.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_validate_ok(capsys):
    assert main(["validate", str(FIXTURES / "solver_problem.yaml")]) == 0
    assert "ok (8 nodes)" in capsys.readouterr().out


def test_validate_reports_errors_with_exit_1(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("concepts:\n  - id: x\n    deps: [y]\n  - id: y\n    deps: [x]\n")
    assert main(["validate", str(bad)]) == 1
    assert "error: cycle" in capsys.readouterr().out


def test_slice_writes_yaml_to_stdout(capsys):
    assert main(["slice", str(FIXTURES / "spl_pipeline.yaml"), "step_summarize"]) == 0
    assert "step_summarize" in capsys.readouterr().out


def test_slice_unknown_target_exit_2(capsys):
    assert main(["slice", str(FIXTURES / "spl_pipeline.yaml"), "nope"]) == 2
    assert "unknown node" in capsys.readouterr().err


def test_diff_identical_exit_0(capsys):
    path = str(FIXTURES / "concept_book.yaml")
    assert main(["diff", path, path]) == 0
    assert "no differences" in capsys.readouterr().out
