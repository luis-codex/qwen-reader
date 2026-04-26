"""CLI application entry point and click group definition.

This module owns the top-level ``cli`` group, the ``main()`` wrapper,
and the Windows UTF-8 reconfiguration guard.  Commands are registered
via a bottom-of-file import of ``commands.py``.
"""

from __future__ import annotations

import sys

# Force UTF-8 on Windows to avoid cp1252 emoji encoding errors
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
from rich.panel import Panel

from qwen_reader import __version__
from qwen_reader.cli.rendering import console

# ---------------------------------------------------------------------------
# Click group
# ---------------------------------------------------------------------------

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, "-v", "--version")
@click.pass_context
def cli(ctx: click.Context):
    """qwen-reader -- Convert articles to audio with Qwen3-TTS."""
    if ctx.invoked_subcommand is None:
        console.print(
            Panel(
                "[bold]qwen-reader[/] v{ver}\n"
                "Convert articles to audio with Qwen3-TTS\n\n"
                "Run [cyan]qwen-reader -h[/] for usage.".format(ver=__version__),
                title="qwen-reader",
                border_style="bright_blue",
            )
        )
        console.print(ctx.get_help())


# Register commands — import triggers @cli.command() decorators
import qwen_reader.cli.commands  # noqa: E402, F401


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    cli()


if __name__ == "__main__":
    main()
