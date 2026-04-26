"""Shared click option groups for consistent CLI flags across commands.

Centralises option definitions so that adding a new voice or output
parameter propagates to all commands automatically.
"""

from __future__ import annotations

import click

from qwen_reader.core.storage import DEFAULT_OUTPUT_DIR

# ---------------------------------------------------------------------------
# Option groups
# ---------------------------------------------------------------------------

voice_options = [
    click.option(
        "--speaker", "-s",
        default="Aiden", show_default=True,
        help="TTS voice name. Use 'speakers' command to list.",
    ),
    click.option(
        "--lang", "-l",
        default="Auto", show_default=True,
        help="Language: Auto, English, Chinese, Spanish, etc.",
    ),
    click.option(
        "--instruct", "-i",
        default="Read in a natural, conversational tone, like a podcast narrator.",
        help="Style instruction.",
    ),
]

output_options = [
    click.option(
        "--output-dir", "-o",
        type=click.Path(),
        default=str(DEFAULT_OUTPUT_DIR), show_default=True,
        help="Output directory.",
    ),
    click.option(
        "--name", "-n",
        default=None,
        help="Custom output filename (no extension).",
    ),
]

hw_options = [
    click.option(
        "--device", "-d",
        default="cuda:0", show_default=True,
        help="Compute device: cuda:0, cpu, etc.",
    ),
]


# ---------------------------------------------------------------------------
# Combinator
# ---------------------------------------------------------------------------


def apply_options(option_list):
    """Decorator combinator: applies a list of click.option decorators."""

    def decorator(fn):
        for opt in reversed(option_list):
            fn = opt(fn)
        return fn

    return decorator
