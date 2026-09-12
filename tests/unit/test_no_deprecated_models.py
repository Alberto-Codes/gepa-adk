"""Repo hygiene guard: no deprecated Gemini identifier anywhere in the tree.

The selection-path guards in ``test_resolve_model_for_agent.py`` protect the
strings the library resolves at runtime. This module protects the rest: the
docstrings, docs pages, examples, and mocked test fixtures that a reader copies.
Adding a newly retired identifier to
[`DEPRECATED_GEMINI_MODELS`][tests.fixtures.models.DEPRECATED_GEMINI_MODELS]
makes this test name every file still pointing at it, so a deprecation sweep
cannot half-finish.

Note:
    Two files are exempt because naming retired models is their job: the
    deprecation data itself, and the parametrized cases proving the native-model
    pattern in ``_resolve_model_for_agent`` is version-agnostic.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.fixtures.models import DEPRECATED_GEMINI_PREFIXES

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: Trees whose model identifiers a user reads, copies, or executes.
_SCANNED_DIRS = ("src", "tests", "docs", "examples")

#: Files that must keep naming retired models. See the module note.
_EXEMPT = frozenset(
    {
        Path("tests/fixtures/models.py"),
        Path("tests/unit/test_resolve_model_for_agent.py"),
    }
)

_SKIPPED_DIR_NAMES = frozenset({"__pycache__", ".ruff_cache", "site"})

_DEPRECATED_RE = re.compile(
    "|".join(re.escape(prefix) for prefix in DEPRECATED_GEMINI_PREFIXES)
)


def _scanned_files() -> list[Path]:
    """Collect every text file under the scanned trees, minus exemptions.

    Returns:
        Repo-relative paths, sorted for a stable failure message.
    """
    found: list[Path] = []
    for directory in _SCANNED_DIRS:
        for path in (_REPO_ROOT / directory).rglob("*"):
            if not path.is_file():
                continue
            if _SKIPPED_DIR_NAMES & set(path.parts):
                continue
            relative = path.relative_to(_REPO_ROOT)
            if relative in _EXEMPT:
                continue
            found.append(relative)
    return sorted(found)


class TestNoDeprecatedGeminiReferences:
    """Guards that no copyable model reference names a retired generation."""

    def test_scan_covers_the_repo(self) -> None:
        """The scan must actually find files, or it guards nothing."""
        files = _scanned_files()
        assert len(files) > 100, f"expected a populated tree, found {len(files)}"

    def test_no_deprecated_gemini_identifiers(self) -> None:
        """No scanned file may reference a retired Gemini generation."""
        offenders: list[str] = []
        for relative in _scanned_files():
            try:
                text = (_REPO_ROOT / relative).read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # Binary or unreadable files carry no model strings.
            for lineno, line in enumerate(text.splitlines(), start=1):
                for match in _DEPRECATED_RE.finditer(line):
                    offenders.append(f"{relative}:{lineno}: {match.group(0)}...")

        assert not offenders, (
            "Retired Gemini identifiers found. Replace each with a current "
            "model, or with a local open model where the surface supports one "
            "(see docs/reference/model-selection.md):\n  " + "\n  ".join(offenders)
        )
