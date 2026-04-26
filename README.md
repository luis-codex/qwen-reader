<div align="center">

# 🎧 qwen-reader

**Convert articles and documents to high-quality audio using Qwen3-TTS.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
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
git clone https://github.com/your-username/qwen-reader.git
cd qwen-reader

# Create virtual environment and install
uv venv
uv pip install -e .

# Install PyTorch with CUDA support (adjust cu128 to your CUDA version)
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
```

> [!NOTE]
> The first run downloads the model (~3.5 GB) from HuggingFace. Subsequent runs load it from cache in ~30s.

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

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--speaker` | `-s` | `Aiden` | TTS voice to use |
| `--lang` | `-l` | `Auto` | Language (Auto, English, Chinese, Spanish, etc.) |
| `--instruct` | `-i` | *conversational* | Style instruction for the TTS engine |
| `--output-dir` | `-o` | `~/qwen-reader-audio` | Output directory |
| `--name` | `-n` | *filename stem* | Custom output filename (without extension) |
| `--device` | `-d` | `cuda:0` | Compute device (`cuda:0`, `cpu`) |
| `--version` | `-v` | — | Show version |
| `--help` | `-h` | — | Show help |

## 🗂️ Supported file types

| Extension | Processing |
|-----------|------------|
| `.md`, `.markdown` | Strips YAML front-matter, code blocks, links, images, emphasis, headers |
| `.rst` | Strips directives, section underlines, inline markup |
| `.txt`, `.text` | Passed through as-is |

## 🏗️ Project structure

```
qwen_reader/
├── __init__.py              # Package version
├── __main__.py              # python -m qwen_reader entry
├── cli.py                   # CLI layer (click + rich)
└── core/
    ├── text.py              # Text cleaning & chunking (stdlib only)
    ├── model.py             # Lazy model singleton + config
    └── synthesis.py         # Audio generation orchestration
```

| Layer | Responsibility | Dependencies |
|-------|---------------|--------------|
| `cli.py` | User interaction, formatting, exit codes | click, rich |
| `core/text.py` | Markdown/RST stripping, sentence chunking | stdlib `re` only |
| `core/model.py` | Model lifecycle, lazy loading, caching | torch, qwen_tts |
| `core/synthesis.py` | Orchestrates text → chunks → TTS → WAV | core/text, core/model, numpy, soundfile |

## ⚙️ Configuration

Environment variables override defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `QWEN_TTS_MODEL` | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | HuggingFace model ID |
| `QWEN_TTS_DEVICE` | `cuda:0` | Inference device |
| `QWEN_TTS_OUTPUT_DIR` | `~/qwen-reader-audio` | Default output directory |

## 📋 Requirements

| Dependency | Purpose |
|------------|---------|
| [qwen-tts](https://pypi.org/project/qwen-tts/) | Qwen3-TTS model inference |
| [torch](https://pytorch.org/) | Deep learning runtime |
| [soundfile](https://pypi.org/project/soundfile/) | WAV file I/O |
| [numpy](https://numpy.org/) | Audio array operations |
| [click](https://click.palletsprojects.com/) | CLI framework |
| [rich](https://rich.readthedocs.io/) | Terminal formatting |

## 📄 License

This project is licensed under the [MIT License](LICENSE).
