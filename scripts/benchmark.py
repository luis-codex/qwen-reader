"""Benchmark script: measure inference latency across configurations.

Runs synthesis with different chunk sizes and quality presets,
then outputs a comparison table. Uses the FakeModel by default
for CI compatibility; pass --live to benchmark against the real model.

Usage:
    python scripts/benchmark.py                  # dry-run with FakeModel
    python scripts/benchmark.py --live            # real GPU inference
    python scripts/benchmark.py --live --text-file article.md
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Force UTF-8 on Windows to avoid cp1252 emoji encoding errors
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure the package is importable from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qwen_reader.core.model import ModelConfig
from qwen_reader.core.synthesis import SynthesisConfig, SynthesisResult, synthesize_text
from qwen_reader.core.text import chunk_text, clean_text


# ---------------------------------------------------------------------------
# Sample texts
# ---------------------------------------------------------------------------

SHORT_TEXT = (
    "Artificial intelligence is transforming how we interact with technology. "
    "Voice synthesis has become remarkably natural in recent years."
)

MEDIUM_TEXT = (
    "Artificial intelligence is transforming how we interact with technology. "
    "Voice synthesis has become remarkably natural in recent years. "
    "Modern text-to-speech systems can produce audio that is nearly "
    "indistinguishable from human speech. These advances have opened up "
    "new possibilities in accessibility, education, and entertainment. "
    "From audiobooks to virtual assistants, TTS technology is everywhere. "
    "The key challenge remains reducing inference latency while maintaining "
    "quality. Users expect real-time or near-real-time responses. "
    "Any perceptible delay can significantly impact user adoption. "
    "This benchmark measures the trade-offs between speed and quality "
    "across different configuration settings."
)

LONG_TEXT = " ".join([MEDIUM_TEXT] * 5)


# ---------------------------------------------------------------------------
# Benchmark configuration
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkScenario:
    name: str
    quality: str
    chunk_size: int
    text: str
    text_label: str


def build_scenarios(text_override: str | None = None) -> list[BenchmarkScenario]:
    """Generate the matrix of scenarios to benchmark."""
    texts = {
        "short (~50w)": SHORT_TEXT,
        "medium (~120w)": MEDIUM_TEXT,
        "long (~600w)": LONG_TEXT,
    }

    if text_override:
        texts = {"custom": text_override}

    configs = [
        ("standard/500", "standard", 500),
        ("standard/800", "standard", 800),
        ("fast/500", "fast", 500),
        ("fast/800", "fast", 800),
    ]

    scenarios = []
    for text_label, text in texts.items():
        for config_name, quality, chunk_size in configs:
            scenarios.append(BenchmarkScenario(
                name=f"{config_name} | {text_label}",
                quality=quality,
                chunk_size=chunk_size,
                text=text,
                text_label=text_label,
            ))

    return scenarios


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    scenario: str
    quality: str
    chunk_size: int
    text_label: str
    chunks: int
    duration_s: float
    audio_duration_s: float
    rtf: float  # Real-Time Factor = audio_duration / wall_time


def run_benchmark(
    scenarios: list[BenchmarkScenario],
    output_dir: Path,
    device: str,
    live: bool,
) -> list[BenchmarkResult]:
    """Execute each scenario and collect timing data."""
    results: list[BenchmarkResult] = []

    if not live:
        # Patch with FakeModel for dry-run
        import numpy as np
        from tests.conftest import FakeModel

        fake = FakeModel()
        import qwen_reader.core.model as model_mod
        import qwen_reader.core.synthesis as synth_mod

        original_get_model = model_mod.get_model
        model_mod.get_model = lambda *a, **kw: fake
        synth_mod.get_model = lambda *a, **kw: fake

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] {scenario.name}")

        scfg = SynthesisConfig(
            output_dir=output_dir,
            chunk_size=scenario.chunk_size,
        )
        mcfg = ModelConfig(
            device=device,
            quality=scenario.quality,
            compile_model=live,  # only compile on live runs
        )

        # Count chunks for reporting
        chunks = chunk_text(scenario.text, max_chars=scenario.chunk_size)
        n_chunks = len(chunks)
        print(f"  Text: {len(scenario.text)} chars → {n_chunks} chunks "
              f"(chunk_size={scenario.chunk_size})")

        t0 = time.perf_counter()
        result = synthesize_text(
            text=scenario.text,
            output_name=f"bench_{i}",
            config=scfg,
            model_config=mcfg,
        )
        elapsed = time.perf_counter() - t0

        rtf = result.duration_seconds / elapsed if elapsed > 0 else float("inf")

        results.append(BenchmarkResult(
            scenario=scenario.name,
            quality=scenario.quality,
            chunk_size=scenario.chunk_size,
            text_label=scenario.text_label,
            chunks=n_chunks,
            duration_s=elapsed,
            audio_duration_s=result.duration_seconds,
            rtf=rtf,
        ))

        print(f"  Wall time: {elapsed:.2f}s | Audio: {result.duration_seconds:.1f}s "
              f"| RTF: {rtf:.2f}x")

    if not live:
        model_mod.get_model = original_get_model
        synth_mod.get_model = original_get_model

    return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(results: list[BenchmarkResult]) -> None:
    """Print a formatted comparison table."""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)

    header = f"{'Scenario':<30} {'Chunks':>6} {'Wall(s)':>8} {'Audio(s)':>8} {'RTF':>6}"
    print(header)
    print("-" * len(header))

    for r in results:
        print(f"{r.scenario:<30} {r.chunks:>6} {r.duration_s:>8.2f} "
              f"{r.audio_duration_s:>8.1f} {r.rtf:>6.2f}x")

    # Summary: compare standard vs fast
    print("\n" + "-" * 40)
    print("SPEED COMPARISON (same text, chunk_size=500)")
    print("-" * 40)

    std_results = [r for r in results if r.quality == "standard" and r.chunk_size == 500]
    fast_results = [r for r in results if r.quality == "fast" and r.chunk_size == 500]

    for std, fast in zip(std_results, fast_results):
        if std.text_label == fast.text_label:
            speedup = std.duration_s / fast.duration_s if fast.duration_s > 0 else 0
            print(f"  {std.text_label}: standard={std.duration_s:.2f}s "
                  f"fast={fast.duration_s:.2f}s → {speedup:.1f}x speedup")

    # Summary: chunk size impact
    print("\n" + "-" * 40)
    print("CHUNK SIZE IMPACT (standard quality)")
    print("-" * 40)

    c500 = [r for r in results if r.quality == "standard" and r.chunk_size == 500]
    c800 = [r for r in results if r.quality == "standard" and r.chunk_size == 800]

    for r500, r800 in zip(c500, c800):
        if r500.text_label == r800.text_label:
            chunk_reduction = (1 - r800.chunks / r500.chunks) * 100 if r500.chunks > 0 else 0
            time_change = (1 - r800.duration_s / r500.duration_s) * 100 if r500.duration_s > 0 else 0
            print(f"  {r500.text_label}: 500→800 chunks "
                  f"{r500.chunks}→{r800.chunks} ({chunk_reduction:.0f}% fewer) "
                  f"| time {time_change:+.0f}%")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Benchmark qwen-reader inference latency")
    parser.add_argument("--live", action="store_true",
                        help="Run against the real model (requires GPU)")
    parser.add_argument("--device", default="cuda:0",
                        help="Compute device (default: cuda:0)")
    parser.add_argument("--text-file", type=str, default=None,
                        help="Path to a text/markdown file to benchmark with")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory for benchmark WAV files")
    args = parser.parse_args()

    # Output dir
    if args.output_dir:
        out = Path(args.output_dir)
    else:
        out = Path(__file__).parent.parent / ".benchmark_output"
    out.mkdir(parents=True, exist_ok=True)

    # Optional custom text
    custom_text = None
    if args.text_file:
        p = Path(args.text_file)
        if not p.exists():
            print(f"Error: {p} not found")
            sys.exit(1)
        raw = p.read_text(encoding="utf-8")
        ext = p.suffix.lower()
        custom_text = clean_text(raw, ext)

    mode = "LIVE (real model)" if args.live else "DRY-RUN (FakeModel)"
    print(f"🔬 qwen-reader Benchmark — {mode}")
    print(f"   Device: {args.device}")
    print(f"   Output: {out}")

    scenarios = build_scenarios(custom_text)
    results = run_benchmark(scenarios, out, args.device, args.live)
    print_report(results)


if __name__ == "__main__":
    main()
