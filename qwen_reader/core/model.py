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
    """Immutable snapshot of model configuration."""

    model_id: str = field(
        default_factory=lambda: os.getenv("QWEN_TTS_MODEL", DEFAULT_MODEL_ID)
    )
    device: str = field(default_factory=_detect_device)


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

    _emit(on_progress, f"Loading model: {cfg.model_id}")
    _emit(on_progress, f"Device: {cfg.device}")

    t0 = time.time()
    _instance = Qwen3TTSModel.from_pretrained(
        cfg.model_id,
        device_map=cfg.device,
        dtype=torch.bfloat16,
    )
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
