"""Interface layer tests — cli.py.

Uses click's ``CliRunner`` to invoke commands without spawning a subprocess.
The model is always mocked via ``patch_model`` so these tests never need
a GPU or network access.
Checklist items: T3, D1, D2, D6.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from qwen_reader.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    """Provide a CliRunner with UTF-8 charset."""
    return CliRunner(charset="utf-8")


# =====================================================================
# Group-level behaviour
# =====================================================================


class TestCLIGroup:
    """Test the top-level ``qwen-reader`` command."""

    def test_help_flag(self, runner: CliRunner):
        result = runner.invoke(cli, ["-h"])
        assert result.exit_code == 0
        assert "Convert articles to audio" in result.output

    def test_help_long_flag(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_version_flag(self, runner: CliRunner):
        result = runner.invoke(cli, ["-v"])
        assert result.exit_code == 0
        # Should contain a version string like "0.1.0"
        assert "." in result.output

    def test_no_command_shows_help(self, runner: CliRunner):
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "qwen-reader" in result.output


# =====================================================================
# read command
# =====================================================================


class TestReadCommand:
    """Test the ``read`` subcommand."""

    def test_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["read", "-h"])
        assert result.exit_code == 0
        assert "Convert one or more files" in result.output

    def test_single_file(self, runner: CliRunner, patch_model, tmp_md: Path, tmp_path: Path):
        result = runner.invoke(cli, [
            "read", str(tmp_md),
            "--output-dir", str(tmp_path),
            "--device", "cpu",
        ])
        assert result.exit_code == 0
        assert "Audio generated" in result.output

    def test_multiple_files(self, runner: CliRunner, patch_model, tmp_md: Path, tmp_txt: Path, tmp_path: Path):
        result = runner.invoke(cli, [
            "read", str(tmp_md), str(tmp_txt),
            "--output-dir", str(tmp_path),
            "--device", "cpu",
        ])
        assert result.exit_code == 0
        assert "Done!" in result.output

    def test_nonexistent_file(self, runner: CliRunner, patch_model):
        result = runner.invoke(cli, ["read", "/nonexistent/file.md"])
        # click validates exists=True before the command runs
        assert result.exit_code != 0

    def test_custom_name(self, runner: CliRunner, patch_model, tmp_md: Path, tmp_path: Path):
        result = runner.invoke(cli, [
            "read", str(tmp_md),
            "--output-dir", str(tmp_path),
            "--name", "my-podcast",
            "--device", "cpu",
        ])
        assert result.exit_code == 0
        assert (tmp_path / "my-podcast.wav").exists()


# =====================================================================
# speak command
# =====================================================================


class TestSpeakCommand:
    """Test the ``speak`` subcommand."""

    def test_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "-h"])
        assert result.exit_code == 0
        assert "inline text" in result.output.lower()

    def test_basic_speak(self, runner: CliRunner, patch_model, tmp_path: Path):
        result = runner.invoke(cli, [
            "speak", "Hello world, testing.",
            "--output-dir", str(tmp_path),
            "--device", "cpu",
        ])
        assert result.exit_code == 0
        assert "Audio generated" in result.output

    def test_custom_name(self, runner: CliRunner, patch_model, tmp_path: Path):
        result = runner.invoke(cli, [
            "speak", "Test.",
            "--output-dir", str(tmp_path),
            "--name", "greeting",
            "--device", "cpu",
        ])
        assert result.exit_code == 0
        assert (tmp_path / "greeting.wav").exists()


# =====================================================================
# speakers command
# =====================================================================


class TestSpeakersCommand:
    """Test the ``speakers`` subcommand."""

    def test_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["speakers", "-h"])
        assert result.exit_code == 0

    def test_lists_speakers(self, runner: CliRunner, patch_model):
        result = runner.invoke(cli, ["speakers", "--device", "cpu"])
        assert result.exit_code == 0
        assert "Aiden" in result.output
        assert "Vivian" in result.output


# =====================================================================
# list command
# =====================================================================


class TestListCommand:
    """Test the ``list`` subcommand."""

    def test_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["list", "-h"])
        assert result.exit_code == 0

    def test_empty_directory(self, runner: CliRunner, tmp_path: Path):
        result = runner.invoke(cli, ["list", "--output-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "No audio files" in result.output

    def test_with_wav_files(self, runner: CliRunner, tmp_path: Path):
        # Create a dummy WAV file
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"\x00" * 1024)

        result = runner.invoke(cli, ["list", "--output-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "test.wav" in result.output


# =====================================================================
# Exit code contract (§5.2)
# =====================================================================


class TestExitCodes:
    """Verify exit-code contract across scenarios."""

    def test_success_returns_0(self, runner: CliRunner, patch_model, tmp_md: Path, tmp_path: Path):
        result = runner.invoke(cli, [
            "read", str(tmp_md),
            "--output-dir", str(tmp_path),
            "--device", "cpu",
        ])
        assert result.exit_code == 0

    def test_usage_error_returns_2(self, runner: CliRunner):
        # Missing required argument
        result = runner.invoke(cli, ["read"])
        assert result.exit_code == 2
