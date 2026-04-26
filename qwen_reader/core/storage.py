"""Audio file storage: output directory defaults and file listing.

This module owns all file-system queries related to generated audio.
It has no dependency on the CLI or presentation layers — stdlib only.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Default output directory
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR = Path(
    os.getenv("QWEN_TTS_OUTPUT_DIR", str(Path.home() / "qwen-reader-audio"))
)

# ---------------------------------------------------------------------------
# Data objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AudioFileInfo:
    """Metadata for a single generated audio file."""

    path: Path
    size_bytes: int
    modified_at: float

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def modified_display(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(self.modified_at))


@dataclass(frozen=True)
class AudioFileList:
    """Result of listing audio files in a directory."""

    directory: Path
    files: tuple[AudioFileInfo, ...]

    @property
    def total_size_mb(self) -> float:
        return sum(f.size_mb for f in self.files)

    @property
    def count(self) -> int:
        return len(self.files)

    @property
    def is_empty(self) -> bool:
        return len(self.files) == 0


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


def list_audio_files(output_dir: Path | None = None) -> AudioFileList:
    """List WAV files in the output directory, sorted by name.

    Args:
        output_dir: Directory to scan. Defaults to ``DEFAULT_OUTPUT_DIR``.

    Returns:
        An ``AudioFileList`` with metadata for each file found.
    """
    directory = output_dir or DEFAULT_OUTPUT_DIR
    wav_files = sorted(directory.glob("*.wav"))

    files = tuple(
        AudioFileInfo(
            path=f,
            size_bytes=f.stat().st_size,
            modified_at=f.stat().st_mtime,
        )
        for f in wav_files
    )

    return AudioFileList(directory=directory, files=files)
