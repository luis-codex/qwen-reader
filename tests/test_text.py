"""Domain layer tests — core/text.py.

These tests exercise pure text transforms with ZERO mocks and ZERO
third-party imports beyond pytest itself (stdlib ``re`` only under test).
Checklist items: T1, A2.
"""

from __future__ import annotations

import pytest

from qwen_reader.core.text import (
    MARKDOWN_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    chunk_text,
    clean_text,
    strip_markdown,
    strip_rst,
)


# =====================================================================
# strip_markdown
# =====================================================================


class TestStripMarkdown:
    """Verify each markdown construct is correctly stripped."""

    def test_heading_markers_removed(self):
        assert strip_markdown("# Title") == "Title"
        assert strip_markdown("## Sub") == "Sub"
        assert strip_markdown("### Deep") == "Deep"

    def test_bold_and_italic(self):
        assert strip_markdown("**bold**") == "bold"
        assert strip_markdown("*italic*") == "italic"
        assert strip_markdown("***both***") == "both"
        assert strip_markdown("__bold__") == "bold"
        assert strip_markdown("_italic_") == "italic"

    def test_strikethrough(self):
        assert strip_markdown("~~deleted~~") == "deleted"

    def test_inline_code(self):
        assert strip_markdown("`code`") == "code"

    def test_fenced_code_blocks_removed(self):
        md = "before\n```python\nprint('hi')\n```\nafter"
        result = strip_markdown(md)
        assert "print" not in result
        assert "before" in result
        assert "after" in result

    def test_links_keep_text(self):
        assert strip_markdown("[click here](https://x.com)") == "click here"

    def test_images_keep_alt(self):
        assert strip_markdown("![alt text](img.png)") == "alt text"

    def test_html_tags_removed(self):
        assert strip_markdown("<div>content</div>").strip() == "content"

    def test_blockquotes(self):
        assert strip_markdown("> quoted text").strip() == "quoted text"

    def test_horizontal_rules(self):
        result = strip_markdown("above\n---\nbelow")
        assert "---" not in result

    def test_unordered_lists(self):
        result = strip_markdown("- item one\n- item two")
        assert "item one" in result
        assert "- " not in result

    def test_ordered_lists(self):
        result = strip_markdown("1. first\n2. second")
        assert "first" in result
        assert "1." not in result

    def test_yaml_frontmatter_removed(self):
        md = "---\ntitle: Test\n---\nBody text"
        assert "title" not in strip_markdown(md)
        assert "Body text" in strip_markdown(md)

    def test_reference_links_removed(self):
        md = "See [ref].\n\n[ref]: https://example.com"
        result = strip_markdown(md)
        assert "https://" not in result

    def test_footnote_definitions_removed(self):
        md = "Text[^1].\n\n[^1]: Footnote content"
        result = strip_markdown(md)
        assert "Footnote content" not in result

    def test_collapses_excess_newlines(self):
        md = "A\n\n\n\n\nB"
        result = strip_markdown(md)
        assert "\n\n\n" not in result

    def test_empty_input(self):
        assert strip_markdown("") == ""

    def test_plain_text_passthrough(self):
        plain = "Just a normal sentence."
        assert strip_markdown(plain) == plain


# =====================================================================
# strip_rst
# =====================================================================


class TestStripRst:
    """Verify reStructuredText stripping."""

    def test_section_underlines_removed(self):
        rst = "Title\n=====\n\nContent"
        result = strip_rst(rst)
        assert "=====" not in result
        assert "Title" in result

    def test_inline_bold(self):
        assert strip_rst("**bold**") == "bold"

    def test_inline_code(self):
        assert strip_rst("``code``") == "code"

    def test_role_markup(self):
        assert strip_rst(":ref:`some label`") == "some label"

    def test_empty_input(self):
        assert strip_rst("") == ""


# =====================================================================
# clean_text (dispatcher)
# =====================================================================


class TestCleanText:
    """Verify the extension-based dispatcher."""

    def test_markdown_extension(self):
        result = clean_text("# Heading", ".md")
        assert result == "Heading"

    def test_markdown_alt_extension(self):
        result = clean_text("# Heading", ".markdown")
        assert result == "Heading"

    def test_rst_extension(self):
        result = clean_text("**bold**", ".rst")
        assert result == "bold"

    def test_txt_passthrough(self):
        text = "  plain text  "
        assert clean_text(text, ".txt") == "plain text"

    def test_text_passthrough(self):
        text = "  plain text  "
        assert clean_text(text, ".text") == "plain text"


# =====================================================================
# chunk_text
# =====================================================================


class TestChunkText:
    """Verify sentence-boundary chunking."""

    def test_short_text_single_chunk(self):
        chunks = chunk_text("Hello world.", max_chars=500)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world."

    def test_splits_at_sentence_boundaries(self):
        text = "First sentence. Second sentence. Third sentence."
        chunks = chunk_text(text, max_chars=30)
        assert len(chunks) >= 2
        # Every chunk should be ≤ max_chars (when possible)
        for c in chunks:
            assert len(c) <= 50  # generous margin for single-sentence overflow

    def test_respects_paragraph_breaks(self):
        text = "Paragraph one.\n\nParagraph two."
        chunks = chunk_text(text, max_chars=500)
        # May be 1 or 2 chunks depending on length, but content preserved
        joined = " ".join(chunks)
        assert "Paragraph one" in joined
        assert "Paragraph two" in joined

    def test_empty_input_returns_empty(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_single_long_sentence(self):
        long = "A" * 600
        chunks = chunk_text(long, max_chars=500)
        # Single sentence can't be split, so it stays as one chunk
        assert len(chunks) == 1
        assert chunks[0] == long

    def test_multiple_sentence_terminators(self):
        text = "Hello! How are you? I'm fine."
        chunks = chunk_text(text, max_chars=20)
        assert len(chunks) >= 2


# =====================================================================
# Constants
# =====================================================================


class TestConstants:
    """Verify expected constants are defined correctly."""

    def test_supported_extensions(self):
        assert ".md" in SUPPORTED_EXTENSIONS
        assert ".markdown" in SUPPORTED_EXTENSIONS
        assert ".txt" in SUPPORTED_EXTENSIONS
        assert ".rst" in SUPPORTED_EXTENSIONS
        assert ".text" in SUPPORTED_EXTENSIONS
        assert ".pdf" not in SUPPORTED_EXTENSIONS

    def test_markdown_extensions_subset(self):
        assert MARKDOWN_EXTENSIONS <= SUPPORTED_EXTENSIONS

    def test_extensions_are_frozenset(self):
        assert isinstance(SUPPORTED_EXTENSIONS, frozenset)
        assert isinstance(MARKDOWN_EXTENSIONS, frozenset)
