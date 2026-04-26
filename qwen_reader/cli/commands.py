"""CLI command implementations: read, speak, speakers, list.

Each function is a thin adapter that wires user input into core-layer
calls and delegates all output formatting to ``rendering.py``.
"""

from __future__ import annotations

import time
from pathlib import Path

import click
from rich.table import Table

from qwen_reader.cli.app import cli
from qwen_reader.cli.options import (
    apply_options,
    hw_options,
    output_options,
    voice_options,
)
from qwen_reader.cli.rendering import (
    console,
    model_progress_bar,
    print_result,
    print_ttfa,
    synthesis_progress_bar,
)
from qwen_reader.core.model import ModelConfig, get_speakers
from qwen_reader.core.storage import DEFAULT_OUTPUT_DIR, list_audio_files
from qwen_reader.core.synthesis import (
    SynthesisConfig,
    synthesize_file,
    synthesize_text,
    synthesize_text_streaming,
)


# ---- read ----------------------------------------------------------------


@cli.command()
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True))
@apply_options(voice_options)
@apply_options(output_options)
@apply_options(hw_options)
def read(files, speaker, lang, instruct, output_dir, name, chunk_size, device, quality):
    """Convert one or more files to audio.

    Supports: .md .markdown .txt .rst .text
    """
    mcfg = ModelConfig(device=device, quality=quality)
    scfg = SynthesisConfig(
        language=lang, speaker=speaker, instruct=instruct,
        output_dir=Path(output_dir), chunk_size=chunk_size,
    )

    # Load model with spinner
    with model_progress_bar() as progress:
        task = progress.add_task("Loading model…")

        def on_load(msg: str):
            progress.update(task, description=msg)

        from qwen_reader.core.model import get_model
        get_model(mcfg, on_progress=on_load)
        progress.update(task, description="Model ready ✅")

    success = 0
    failed = 0

    for filepath in files:
        path = Path(filepath)
        console.rule(f"[bold]{path.name}")

        name_override = name if (name and len(files) == 1) else None

        t0 = time.perf_counter()

        with synthesis_progress_bar() as progress:
            synth_task = progress.add_task(f"Synthesizing {path.name}", total=0)

            def on_chunk(current: int, total: int, preview: str):
                progress.update(synth_task, total=total, completed=current,
                                description=f"[dim]{preview[:50]}…")

            def on_first_audio(audio_path: Path):
                ttfa = time.perf_counter() - t0
                print_ttfa(audio_path, ttfa)

            try:
                result = synthesize_file(
                    file_path=path,
                    output_name=name_override,
                    config=scfg,
                    model_config=mcfg,
                    on_chunk=on_chunk,
                    on_first_audio=on_first_audio,
                    on_model_progress=lambda _: None,
                    streaming=True,
                )
            except (FileNotFoundError, ValueError, RuntimeError) as exc:
                console.print(f"  [red]❌ {exc}[/red]")
                failed += 1
                continue

        print_result(result)
        success += 1

    if len(files) > 1:
        console.rule()
        style = "green" if failed == 0 else "yellow"
        console.print(f"[{style}]🎉 Done! {success} converted, {failed} failed[/]")

    raise SystemExit(0 if failed == 0 else 1)


# ---- speak ----------------------------------------------------------------


@cli.command()
@click.argument("text")
@apply_options(voice_options)
@apply_options(output_options)
@apply_options(hw_options)
def speak(text, speaker, lang, instruct, output_dir, name, chunk_size, device, quality):
    """Convert inline text to audio.

    Example: qwen-reader speak "Hello world, this is a test."
    """
    mcfg = ModelConfig(device=device, quality=quality)
    scfg = SynthesisConfig(
        language=lang, speaker=speaker, instruct=instruct,
        output_dir=Path(output_dir), chunk_size=chunk_size,
    )
    out_name = name or "spoken_text"

    with model_progress_bar() as progress:
        task = progress.add_task("Loading model…")
        from qwen_reader.core.model import get_model
        get_model(mcfg, on_progress=lambda msg: progress.update(task, description=msg))

    t0 = time.perf_counter()

    with synthesis_progress_bar() as progress:
        synth_task = progress.add_task("Synthesizing…", total=0)

        def on_chunk(current: int, total: int, preview: str):
            progress.update(synth_task, total=total, completed=current,
                            description=f"[dim]{preview[:50]}…")

        def on_first_audio(audio_path: Path):
            ttfa = time.perf_counter() - t0
            print_ttfa(audio_path, ttfa)

        try:
            result = synthesize_text_streaming(
                text=text,
                output_name=out_name,
                config=scfg,
                model_config=mcfg,
                on_chunk=on_chunk,
                on_first_audio=on_first_audio,
                on_model_progress=lambda _: None,
            )
        except (ValueError, RuntimeError) as exc:
            console.print(f"[red]❌ {exc}[/red]")
            raise SystemExit(1)

    print_result(result)


# ---- speakers -------------------------------------------------------------


@cli.command()
@apply_options(hw_options)
def speakers(device, quality):
    """List available TTS voices."""
    mcfg = ModelConfig(device=device, quality=quality)

    with model_progress_bar() as progress:
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
@click.option(
    "--output-dir", "-o",
    type=click.Path(),
    default=str(DEFAULT_OUTPUT_DIR), show_default=True,
)
def list_audio(output_dir):
    """List previously generated audio files."""
    listing = list_audio_files(Path(output_dir))

    if listing.is_empty:
        console.print(f"[dim]📂 No audio files in {listing.directory}[/dim]")
        return

    table = Table(title=f"📂 {listing.directory}")
    table.add_column("File", style="bold")
    table.add_column("Size", justify="right")
    table.add_column("Modified", style="dim")

    for f in listing.files:
        table.add_row(f"🔊 {f.path.name}", f"{f.size_mb:.1f} MB", f.modified_display)

    table.add_section()
    table.add_row(
        f"[bold]{listing.count} files[/]",
        f"[bold]{listing.total_size_mb:.1f} MB[/]",
        "",
    )

    console.print(table)
