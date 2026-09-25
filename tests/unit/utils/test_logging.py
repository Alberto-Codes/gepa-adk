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
from collections.abc import Iterator

import pytest
import structlog

from gepa_adk.utils.logging import configure_default_logging

pytestmark = pytest.mark.unit


@pytest.fixture
def unconfigured_structlog() -> Iterator[None]:
    """Run a test against an unconfigured structlog, then restore the prior state.

    Yields:
        None, with structlog at its defaults for the duration of the test.
        Afterwards the previous configuration and its configured flag are
        restored, so the test neither inherits nor leaks a configuration.
    """
    saved = structlog.get_config()
    was_configured = structlog.is_configured()
    structlog.reset_defaults()
    try:
        yield
    finally:
        structlog.reset_defaults()
        if was_configured:
            structlog.configure(**saved)


class TestConfigureDefaultLogging:
    """Configure structlog only when the host has not.

    Examples:
        ```python
        TestConfigureDefaultLogging().test_configures_once_then_defers()
        ```
    """

    def test_configures_once_then_defers(self, unconfigured_structlog: None) -> None:
        """First call configures stdlib routing; a second call changes nothing.

        Args:
            unconfigured_structlog: Fixture that resets structlog for the test.
        """
        assert configure_default_logging() is True
        config = structlog.get_config()
        assert isinstance(config["logger_factory"], structlog.stdlib.LoggerFactory)
        assert config["wrapper_class"] is structlog.stdlib.BoundLogger
        assert config["processors"][0] is structlog.stdlib.filter_by_level
        assert configure_default_logging() is False
        assert structlog.get_config()["logger_factory"] is config["logger_factory"]

    def test_leaves_host_configuration_alone(
        self, unconfigured_structlog: None
    ) -> None:
        """A host configuration made first stays in force.

        Args:
            unconfigured_structlog: Fixture that resets structlog for the test.
        """
        host_factory = structlog.PrintLoggerFactory(file=sys.stdout)
        structlog.configure(logger_factory=host_factory)
        assert configure_default_logging() is False
        assert structlog.get_config()["logger_factory"] is host_factory
