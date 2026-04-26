"""CLI entry point — built with click + rich."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Force UTF-8 on Windows to avoid cp1252 emoji encoding errors
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
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

from qwen_reader import __version__
from qwen_reader.core.model import ModelConfig, get_speakers
from qwen_reader.core.synthesis import (
    DEFAULT_OUTPUT_DIR,
    SynthesisConfig,
    SynthesisResult,
    synthesize_file,
    synthesize_text,
)
from qwen_reader.core.text import SUPPORTED_EXTENSIONS

console = Console()

# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------

_voice_options = [
    click.option("--speaker", "-s", default="Aiden", show_default=True, help="TTS voice name. Use --speakers to list."),
    click.option("--lang", "-l", default="Auto", show_default=True, help="Language: Auto, English, Chinese, Spanish, etc."),
    click.option("--instruct", "-i", default="Read in a natural, conversational tone, like a podcast narrator.", help="Style instruction."),
]

_output_options = [
    click.option("--output-dir", "-o", type=click.Path(), default=str(DEFAULT_OUTPUT_DIR), show_default=True, help="Output directory."),
    click.option("--name", "-n", default=None, help="Custom output filename (no extension)."),
]

_hw_options = [
    click.option("--device", "-d", default="cuda:0", show_default=True, help="Compute device: cuda:0, cpu, etc."),
]


def _apply_options(option_list):
    """Decorator combinator: applies a list of click.option decorators."""
    def decorator(fn):
        for opt in reversed(option_list):
            fn = opt(fn)
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Rich helpers
# ---------------------------------------------------------------------------

def _print_result(result: SynthesisResult) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("📁 File", str(result.path))
    table.add_row("⏱️  Duration", result.duration_display)
    table.add_row("💾 Size", f"{result.size_mb:.1f} MB")
    table.add_row("🧩 Chunks", str(result.chunks_total))
    table.add_row("🎙️  Speaker", result.speaker)
    table.add_row("🌐 Language", result.language)
    console.print(Panel(table, title="[bold green]✅ Audio generated", border_style="green"))


def _model_progress_bar():
    """Context manager that shows a spinner while the model loads."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


def _synthesis_progress_bar():
    """Context manager for chunk-level progress."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )


# ---------------------------------------------------------------------------
# Click CLI
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


# ---- read ----------------------------------------------------------------

@cli.command()
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True))
@_apply_options(_voice_options)
@_apply_options(_output_options)
@_apply_options(_hw_options)
def read(files, speaker, lang, instruct, output_dir, name, device):
    """Convert one or more files to audio.

    Supports: .md .markdown .txt .rst .text
    """
    mcfg = ModelConfig(device=device)
    scfg = SynthesisConfig(
        language=lang, speaker=speaker, instruct=instruct,
        output_dir=Path(output_dir),
    )

    # Load model with spinner
    with _model_progress_bar() as progress:
        task = progress.add_task("Loading model…")
        model_ref = [None]

        def on_load(msg: str):
            progress.update(task, description=msg)

        from qwen_reader.core.model import get_model
        model_ref[0] = get_model(mcfg, on_progress=on_load)
        progress.update(task, description="Model ready ✅")

    success = 0
    failed = 0

    for filepath in files:
        path = Path(filepath)
        console.rule(f"[bold]{path.name}")

        name_override = name if (name and len(files) == 1) else None

        with _synthesis_progress_bar() as progress:
            synth_task = progress.add_task(f"Synthesizing {path.name}", total=0)

            def on_chunk(current: int, total: int, preview: str):
                progress.update(synth_task, total=total, completed=current,
                                description=f"[dim]{preview[:50]}…")

            try:
                result = synthesize_file(
                    file_path=path,
                    output_name=name_override,
                    config=scfg,
                    model_config=mcfg,
                    on_chunk=on_chunk,
                    on_model_progress=lambda _: None,
                )
            except (FileNotFoundError, ValueError, RuntimeError) as exc:
                console.print(f"  [red]❌ {exc}[/red]")
                failed += 1
                continue

        _print_result(result)
        success += 1

    if len(files) > 1:
        console.rule()
        style = "green" if failed == 0 else "yellow"
        console.print(f"[{style}]🎉 Done! {success} converted, {failed} failed[/]")

    raise SystemExit(0 if failed == 0 else 1)


# ---- speak ----------------------------------------------------------------

@cli.command()
@click.argument("text")
@_apply_options(_voice_options)
@_apply_options(_output_options)
@_apply_options(_hw_options)
def speak(text, speaker, lang, instruct, output_dir, name, device):
    """Convert inline text to audio.

    Example: qwen-reader speak "Hello world, this is a test."
    """
    mcfg = ModelConfig(device=device)
    scfg = SynthesisConfig(
        language=lang, speaker=speaker, instruct=instruct,
        output_dir=Path(output_dir),
    )
    out_name = name or "spoken_text"

    with _model_progress_bar() as progress:
        task = progress.add_task("Loading model…")
        from qwen_reader.core.model import get_model
        get_model(mcfg, on_progress=lambda msg: progress.update(task, description=msg))

    with _synthesis_progress_bar() as progress:
        synth_task = progress.add_task("Synthesizing…", total=0)

        def on_chunk(current: int, total: int, preview: str):
            progress.update(synth_task, total=total, completed=current,
                            description=f"[dim]{preview[:50]}…")

        try:
            result = synthesize_text(
                text=text,
                output_name=out_name,
                config=scfg,
                model_config=mcfg,
                on_chunk=on_chunk,
                on_model_progress=lambda _: None,
            )
        except (ValueError, RuntimeError) as exc:
            console.print(f"[red]❌ {exc}[/red]")
            raise SystemExit(1)

    _print_result(result)


# ---- speakers -------------------------------------------------------------

@cli.command()
@_apply_options(_hw_options)
def speakers(device):
    """List available TTS voices."""
    mcfg = ModelConfig(device=device)

    with _model_progress_bar() as progress:
        task = progress.add_task("Loading model…")
        from qwen_reader.core.model import get_model
        get_model(mcfg, on_progress=lambda msg: progress.update(task, description=msg))

    names = get_speakers(mcfg)

    table = Table(title="🎙️ Available Speakers", show_lines=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="bold cyan")
    for i, s in enumerate(names, 1):
        table.add_row(str(i), s)

    console.print(table)
    console.print(f"\n  [dim]{len(names)} voices available[/dim]")


# ---- list -----------------------------------------------------------------

@cli.command("list")
@click.option("--output-dir", "-o", type=click.Path(), default=str(DEFAULT_OUTPUT_DIR), show_default=True)
def list_audio(output_dir):
    """List previously generated audio files."""
    out = Path(output_dir)
    files = sorted(out.glob("*.wav"))

    if not files:
        console.print(f"[dim]📂 No audio files in {out}[/dim]")
        return

    table = Table(title=f"📂 {out}")
    table.add_column("File", style="bold")
    table.add_column("Size", justify="right")
    table.add_column("Modified", style="dim")

    total_size = 0.0
    for f in files:
        size_mb = f.stat().st_size / (1024 * 1024)
        total_size += size_mb
        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime))
        table.add_row(f"🔊 {f.name}", f"{size_mb:.1f} MB", mtime)

    table.add_section()
    table.add_row(f"[bold]{len(files)} files[/]", f"[bold]{total_size:.1f} MB[/]", "")

    console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    cli()


if __name__ == "__main__":
    main()
