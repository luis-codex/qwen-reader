"""Model management: lazy-loaded singleton for Qwen3-TTS.

Heavy imports (``torch``, ``qwen_tts``) are deferred until the model is
actually requested so that CLI ``--help`` and ``--list`` remain instant.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"

QUALITY_PRESETS: dict[str, str] = {
    "standard": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "fast": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
}


def _detect_device() -> str:
    """Return the best available device (cuda:0 → cpu)."""
    env = os.getenv("QWEN_TTS_DEVICE")
    if env:
        return env
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:0"
    except ImportError:
        pass
    return "cpu"


@dataclass(frozen=True)
class ModelConfig:
    """Immutable snapshot of model configuration.

    Attributes:
        model_id: HuggingFace model identifier.
        device: Compute device string (``cuda:0``, ``cpu``).
        quality: Quality preset name (``standard`` or ``fast``).
            When set, overrides *model_id* with the preset value.
        compile_model: Apply ``torch.compile`` for inference acceleration.
            Only effective on CUDA devices.
    """

    model_id: str = field(
        default_factory=lambda: os.getenv("QWEN_TTS_MODEL", DEFAULT_MODEL_ID)
    )
    device: str = field(default_factory=_detect_device)
    quality: str = "standard"
    compile_model: bool = True

    def resolved_model_id(self) -> str:
        """Return the model ID, applying quality preset if applicable."""
        if self.quality in QUALITY_PRESETS:
            return QUALITY_PRESETS[self.quality]
        return self.model_id


# ---------------------------------------------------------------------------
# Singleton holder
# ---------------------------------------------------------------------------

_instance: Any | None = None
_config: ModelConfig | None = None


def get_model(
    config: ModelConfig | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> Any:
    """Return the cached model, loading it on first call.

    Args:
        config: Optional override; defaults to ``ModelConfig()``.
        on_progress: Called with status messages during loading.

    Returns:
        A ``Qwen3TTSModel`` instance ready for inference.
    """
    global _instance, _config

    cfg = config or ModelConfig()

    if _instance is not None and _config == cfg:
        return _instance

    # Deferred heavy imports
    import torch
    from qwen_tts import Qwen3TTSModel

    resolved_id = cfg.resolved_model_id()
    _emit(on_progress, f"Loading model: {resolved_id}")
    _emit(on_progress, f"Device: {cfg.device}")
    _emit(on_progress, f"Quality: {cfg.quality}")

    t0 = time.time()
    _instance = Qwen3TTSModel.from_pretrained(
        resolved_id,
        device_map=cfg.device,
        dtype=torch.bfloat16,
    )

    # Apply torch.compile for inference acceleration (CUDA only)
    if cfg.compile_model and cfg.device.startswith("cuda"):
        try:
            _instance = torch.compile(_instance, mode="reduce-overhead")
            _emit(on_progress, "torch.compile applied ✅")
        except Exception:  # noqa: BLE001 — broad catch is intentional
            _emit(on_progress, "torch.compile skipped (unsupported)")

    _config = cfg

    elapsed = time.time() - t0
    _emit(on_progress, f"Model loaded in {elapsed:.1f}s")

    return _instance


def get_speakers(config: ModelConfig | None = None) -> list[str]:
    """Return the list of supported speaker names."""
    model = get_model(config)
    return list(model.get_supported_speakers())


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _emit(cb: Callable[[str], None] | None, msg: str) -> None:
    if cb is not None:
        cb(msg)
