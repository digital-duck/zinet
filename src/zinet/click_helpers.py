"""Click helpers shared across the ZiNets CLIs. `click` is a core zinet dependency.

`FullHelpGroup` stops Click from truncating command summaries with "..." in `--help`.
Click's `Group.format_commands()` cuts a command's docstring summary to one line of
`terminal width - 6 - longest command name`; this class shows the full first paragraph
and lets the formatter wrap it instead.

    import click
    from zinet.click_helpers import FullHelpGroup, HELP_OPTION_NAMES

    @click.group(cls=FullHelpGroup, context_settings={"help_option_names": HELP_OPTION_NAMES})
    @version_option("my-dist-name", "mytool")      # adds -v / --version
    def main(): ...

    @main.group()          # subgroups inherit FullHelpGroup (group_class = type)
    def tools(): ...
"""

from __future__ import annotations

import click

__all__ = ["FullHelpGroup", "HELP_OPTION_NAMES", "version_option"]

# Pass as context_settings={"help_option_names": HELP_OPTION_NAMES} to accept -h as well as --help.
HELP_OPTION_NAMES = ["-h", "--help"]


def version_option(package: str, prog_name: str | None = None):
    """`-v`/`--version` for a command group, printing `PROG, version X` read from the installed distribution `package`
    (the pip name, e.g. "app-graph"), so there is no second version string to keep in step with pyproject.toml.

        @click.group(cls=FullHelpGroup, ...)
        @version_option("app-graph", "appgraph")
        def main(): ...
    """
    return click.version_option(None, "-v", "--version", package_name=package, prog_name=prog_name, message="%(prog)s, version %(version)s")


class FullHelpGroup(click.Group):
    """A `click.Group` whose command list shows each command's full summary, wrapped, never cut with '...'."""

    group_class = type  # subgroups created with @group.group() use this same class

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        rows = []
        for name in self.list_commands(ctx):
            cmd = self.get_command(ctx, name)
            if cmd is None or cmd.hidden:
                continue
            text = cmd.short_help or (cmd.help or "").split("\n\n")[0]
            rows.append((name, " ".join(text.split())))
        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)  # write_dl wraps long text to the terminal width
