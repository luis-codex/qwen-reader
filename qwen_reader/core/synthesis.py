"""Audio synthesis: orchestrates text cleaning, chunking, TTS, and file output.

This is the main "use-case" layer. It depends on ``core.text`` and
``core.model`` but contains **no UI logic** (no print, no argparse, no MCP).
Progress is reported via callbacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import soundfile as sf

from qwen_reader.core.model import ModelConfig, get_model
from qwen_reader.core.storage import DEFAULT_OUTPUT_DIR
from qwen_reader.core.text import (
    SUPPORTED_EXTENSIONS,
    chunk_text,
    clean_text,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class SynthesisConfig:
    """Parameters for a synthesis run.

    Attributes:
        language: Target language for TTS.
        speaker: Speaker voice name.
        instruct: Style instruction for the TTS engine.
        output_dir: Directory for generated audio files.
        silence_gap: Seconds of silence between chunks.
        chunk_size: Max characters per synthesis chunk.
            Larger values reduce overhead but may affect quality.
    """

    language: str = "Auto"
    speaker: str = "Aiden"
    instruct: str = (
        "Read this article in a natural, conversational tone, "
        "like a podcast narrator."
    )
    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)
    silence_gap: float = 0.4
    chunk_size: int = 500


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SynthesisResult:
    """Outcome of a successful synthesis."""

    path: Path
    duration_seconds: float
    size_bytes: int
    chunks_total: int
    speaker: str
    language: str

    @property
    def duration_display(self) -> str:
        m = int(self.duration_seconds // 60)
        s = int(self.duration_seconds % 60)
        return f"{m}m {s}s"

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def synthesize_text(
    text: str,
    output_name: str,
    config: SynthesisConfig | None = None,
    model_config: ModelConfig | None = None,
    on_chunk: Callable[[int, int, str], None] | None = None,
    on_model_progress: Callable[[str], None] | None = None,
) -> SynthesisResult:
    """Convert plain text to a WAV audio file.

    Args:
        text: Clean text to synthesize (already stripped of markup).
        output_name: Stem for the output file (without extension).
        config: Synthesis parameters; defaults to ``SynthesisConfig()``.
        model_config: Model parameters; defaults to ``ModelConfig()``.
        on_chunk: ``(current, total, preview)`` called before each chunk.
        on_model_progress: Forwarded to ``get_model`` for loading feedback.

    Returns:
        A ``SynthesisResult`` with metadata about the generated audio.

    Raises:
        ValueError: If *text* is empty.
        RuntimeError: If no audio could be generated.
    """
    if not text.strip():
        raise ValueError("Cannot synthesize empty text.")

    cfg = config or SynthesisConfig()
    model = get_model(model_config, on_progress=on_model_progress)

    chunks = chunk_text(text, max_chars=cfg.chunk_size)
    total = len(chunks)

    all_audio: list[np.ndarray] = []
    sample_rate: int | None = None

    for i, chunk in enumerate(chunks, 1):
        preview = chunk[:70].replace("\n", " ")
        if on_chunk:
            on_chunk(i, total, preview)

        wavs, sr = model.generate_custom_voice(
            text=chunk,
            language=cfg.language,
            speaker=cfg.speaker,
            instruct=cfg.instruct,
        )
        sample_rate = sr
        all_audio.append(wavs[0])

        # Silence gap between chunks
        silence = np.zeros(int(sr * cfg.silence_gap), dtype=wavs[0].dtype)
        all_audio.append(silence)

    if not all_audio or sample_rate is None:
        raise RuntimeError("No audio was generated.")

    # Concatenate and write
    full_audio = np.concatenate(all_audio)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = cfg.output_dir / f"{output_name}.wav"
    sf.write(str(out_path), full_audio, sample_rate)

    duration = len(full_audio) / sample_rate

    return SynthesisResult(
        path=out_path,
        duration_seconds=duration,
        size_bytes=out_path.stat().st_size,
        chunks_total=total,
        speaker=cfg.speaker,
        language=cfg.language,
    )


def synthesize_text_streaming(
    text: str,
    output_name: str,
    config: SynthesisConfig | None = None,
    model_config: ModelConfig | None = None,
    on_chunk: Callable[[int, int, str], None] | None = None,
    on_first_audio: Callable[[Path], None] | None = None,
    on_model_progress: Callable[[str], None] | None = None,
) -> SynthesisResult:
    """Convert text to audio with progressive WAV writing.

    Unlike ``synthesize_text``, this writes each chunk to disk as soon as
    it is generated, reducing the **Time To First Audio (TTFA)** — the
    user can start playback while synthesis continues.

    The WAV file is opened once with the correct sample rate and written
    to incrementally.  An ``on_first_audio`` callback fires after the
    first chunk is flushed, providing the file path for early playback.

    Args:
        text: Clean text to synthesize (already stripped of markup).
        output_name: Stem for the output file (without extension).
        config: Synthesis parameters; defaults to ``SynthesisConfig()``.
        model_config: Model parameters; defaults to ``ModelConfig()``.
        on_chunk: ``(current, total, preview)`` called before each chunk.
        on_first_audio: ``(path)`` called after the first chunk is written.
        on_model_progress: Forwarded to ``get_model`` for loading feedback.

    Returns:
        A ``SynthesisResult`` with metadata about the generated audio.

    Raises:
        ValueError: If *text* is empty.
        RuntimeError: If no audio could be generated.
    """
    if not text.strip():
        raise ValueError("Cannot synthesize empty text.")

    cfg = config or SynthesisConfig()
    model = get_model(model_config, on_progress=on_model_progress)

    chunks = chunk_text(text, max_chars=cfg.chunk_size)
    total = len(chunks)

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = cfg.output_dir / f"{output_name}.wav"

    sample_rate: int | None = None
    total_frames = 0
    sfile: sf.SoundFile | None = None

    try:
        for i, chunk in enumerate(chunks, 1):
            preview = chunk[:70].replace("\n", " ")
            if on_chunk:
                on_chunk(i, total, preview)

            wavs, sr = model.generate_custom_voice(
                text=chunk,
                language=cfg.language,
                speaker=cfg.speaker,
                instruct=cfg.instruct,
            )

            audio_data = wavs[0]
            silence = np.zeros(int(sr * cfg.silence_gap), dtype=audio_data.dtype)

            # Open WAV on first chunk (now we know sample_rate)
            if sfile is None:
                sample_rate = sr
                sfile = sf.SoundFile(
                    str(out_path),
                    mode="w",
                    samplerate=sr,
                    channels=1,
                    format="WAV",
                    subtype="FLOAT",
                )

            sfile.write(audio_data)
            sfile.write(silence)
            sfile.flush()
            total_frames += len(audio_data) + len(silence)

            # Signal that audio is available for playback
            if i == 1 and on_first_audio:
                on_first_audio(out_path)

    finally:
        if sfile is not None:
            sfile.close()

    if sample_rate is None or total_frames == 0:
        raise RuntimeError("No audio was generated.")

    duration = total_frames / sample_rate

    return SynthesisResult(
        path=out_path,
        duration_seconds=duration,
        size_bytes=out_path.stat().st_size,
        chunks_total=total,
        speaker=cfg.speaker,
        language=cfg.language,
    )


def synthesize_file(
    file_path: Path,
    output_name: str | None = None,
    config: SynthesisConfig | None = None,
    model_config: ModelConfig | None = None,
    on_chunk: Callable[[int, int, str], None] | None = None,
    on_first_audio: Callable[[Path], None] | None = None,
    on_model_progress: Callable[[str], None] | None = None,
    streaming: bool = False,
) -> SynthesisResult:
    """Read a file, clean its markup, and synthesize to audio.

    Args:
        file_path: Path to the source file.
        output_name: Override for the output filename stem.
        config: Synthesis parameters.
        model_config: Model parameters.
        on_chunk: Progress callback per chunk.
        on_first_audio: Callback fired after the first chunk is flushed
            (only used when *streaming* is True).
        on_model_progress: Progress callback for model loading.
        streaming: If True, use progressive WAV writing for lower TTFA.

    Returns:
        A ``SynthesisResult``.

    Raises:
        FileNotFoundError: If *file_path* does not exist.
        ValueError: If the file type is unsupported or content is empty.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type: {ext}. Supported: {supported}"
        )

    try:
        raw = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = file_path.read_text(encoding="latin-1")

    plain = clean_text(raw, ext)
    if not plain:
        raise ValueError(f"{file_path.name}: empty after cleaning markup.")

    stem = output_name or file_path.stem

    synth_fn = synthesize_text_streaming if streaming else synthesize_text

    kwargs: dict = dict(
        text=plain,
        output_name=stem,
        config=config,
        model_config=model_config,
        on_chunk=on_chunk,
        on_model_progress=on_model_progress,
    )
    if streaming:
        kwargs["on_first_audio"] = on_first_audio

    return synth_fn(**kwargs)
