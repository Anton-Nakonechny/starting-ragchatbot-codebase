"""Tests for code quality tooling setup.

Verifies:
- black is available as a dev dependency (importable)
- pyproject.toml carries a [tool.black] configuration section
- A dev format/lint script exists and is executable
"""

import stat
import importlib
from pathlib import Path

import tomllib
import pytest


# Resolve the project root (two levels up from backend/tests/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_SCRIPT = PROJECT_ROOT / "scripts" / "format.sh"


@pytest.fixture(scope="module")
def pyproject_config():
    """Parsed contents of pyproject.toml, loaded once per module."""
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as fh:
        return tomllib.load(fh)


@pytest.fixture(scope="module")
def format_script_content():
    """Text content of scripts/format.sh, read once per module."""
    return FORMAT_SCRIPT.read_text()


def test_black_is_importable():
    """black must be installed as a dev dependency."""
    black = importlib.import_module("black")
    assert hasattr(black, "format_str"), "black.format_str should exist"


def test_pyproject_has_black_config(pyproject_config):
    """pyproject.toml must have a [tool.black] section."""
    assert "tool" in pyproject_config, "pyproject.toml must have a [tool] table"
    assert "black" in pyproject_config["tool"], (
        "pyproject.toml must have a [tool.black] section"
    )


def test_black_config_has_line_length(pyproject_config):
    """[tool.black] must specify line-length."""
    black_cfg = pyproject_config["tool"]["black"]
    assert "line-length" in black_cfg, "[tool.black] must set line-length"
    assert isinstance(black_cfg["line-length"], int)


def test_format_script_exists():
    """A format/lint dev script must exist at scripts/format.sh."""
    assert FORMAT_SCRIPT.exists(), f"Expected format script at {FORMAT_SCRIPT}"


def test_format_script_is_executable():
    """The format script must be executable."""
    mode = FORMAT_SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, f"{FORMAT_SCRIPT} must have user-execute permission"


def test_format_script_invokes_black(format_script_content):
    """The format script must call black."""
    assert "black" in format_script_content, "format.sh must invoke black"


def test_format_script_invokes_ruff(format_script_content):
    """The format script must call ruff (already used in pre-commit)."""
    assert "ruff" in format_script_content, "format.sh must invoke ruff"
