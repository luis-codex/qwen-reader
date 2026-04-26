"""Central test fixtures for qwen-reader.

This is the single source of truth for test isolation:
- ``FakeModel``: deterministic stub (0.1s silence per chunk, 24 kHz).
- ``patch_model``: monkeypatches ``get_model`` / ``get_speakers`` in both
  ``core.model`` and ``core.synthesis`` so no test ever loads a real model.
- File fixtures: reusable sample files for each supported format.

Rules:
  1. No test file should create its own model fake — use ``patch_model``.
  2. All temp files go through ``tmp_path`` (pytest built-in).
  3. Fixtures are function-scoped by default (no cross-test state).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Fake model (replaces torch + qwen_tts in tests)
# ---------------------------------------------------------------------------

@dataclass
class FakeModel:
    """Stub that returns silence instead of running real TTS inference."""

    sample_rate: int = 24_000
    speakers: list[str] | None = None

    def __post_init__(self):
        if self.speakers is None:
            self.speakers = ["Aiden", "Dylan", "Eric", "Ryan", "Serena", "Vivian"]

    def generate_custom_voice(
        self,
        text: str,
        language: str = "Auto",
        speaker: str = "Aiden",
        instruct: str = "",
    ) -> tuple[list[np.ndarray], int]:
        """Return a short silent audio array for each call."""
        # 0.1 seconds of silence per chunk
        samples = int(self.sample_rate * 0.1)
        wav = np.zeros(samples, dtype=np.float32)
        return [wav], self.sample_rate

    def get_supported_speakers(self) -> list[str]:
        return list(self.speakers)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_model() -> FakeModel:
    """Provide a FakeModel instance for direct use."""
    return FakeModel()


@pytest.fixture
def patch_model(monkeypatch: pytest.MonkeyPatch, fake_model: FakeModel):
    """Patch ``get_model`` across both model and synthesis modules.

    This ensures any code that calls ``get_model()`` gets the fake,
    regardless of which module imported it.
    """
    stub = lambda *a, **kw: fake_model  # noqa: E731

    monkeypatch.setattr("qwen_reader.core.model.get_model", stub)
    monkeypatch.setattr("qwen_reader.core.model.get_speakers", lambda cfg=None: fake_model.get_supported_speakers())
    monkeypatch.setattr("qwen_reader.core.synthesis.get_model", stub)

    return fake_model


@pytest.fixture
def tmp_md(tmp_path: Path) -> Path:
    """Create a temporary markdown file with sample content."""
    f = tmp_path / "sample.md"
    f.write_text(
        "# Hello World\n\n"
        "This is a **test** article.\n\n"
        "It has [a link](https://example.com) and `code`.\n",
        encoding="utf-8",
    )
    return f


@pytest.fixture
def tmp_txt(tmp_path: Path) -> Path:
    """Create a temporary plain-text file."""
    f = tmp_path / "plain.txt"
    f.write_text("Just a plain sentence.", encoding="utf-8")
    return f


@pytest.fixture
def tmp_empty_md(tmp_path: Path) -> Path:
    """Create a markdown file that becomes empty after stripping."""
    f = tmp_path / "empty.md"
    f.write_text("```\ncode only\n```\n", encoding="utf-8")
    return f


@pytest.fixture
def tmp_unsupported(tmp_path: Path) -> Path:
    """Create a file with an unsupported extension."""
    f = tmp_path / "data.csv"
    f.write_text("col1,col2\n1,2\n", encoding="utf-8")
    return f
