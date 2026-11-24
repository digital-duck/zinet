from __future__ import annotations

import pytest

click = pytest.importorskip("click")
from click.testing import CliRunner  # noqa: E402

from zinet.click_helpers import HELP_OPTION_NAMES, FullHelpGroup  # noqa: E402

LONG = "Small dev-utility commands (clean-port, scaffold-vue, scaffold-fastapi, suggest-graph-clusters)."


def _cli():
    @click.group(cls=FullHelpGroup, context_settings={"help_option_names": HELP_OPTION_NAMES})
    def main():
        """Root."""

    @main.group()
    def tools():
        """Small dev-utility commands (clean-port, scaffold-vue, scaffold-fastapi, suggest-graph-clusters)."""

    @tools.command()
    def sub():
        """A subcommand with a rather long one-line summary that would be cut off by default."""

    return main


def test_summary_not_truncated():
    out = CliRunner().invoke(_cli(), ["-h"], terminal_width=80).output
    assert not [l for l in out.splitlines() if l.rstrip().endswith("...") and not l.startswith("Usage")]
    assert " ".join(out.split()).count(LONG) == 1


def test_subgroup_inherits_and_short_flag():
    main = _cli()
    assert isinstance(main.commands["tools"], FullHelpGroup)
    out = CliRunner().invoke(main, ["tools", "-h"], terminal_width=60).output
    assert not [l for l in out.splitlines() if l.rstrip().endswith("...") and not l.startswith("Usage")]
    assert "cut off by default." in " ".join(out.split())
