"""Text processing: markdown/RST stripping, cleaning, and chunking.

This module has zero external dependencies — only ``re`` from stdlib.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Supported file types
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".md", ".markdown", ".txt", ".rst", ".text"}
)

MARKDOWN_EXTENSIONS: frozenset[str] = frozenset({".md", ".markdown"})


# ---------------------------------------------------------------------------
# Markdown → plain text
# ---------------------------------------------------------------------------

def strip_markdown(text: str) -> str:
    """Convert markdown to clean, readable plain text for TTS."""
    # YAML front-matter
    text = re.sub(r"^---\s*\n[\s\S]*?\n---\s*\n", "", text)
    # Fenced code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Images (keep alt text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # Links (keep link text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Heading markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Bold / italic
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    # Strikethrough
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    # Blockquotes
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    # Horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Unordered list markers
    text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
    # Ordered list markers
    text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Reference-style links
    text = re.sub(r"^\[[^\]]+\]:\s+.*$", "", text, flags=re.MULTILINE)
    # Footnote definitions
    text = re.sub(r"^\[\^[^\]]+\]:.*$", "", text, flags=re.MULTILINE)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# reStructuredText → plain text
# ---------------------------------------------------------------------------

def strip_rst(text: str) -> str:
    """Convert reStructuredText to plain text for TTS."""
    # Directive blocks
    text = re.sub(r"\.\.\s+\w+::.*?(?=\n\S|\Z)", "", text, flags=re.DOTALL)
    # Section underlines
    text = re.sub(r"^[=\-~^\"'`]+$", "", text, flags=re.MULTILINE)
    # Inline markup
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"``([^`]+)``", r"\1", text)
    text = re.sub(r":[\w]+:`([^`]+)`", r"\1", text)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def clean_text(text: str, extension: str) -> str:
    """Dispatch to the appropriate cleaner based on file extension.

    Args:
        text: Raw file content.
        extension: Lowercase file extension including dot (e.g. ``".md"``).

    Returns:
        Cleaned plain text suitable for TTS.
    """
    if extension in MARKDOWN_EXTENSIONS:
        return strip_markdown(text)
    if extension == ".rst":
        return strip_rst(text)
    return text.strip()


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    """Split *text* into chunks at sentence boundaries.

    Each chunk is ≤ *max_chars* characters when possible.
    """
    sentences = re.split(r"(?<=[.!?。！？])\s+|\n\n+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if not current:
            current = sentence
        elif len(current) + len(sentence) + 1 <= max_chars:
            current += " " + sentence
        else:
            chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks
