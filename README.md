<img width="14135" height="6792" alt="image" src="https://github.com/user-attachments/assets/bd638001-e12b-49dd-8acf-2c33e83f427e" />
<div align="center">

# 🎧 qwen-reader

**Convert articles and documents to high-quality audio using Qwen3-TTS.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-82%20passed-brightgreen)](#-testing)
[![Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen)](#-coverage)
[![Powered by](https://img.shields.io/badge/powered%20by-Qwen3--TTS-purple)](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)

Turn your markdown notes, articles, and text files into podcast-style audio you can listen to anywhere — powered by local AI inference on your GPU.

</div>

---

## ✨ Features

- **Multi-format support** — `.md`, `.markdown`, `.txt`, `.rst`, `.text`
- **Intelligent text cleaning** — Strips markdown syntax, code blocks, links, and front-matter before synthesis
- **Batch processing** — Convert multiple files in a single command
- **Multiple voices** — 7+ built-in speakers with natural, conversational tone
- **Chunked synthesis** — Splits long text at sentence boundaries for consistent quality
- **Rich CLI output** — Progress bars, tables, and styled panels via [Rich](https://github.com/Textualize/rich)
- **GPU accelerated** — Runs on CUDA for fast inference

## 📦 Installation

### Prerequisites

- Python 3.10+
- NVIDIA GPU with CUDA support (recommended) or CPU
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
git clone https://github.com/luis-codex/qwen-reader.git
cd qwen-reader

# Create virtual environment and install
uv venv
uv pip install -e .

# Install PyTorch with CUDA support (adjust cu128 to your CUDA version)
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
```

> [!NOTE]
> The first run downloads the model (~3.5 GB) from HuggingFace. Subsequent runs load it from cache in ~30s.

### Developer setup

```bash
# Install with dev dependencies (pytest, pytest-cov)
uv pip install -e ".[dev]"

# Run the test suite
python -m pytest
```

### Make it globally available

Add the virtual environment's `Scripts` (Windows) or `bin` (Linux/macOS) directory to your system `PATH`:

```powershell
# Windows (PowerShell) — run once
$scriptsPath = "$PWD\.venv\Scripts"
[Environment]::SetEnvironmentVariable("Path", "$([Environment]::GetEnvironmentVariable('Path', 'User'));$scriptsPath", "User")
```

```bash
# Linux / macOS — add to ~/.bashrc or ~/.zshrc
export PATH="/path/to/qwen-reader/.venv/bin:$PATH"
```

Then open a new terminal and use `qwen-reader` from anywhere.

## 🚀 Usage

```
Usage: qwen-reader [OPTIONS] COMMAND [ARGS]

Commands:
  read      Convert one or more files to audio
  speak     Convert inline text to audio
  speakers  List available TTS voices
  list      List previously generated audio files
```

### Convert files to audio

```bash
# Single file
qwen-reader read article.md

# Multiple files at once
qwen-reader read notes.txt report.md spec.rst

# Choose a voice and language
qwen-reader read article.md --speaker Ryan --lang English

# Custom output directory
qwen-reader read article.md --output-dir ./my-audio

# Custom output filename
qwen-reader read article.md --name my-podcast
```

### Speak inline text

```bash
qwen-reader speak "Hello world, this is a test."
qwen-reader speak "Hola mundo, esto es una prueba." --lang Spanish --speaker Vivian
```

### Explore voices

```bash
qwen-reader speakers
```

```
  🎙️ Available Speakers
┌───┬─────────┐
│ # │ Name    │
├───┼─────────┤
│ 1 │ Aiden   │
│ 2 │ Dylan   │
│ 3 │ Eric    │
│ 4 │ Ryan    │
│ 5 │ Serena  │
│ 6 │ Vivian  │
│ … │ …       │
└───┴─────────┘
```

### Browse generated files

```bash
qwen-reader list
```

```
         📂 ~/qwen-reader-audio
┌──────────────────────┬────────┬──────────────────┐
│ File                 │   Size │ Modified         │
├──────────────────────┼────────┼──────────────────┤
│ 🔊 article.wav       │ 4.2 MB │ 2026-04-25 22:10 │
│ 🔊 spoken_text.wav   │ 0.1 MB │ 2026-04-25 21:52 │
├──────────────────────┼────────┼──────────────────┤
│ 2 files              │ 4.3 MB │                  │
└──────────────────────┴────────┴──────────────────┘
```

### Full option reference

| Option         | Short | Default               | Description                                      |
| -------------- | ----- | --------------------- | ------------------------------------------------ |
| `--speaker`    | `-s`  | `Aiden`               | TTS voice to use                                 |
| `--lang`       | `-l`  | `Auto`                | Language (Auto, English, Chinese, Spanish, etc.) |
| `--instruct`   | `-i`  | _conversational_      | Style instruction for the TTS engine             |
| `--output-dir` | `-o`  | `~/qwen-reader-audio` | Output directory                                 |
| `--name`       | `-n`  | _filename stem_       | Custom output filename (without extension)       |
| `--device`     | `-d`  | `cuda:0`              | Compute device (`cuda:0`, `cpu`)                 |
| `--version`    | `-v`  | —                     | Show version                                     |
| `--help`       | `-h`  | —                     | Show help                                        |

## 🗂️ Supported file types

| Extension          | Processing                                                              |
| ------------------ | ----------------------------------------------------------------------- |
| `.md`, `.markdown` | Strips YAML front-matter, code blocks, links, images, emphasis, headers |
| `.rst`             | Strips directives, section underlines, inline markup                    |
| `.txt`, `.text`    | Passed through as-is                                                    |

## 🏗️ Architecture

This project follows **Clean Architecture** with strict layer boundaries and a unidirectional dependency rule.

### Layer diagram

```
┌───────────────────────────────────────────────────────────┐
│  Interface Layer                           cli/           │
│  app.py · commands.py · options.py · rendering.py         │
│  click + rich · args, output, exit codes                  │
├───────────────────────────────────────────────────────────┤
│  Use-Case Layer                    core/synthesis.py      │
│  Orchestration · chunking → TTS → WAV assembly            │
├──────────────────────┬────────────────────────────────────┤
│  Domain Layer        │  Infrastructure Layer              │
│  core/text.py        │  core/model.py                     │
│  core/storage.py     │  Model lifecycle, GPU management   │
│  Pure transforms,    │  torch, qwen_tts (deferred import) │
│  file listing        │                                    │
│  stdlib only         │                                    │
└──────────────────────┴────────────────────────────────────┘
```

### Dependency rule

```
Interface → Use-Case → Domain
                     → Infrastructure → External Systems
```

No inner layer ever imports an outer layer. Core modules never call `print()`, `sys.exit()`, or import `click`/`rich`.

### Project structure

```
qwen_reader/
├── __init__.py              # Package version
├── __main__.py              # python -m qwen_reader entry
├── cli/
│   ├── __init__.py          # Re-exports cli, main
│   ├── app.py               # Click group, entry point, Windows UTF-8
│   ├── commands.py          # read, speak, speakers, list commands
│   ├── options.py           # Shared option decorators
│   └── rendering.py         # Rich console, progress bars, result panel
└── core/
    ├── __init__.py          # Docstring only — no re-exports
    ├── text.py              # Domain: text cleaning & chunking
    ├── storage.py           # Domain: audio file listing & output dir
    ├── model.py             # Infrastructure: lazy model singleton
    └── synthesis.py         # Use-Case: audio generation orchestration

tests/
├── conftest.py              # FakeModel stub + shared fixtures
├── test_text.py             # Domain layer — no mocks, stdlib only
├── test_storage.py          # Domain layer — file listing, no mocks
├── test_synthesis.py        # Use-Case layer — mocked infrastructure
└── test_cli.py              # Interface layer — click CliRunner
```

### Layer contract

| Layer              | Module(s)                                                             | Responsibility                              | Allowed deps                             | Forbidden                 |
| ------------------ | --------------------------------------------------------------------- | ------------------------------------------- | ---------------------------------------- | ------------------------- |
| **Interface**      | `cli/app.py`, `cli/commands.py`, `cli/options.py`, `cli/rendering.py` | Parse args, render output, map exit codes   | click, rich, Use-Case                    | torch, numpy, direct I/O  |
| **Use-Case**       | `core/synthesis.py`                                                   | Orchestrate domain + infra into workflows   | Domain, Infrastructure, numpy, soundfile | click, rich, `print()`    |
| **Domain**         | `core/text.py`, `core/storage.py`                                     | Pure text transforms, file listing          | **stdlib only** (`re`, `os`, `time`)     | Any third-party package   |
| **Infrastructure** | `core/model.py`                                                       | External system lifecycle (model load, GPU) | torch, qwen_tts, stdlib                  | click, rich, domain logic |

### Cross-layer communication

| Mechanism                 | Example                             | Purpose                                           |
| ------------------------- | ----------------------------------- | ------------------------------------------------- |
| `@dataclass(frozen=True)` | `ModelConfig`, `SynthesisResult`    | Immutable snapshots passed between layers         |
| `@dataclass` (mutable)    | `SynthesisConfig`                   | Aggregates user inputs before passing down        |
| Callbacks                 | `on_chunk(current, total, preview)` | Interface layer decides _how_ to display progress |

## 🧪 Testing

### Strategy

Each architectural layer has its own test file with a tailored testing approach:

| File                | Layer     | Tests | Mocking                            | Speed            |
| ------------------- | --------- | ----- | ---------------------------------- | ---------------- |
| `test_text.py`      | Domain    | 37    | None — pure functions, stdlib only | < 1ms per test   |
| `test_storage.py`   | Domain    | 9     | None — real temp files             | < 1ms per test   |
| `test_synthesis.py` | Use-Case  | 17    | `FakeModel` stubs infrastructure   | < 100ms per test |
| `test_cli.py`       | Interface | 19    | `patch_model` + `CliRunner`        | < 500ms per test |

### Running tests

```bash
# Quick run
python -m pytest

# With coverage report
python -m pytest --cov=qwen_reader --cov-report=term-missing

# Single layer
python -m pytest tests/test_text.py -v
```

### Coverage

| Module              | Stmts   | Miss   | Cover    |
| ------------------- | ------- | ------ | -------- |
| `__init__.py`       | 1       | 0      | 100%     |
| `cli/app.py`        | 22      | 2      | 91%      |
| `cli/commands.py`   | 103     | 8      | 92%      |
| `cli/options.py`    | 12      | 0      | **100%** |
| `cli/rendering.py`  | 22      | 0      | **100%** |
| `core/text.py`      | 52      | 0      | **100%** |
| `core/storage.py`   | 35      | 0      | **100%** |
| `core/synthesis.py` | 74      | 3      | 96%      |
| `core/model.py`     | 33      | 15     | 55%      |
| **Total**           | **358** | **30** | **92%**  |

> [!NOTE]
> `core/model.py` coverage is lower by design — it wraps `torch` and `qwen_tts` which are mocked in tests. The remaining uncovered lines are the actual model loading path that requires a GPU.

### Coverage targets

| Layer     | Minimum | Target | Actual  |
| --------- | ------- | ------ | ------- |
| Domain    | 90%     | 100%   | ✅ 100% |
| Use-Case  | 80%     | 90%    | ✅ 96%  |
| Interface | 60%     | 80%    | ✅ 92%  |

## 🔒 Error handling & exit codes

### Error taxonomy

| Category           | Exception           | CLI behavior                  |
| ------------------ | ------------------- | ----------------------------- |
| File not found     | `FileNotFoundError` | Print message, continue batch |
| Unsupported format | `ValueError`        | Print message, continue batch |
| Empty content      | `ValueError`        | Print message, continue batch |
| Model failure      | `RuntimeError`      | Print message, exit 1         |
| Synthesis failure  | `RuntimeError`      | Print message, exit 1         |

### Exit codes

| Code | Meaning                                   |
| ---- | ----------------------------------------- |
| `0`  | All operations succeeded                  |
| `1`  | One or more operations failed             |
| `2`  | CLI usage error (missing args, bad flags) |

Core modules never call `sys.exit()` — they raise typed exceptions. Only `cli/commands.py` converts exceptions to exit codes.

## ⚙️ Configuration

Configuration follows a strict priority order: **CLI flags → Environment variables → Dataclass defaults**.

| Variable              | Default                                | Description              |
| --------------------- | -------------------------------------- | ------------------------ |
| `QWEN_TTS_MODEL`      | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | HuggingFace model ID     |
| `QWEN_TTS_DEVICE`     | `cuda:0`                               | Inference device         |
| `QWEN_TTS_OUTPUT_DIR` | `~/qwen-reader-audio`                  | Default output directory |

Environment variables are read inside `default_factory` on config dataclasses — never scattered through application logic.

## 📋 Requirements

| Dependency                                       | Purpose                   |
| ------------------------------------------------ | ------------------------- |
| [qwen-tts](https://pypi.org/project/qwen-tts/)   | Qwen3-TTS model inference |
| [torch](https://pytorch.org/)                    | Deep learning runtime     |
| [soundfile](https://pypi.org/project/soundfile/) | WAV file I/O              |
| [numpy](https://numpy.org/)                      | Audio array operations    |
| [click](https://click.palletsprojects.com/)      | CLI framework             |
| [rich](https://rich.readthedocs.io/)             | Terminal formatting       |

**Dev dependencies** (optional):

| Dependency                                       | Purpose            |
| ------------------------------------------------ | ------------------ |
| [pytest](https://docs.pytest.org/)               | Test framework     |
| [pytest-cov](https://pytest-cov.readthedocs.io/) | Coverage reporting |

## ✅ Readiness checklist

Every item must pass before merge to `main`.

### Architecture (A1–A5)

- [x] Interface layer (`cli/`) imports no infrastructure/domain heavy deps
- [x] Domain layer (`core/text.py`, `core/storage.py`) has zero third-party imports
- [x] Core modules never call `print()`, `sys.exit()`, or import `click`/`rich`
- [x] All cross-layer data flows via `@dataclass` or callbacks
- [x] Heavy imports (torch, model libs) are deferred inside functions

### Packaging (P1–P4)

- [x] `pyproject.toml` has `[project.scripts]` entry
- [x] `__main__.py` exists and delegates to `cli:main`
- [x] `__init__.py` exports only `__version__`
- [x] `pip install -e .` + `qwen-reader --help` succeeds

### Developer experience (D1–D6)

- [x] `-h`/`--help` available on every group and command
- [x] `-v`/`--version` prints version and exits
- [x] All options have `show_default=True` where applicable
- [x] Success output is a structured Rich panel/table
- [x] Error output uses `[red]❌` prefix
- [x] Exit codes follow contract (0/1/2)

### Robustness (R1–R5)

- [x] Empty file / empty text raises `ValueError`, not crash
- [x] Unsupported extension raises `ValueError` with list of valid types
- [x] File encoding fallback (UTF-8 → Latin-1) is implemented
- [x] Windows UTF-8 stdout reconfiguration is present
- [x] Batch processing continues on per-file errors

### Code quality (Q1–Q5)

- [x] Every public function has a docstring with Args/Returns/Raises
- [x] Module-level docstring states purpose and dependency contract
- [x] Type annotations on all public function signatures
- [x] No `# type: ignore` without adjacent comment explaining why
- [x] Constants use `UPPER_SNAKE_CASE`, classes `PascalCase`

### Testing (T1–T3)

- [x] Domain layer has unit tests with no mocks (46 tests)
- [x] Use-Case layer has tests that mock infrastructure (17 tests)
- [x] CLI layer has click `CliRunner` tests (19 tests)

## 📄 License

This project is licensed under the [MIT License](LICENSE).
