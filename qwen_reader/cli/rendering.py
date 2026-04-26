"""Rich console helpers for formatting CLI output.

This module owns all presentation logic: the shared ``Console`` instance,
progress-bar factories, and result-panel rendering.  It depends on
``SynthesisResult`` (Use-Case layer) which is allowed by the dependency rule.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from qwen_reader.core.synthesis import SynthesisResult

# ---------------------------------------------------------------------------
# Shared console instance
# ---------------------------------------------------------------------------

console = Console()


# ---------------------------------------------------------------------------
# Result display
# ---------------------------------------------------------------------------


def print_result(result: SynthesisResult) -> None:
    """Display a synthesis result in a styled Rich panel."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("📁 File", str(result.path))
    table.add_row("⏱️  Duration", result.duration_display)
    table.add_row("💾 Size", f"{result.size_mb:.1f} MB")
    table.add_row("🧩 Chunks", str(result.chunks_total))
    table.add_row("🎙️  Speaker", result.speaker)
    table.add_row("🌐 Language", result.language)
    console.print(
        Panel(table, title="[bold green]✅ Audio generated", border_style="green")
    )


# ---------------------------------------------------------------------------
# Progress bars
# ---------------------------------------------------------------------------


def model_progress_bar() -> Progress:
    """Context manager: spinner while the model loads (transient)."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


def synthesis_progress_bar() -> Progress:
    """Context manager: bar + counter for chunk-level progress."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )
