"""Domain layer tests — core/storage.py.

These tests exercise file listing with real temporary files and
ZERO mocks. Checklist items: T1, A2.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from qwen_reader.core.storage import (
    AudioFileInfo,
    AudioFileList,
    DEFAULT_OUTPUT_DIR,
    list_audio_files,
)


# =====================================================================
# AudioFileInfo
# =====================================================================


class TestAudioFileInfo:
    """Verify computed properties on file metadata."""

    def test_size_mb(self):
        info = AudioFileInfo(path=Path("/f.wav"), size_bytes=2 * 1024 * 1024, modified_at=0)
        assert info.size_mb == pytest.approx(2.0)

    def test_modified_display_format(self):
        ts = time.mktime(time.strptime("2026-04-25 22:10", "%Y-%m-%d %H:%M"))
        info = AudioFileInfo(path=Path("/f.wav"), size_bytes=0, modified_at=ts)
        assert info.modified_display == "2026-04-25 22:10"


# =====================================================================
# AudioFileList
# =====================================================================


class TestAudioFileList:
    """Verify aggregate properties."""

    def test_empty_list(self):
        listing = AudioFileList(directory=Path("/tmp"), files=())
        assert listing.is_empty
        assert listing.count == 0
        assert listing.total_size_mb == 0.0

    def test_populated_list(self):
        files = (
            AudioFileInfo(path=Path("/a.wav"), size_bytes=1024 * 1024, modified_at=0),
            AudioFileInfo(path=Path("/b.wav"), size_bytes=2 * 1024 * 1024, modified_at=0),
        )
        listing = AudioFileList(directory=Path("/tmp"), files=files)
        assert not listing.is_empty
        assert listing.count == 2
        assert listing.total_size_mb == pytest.approx(3.0)


# =====================================================================
# list_audio_files
# =====================================================================


class TestListAudioFiles:
    """Integration tests with real temp files."""

    def test_empty_directory(self, tmp_path: Path):
        result = list_audio_files(tmp_path)
        assert result.is_empty
        assert result.directory == tmp_path

    def test_finds_wav_files(self, tmp_path: Path):
        (tmp_path / "a.wav").write_bytes(b"\x00" * 512)
        (tmp_path / "b.wav").write_bytes(b"\x00" * 1024)
        (tmp_path / "c.txt").write_text("not audio")

        result = list_audio_files(tmp_path)
        assert result.count == 2
        names = [f.path.name for f in result.files]
        assert "a.wav" in names
        assert "b.wav" in names
        assert "c.txt" not in names

    def test_sorted_by_name(self, tmp_path: Path):
        (tmp_path / "zebra.wav").write_bytes(b"\x00")
        (tmp_path / "alpha.wav").write_bytes(b"\x00")

        result = list_audio_files(tmp_path)
        assert result.files[0].path.name == "alpha.wav"
        assert result.files[1].path.name == "zebra.wav"

    def test_file_sizes_correct(self, tmp_path: Path):
        (tmp_path / "test.wav").write_bytes(b"\x00" * 2048)

        result = list_audio_files(tmp_path)
        assert result.files[0].size_bytes == 2048

    def test_default_dir_is_path(self):
        assert isinstance(DEFAULT_OUTPUT_DIR, Path)
