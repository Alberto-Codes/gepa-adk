"""Acceptance tests for a silent ``import gepa_adk``.

Importing the package must write nothing to stdout. The component handler
registration messages stay available at DEBUG level through the standard
``logging`` module, and a structlog configuration the host program made
before the import is left alone.

Notes:
    Each case runs in a fresh interpreter so import-time behaviour is
    observed rather than a cached module.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit

REGISTRATION_EVENT = "component_handler.register.success"


def _run(code: str) -> subprocess.CompletedProcess[str]:
    """Run a Python snippet in a fresh interpreter and capture both streams.

    Args:
        code: Python source passed to the interpreter with ``-c``.

    Returns:
        The completed process, with ``stdout`` and ``stderr`` as text.
    """
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


class TestImportIsSilent:
    """Nothing reaches stdout on import."""

    def test_import_writes_nothing_to_stdout(self) -> None:
        """A bare import leaves stdout empty."""
        result = _run("import gepa_adk")
        assert result.returncode == 0, result.stderr
        assert result.stdout == ""

    def test_import_writes_nothing_to_stderr_by_default(self) -> None:
        """Without a logging configuration, DEBUG registration lines are dropped."""
        result = _run("import gepa_adk")
        assert result.returncode == 0, result.stderr
        assert REGISTRATION_EVENT not in result.stderr


class TestRegistrationStaysAvailableThroughLogging:
    """The registration events flow through ``logging`` at DEBUG."""

    def test_debug_logging_config_receives_registration_events(self) -> None:
        """A DEBUG basicConfig on stderr shows the three registration lines."""
        result = _run(
            "import logging, sys\n"
            "logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)\n"
            "import gepa_adk\n"
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == ""
        assert result.stderr.count(REGISTRATION_EVENT) == 3

    def test_host_structlog_configuration_is_respected(self) -> None:
        """A structlog configuration made before the import is not replaced."""
        result = _run(
            "import sys, structlog\n"
            "structlog.configure(\n"
            "    processors=[structlog.processors.KeyValueRenderer()],\n"
            "    logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),\n"
            ")\n"
            "import gepa_adk\n"
            "print('configured', structlog.get_config()['logger_factory'].__class__.__name__)\n"
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.count(REGISTRATION_EVENT) == 3
        assert "configured PrintLoggerFactory" in result.stdout
