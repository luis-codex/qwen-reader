"""Use-Case layer tests — core/synthesis.py.

These tests mock the Infrastructure layer (model) and exercise the
orchestration logic: chunking → TTS → concatenation → WAV output.
Checklist items: T2, R1, R2, R3.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qwen_reader.core.synthesis import (
    DEFAULT_OUTPUT_DIR,
    SynthesisConfig,
    SynthesisResult,
    synthesize_file,
    synthesize_text,
    synthesize_text_streaming,
)


# =====================================================================
# synthesize_text
# =====================================================================


class TestSynthesizeText:
    """Test the core text→audio pipeline with a mocked model."""

    def test_basic_synthesis(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)

        result = synthesize_text(
            text="Hello world. This is a test sentence.",
            output_name="test_out",
            config=config,
        )

        assert isinstance(result, SynthesisResult)
        assert result.path.exists()
        assert result.path.suffix == ".wav"
        assert result.path.name == "test_out.wav"
        assert result.duration_seconds > 0
        assert result.size_bytes > 0
        assert result.chunks_total >= 1
        assert result.speaker == "Aiden"
        assert result.language == "Auto"

    def test_custom_speaker_and_language(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(
            speaker="Vivian",
            language="Spanish",
            output_dir=tmp_path,
        )

        result = synthesize_text(
            text="Hola mundo.",
            output_name="spanish",
            config=config,
        )

        assert result.speaker == "Vivian"
        assert result.language == "Spanish"

    def test_empty_text_raises_value_error(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)

        with pytest.raises(ValueError, match="empty"):
            synthesize_text(text="", output_name="fail", config=config)

    def test_whitespace_only_raises_value_error(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)

        with pytest.raises(ValueError, match="empty"):
            synthesize_text(text="   \n\t  ", output_name="fail", config=config)

    def test_callback_receives_progress(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)
        calls: list[tuple[int, int, str]] = []

        def on_chunk(current: int, total: int, preview: str):
            calls.append((current, total, preview))

        synthesize_text(
            text="First sentence. Second sentence.",
            output_name="progress",
            config=config,
            on_chunk=on_chunk,
        )

        assert len(calls) >= 1
        # last call should have current == total
        last = calls[-1]
        assert last[0] == last[1]

    def test_creates_output_dir_if_missing(self, patch_model, tmp_path: Path):
        nested = tmp_path / "deep" / "nested" / "dir"
        config = SynthesisConfig(output_dir=nested)

        result = synthesize_text(
            text="Test creating dirs.",
            output_name="nested_test",
            config=config,
        )

        assert nested.exists()
        assert result.path.parent == nested

    def test_multi_chunk_text(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)
        # Generate text long enough to force multiple chunks
        text = ". ".join(f"Sentence number {i}" for i in range(50)) + "."

        result = synthesize_text(
            text=text,
            output_name="multi",
            config=config,
        )

        assert result.chunks_total > 1

    def test_larger_chunk_size_fewer_chunks(self, patch_model, tmp_path: Path):
        text = ". ".join(f"Sentence number {i}" for i in range(50)) + "."

        result_small = synthesize_text(
            text=text,
            output_name="small_chunks",
            config=SynthesisConfig(output_dir=tmp_path, chunk_size=200),
        )
        result_large = synthesize_text(
            text=text,
            output_name="large_chunks",
            config=SynthesisConfig(output_dir=tmp_path, chunk_size=800),
        )

        assert result_large.chunks_total < result_small.chunks_total


# =====================================================================
# synthesize_text_streaming
# =====================================================================


class TestSynthesizeTextStreaming:
    """Test progressive WAV writing (streaming mode)."""

    def test_basic_streaming(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)

        result = synthesize_text_streaming(
            text="Hello world. This is streaming.",
            output_name="stream_test",
            config=config,
        )

        assert isinstance(result, SynthesisResult)
        assert result.path.exists()
        assert result.path.suffix == ".wav"
        assert result.duration_seconds > 0
        assert result.size_bytes > 0

    def test_on_first_audio_called(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)
        calls: list[Path] = []

        result = synthesize_text_streaming(
            text="First chunk. Second chunk. Third chunk.",
            output_name="ttfa",
            config=config,
            on_first_audio=lambda p: calls.append(p),
        )

        assert len(calls) == 1
        assert calls[0] == result.path

    def test_multi_chunk_streaming(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)
        text = ". ".join(f"Sentence number {i}" for i in range(50)) + "."

        result = synthesize_text_streaming(
            text=text,
            output_name="multi_stream",
            config=config,
        )

        assert result.chunks_total > 1
        assert result.path.exists()
        assert result.duration_seconds > 0

    def test_empty_text_raises(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)

        with pytest.raises(ValueError, match="empty"):
            synthesize_text_streaming(
                text="", output_name="fail", config=config,
            )

    def test_file_written_progressively(self, patch_model, tmp_path: Path):
        """Verify the WAV file exists after on_first_audio fires."""
        config = SynthesisConfig(output_dir=tmp_path)
        file_existed_at_first_audio: list[bool] = []

        def check_file(path: Path):
            file_existed_at_first_audio.append(path.exists())

        synthesize_text_streaming(
            text="First sentence. Second sentence. Third sentence.",
            output_name="progressive",
            config=config,
            on_first_audio=check_file,
        )

        assert file_existed_at_first_audio == [True]

    def test_callback_receives_progress(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)
        calls: list[tuple[int, int, str]] = []

        synthesize_text_streaming(
            text="First. Second. Third.",
            output_name="cb",
            config=config,
            on_chunk=lambda c, t, p: calls.append((c, t, p)),
        )

        assert len(calls) >= 1
        last = calls[-1]
        assert last[0] == last[1]  # current == total on last call

    def test_creates_output_dir(self, patch_model, tmp_path: Path):
        nested = tmp_path / "deep" / "streaming"
        config = SynthesisConfig(output_dir=nested)

        result = synthesize_text_streaming(
            text="Test dirs.", output_name="nested", config=config,
        )

        assert nested.exists()
        assert result.path.parent == nested


# =====================================================================
# synthesize_file
# =====================================================================


class TestSynthesizeFile:
    """Test file-level synthesis (read → clean → synthesize)."""

    def test_markdown_file(self, patch_model, tmp_md: Path, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)

        result = synthesize_file(file_path=tmp_md, config=config)

        assert result.path.exists()
        assert result.path.stem == "sample"  # derived from filename

    def test_plain_text_file(self, patch_model, tmp_txt: Path, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)

        result = synthesize_file(file_path=tmp_txt, config=config)

        assert result.path.exists()

    def test_custom_output_name(self, patch_model, tmp_md: Path, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)

        result = synthesize_file(
            file_path=tmp_md,
            output_name="custom",
            config=config,
        )

        assert result.path.name == "custom.wav"

    def test_file_not_found(self, patch_model, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)
        missing = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError, match="not found"):
            synthesize_file(file_path=missing, config=config)

    def test_unsupported_extension(self, patch_model, tmp_unsupported: Path, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)

        with pytest.raises(ValueError, match="Unsupported"):
            synthesize_file(file_path=tmp_unsupported, config=config)

    def test_empty_after_cleaning(self, patch_model, tmp_empty_md: Path, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)

        with pytest.raises(ValueError, match="empty"):
            synthesize_file(file_path=tmp_empty_md, config=config)

    def test_streaming_mode(self, patch_model, tmp_md: Path, tmp_path: Path):
        config = SynthesisConfig(output_dir=tmp_path)
        first_audio_calls: list[Path] = []

        result = synthesize_file(
            file_path=tmp_md,
            config=config,
            on_first_audio=lambda p: first_audio_calls.append(p),
            streaming=True,
        )

        assert result.path.exists()
        assert len(first_audio_calls) == 1
        assert first_audio_calls[0] == result.path


# =====================================================================
# SynthesisResult
# =====================================================================


class TestSynthesisResult:
    """Verify computed properties."""

    def test_duration_display(self):
        r = SynthesisResult(
            path=Path("/fake.wav"),
            duration_seconds=125.7,
            size_bytes=1_000_000,
            chunks_total=5,
            speaker="Aiden",
            language="English",
        )
        assert r.duration_display == "2m 5s"

    def test_size_mb(self):
        r = SynthesisResult(
            path=Path("/fake.wav"),
            duration_seconds=60,
            size_bytes=2 * 1024 * 1024,
            chunks_total=1,
            speaker="Aiden",
            language="Auto",
        )
        assert r.size_mb == pytest.approx(2.0)


# =====================================================================
# SynthesisConfig
# =====================================================================


class TestSynthesisConfig:
    """Verify defaults and mutability."""

    def test_defaults(self):
        cfg = SynthesisConfig()
        assert cfg.language == "Auto"
        assert cfg.speaker == "Aiden"
        assert cfg.silence_gap == 0.4
        assert cfg.chunk_size == 500
        assert cfg.output_dir == DEFAULT_OUTPUT_DIR

    def test_custom_values(self):
        cfg = SynthesisConfig(language="Chinese", speaker="Eric", silence_gap=0.2)
        assert cfg.language == "Chinese"
        assert cfg.speaker == "Eric"
        assert cfg.silence_gap == 0.2

    def test_custom_chunk_size(self):
        cfg = SynthesisConfig(chunk_size=800)
        assert cfg.chunk_size == 800
