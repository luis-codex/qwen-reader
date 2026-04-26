"""Infrastructure layer tests — core/model.py.

Tests for model configuration, quality presets, and model ID resolution.
These tests exercise the configuration logic without loading any real models.
Checklist items: T2, A5.
"""

from __future__ import annotations

import pytest

from qwen_reader.core.model import (
    DEFAULT_MODEL_ID,
    QUALITY_PRESETS,
    ModelConfig,
)


# =====================================================================
# ModelConfig
# =====================================================================


class TestModelConfig:
    """Verify model configuration defaults and overrides."""

    def test_defaults(self):
        cfg = ModelConfig()
        assert cfg.quality == "standard"
        assert cfg.compile_model is True

    def test_quality_presets_exist(self):
        assert "standard" in QUALITY_PRESETS
        assert "fast" in QUALITY_PRESETS

    def test_standard_resolves_to_1_7b(self):
        cfg = ModelConfig(quality="standard")
        assert "1.7B" in cfg.resolved_model_id()

    def test_fast_resolves_to_0_6b(self):
        cfg = ModelConfig(quality="fast")
        assert "0.6B" in cfg.resolved_model_id()

    def test_custom_model_id_with_unknown_quality(self):
        """When quality is not a known preset, resolved_model_id falls through."""
        cfg = ModelConfig(model_id="custom/model", quality="custom")
        assert cfg.resolved_model_id() == "custom/model"

    def test_default_model_id_matches_standard(self):
        assert DEFAULT_MODEL_ID == QUALITY_PRESETS["standard"]

    def test_compile_model_can_be_disabled(self):
        cfg = ModelConfig(compile_model=False)
        assert cfg.compile_model is False

    def test_frozen_dataclass(self):
        cfg = ModelConfig()
        with pytest.raises(AttributeError):
            cfg.quality = "fast"  # type: ignore[misc]
