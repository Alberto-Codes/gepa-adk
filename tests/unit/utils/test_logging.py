"""Unit tests for the default structlog configuration guard.

Examples:
    Run this module alone:

    ```bash
    uv run pytest tests/unit/utils/test_logging.py -q
    ```

See Also:
    - [`configure_default_logging`][gepa_adk.utils.logging.configure_default_logging]:
      The function under test.
"""

from __future__ import annotations

import sys

import pytest
import structlog

from gepa_adk.utils.logging import configure_default_logging

pytestmark = pytest.mark.unit


class TestConfigureDefaultLogging:
    """Configure structlog only when the host has not.

    Examples:
        ```python
        TestConfigureDefaultLogging().test_configures_once_then_defers()
        ```
    """

    def test_configures_once_then_defers(self) -> None:
        """First call configures stdlib routing; a second call changes nothing."""
        saved = structlog.get_config()
        structlog.reset_defaults()
        try:
            assert configure_default_logging() is True
            config = structlog.get_config()
            assert isinstance(config["logger_factory"], structlog.stdlib.LoggerFactory)
            assert config["wrapper_class"] is structlog.stdlib.BoundLogger
            assert config["processors"][0] is structlog.stdlib.filter_by_level
            assert configure_default_logging() is False
            assert structlog.get_config()["logger_factory"] is config["logger_factory"]
        finally:
            structlog.reset_defaults()
            structlog.configure(**saved)

    def test_leaves_host_configuration_alone(self) -> None:
        """A host configuration made first stays in force."""
        saved = structlog.get_config()
        structlog.reset_defaults()
        host_factory = structlog.PrintLoggerFactory(file=sys.stdout)
        try:
            structlog.configure(logger_factory=host_factory)
            assert configure_default_logging() is False
            assert structlog.get_config()["logger_factory"] is host_factory
        finally:
            structlog.reset_defaults()
            structlog.configure(**saved)
