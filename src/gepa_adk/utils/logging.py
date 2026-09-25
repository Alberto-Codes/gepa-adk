"""Default structlog configuration that defers to the host's ``logging`` setup.

gepa-adk logs through structlog and never prints. When a host program has not
configured structlog, structlog's built-in default writes every event, DEBUG
included, to stdout. This module replaces that default with a configuration
that routes events through the standard library ``logging`` module, so the
host's ``logging`` configuration decides what is emitted and where.

Attributes:
    configure_default_logging (function): Route structlog through the standard
        library when the host has not configured structlog.

Examples:
    The package calls this at import time. A host that wants the DEBUG events
    configures ``logging`` before importing gepa-adk:

    ```python
    import logging

    logging.basicConfig(level=logging.DEBUG)

    import gepa_adk  # registration events now appear at DEBUG
    ```

See Also:
    - [structlog configuration](https://www.structlog.org/en/stable/configuration.html):
      ``structlog.is_configured()`` and ``structlog.stdlib.LoggerFactory``.
    - [`EncodingSafeProcessor`][gepa_adk.utils.encoding.EncodingSafeProcessor]:
      Processor placed before the renderer in the default chain.

Notes:
    A structlog configuration made before gepa-adk is imported is left
    untouched. The package never calls ``logging.basicConfig`` and adds no
    handlers, so with no host configuration Python's last-resort handler emits
    WARNING and above to stderr and drops DEBUG and INFO.
"""

from __future__ import annotations

import structlog

from gepa_adk.utils.encoding import EncodingSafeProcessor


def configure_default_logging() -> bool:
    """Route structlog through ``logging`` unless the host configured structlog.

    Returns:
        True if this call configured structlog, False if structlog was already
        configured and was left unchanged.

    Examples:
        ```python
        from gepa_adk.utils.logging import configure_default_logging

        configure_default_logging()  # False after gepa_adk has been imported
        ```
    """
    if structlog.is_configured():
        return False
    structlog.configure(
        processors=[
            # First, so an event below the stdlib logger's level is dropped
            # before any rendering work.
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            EncodingSafeProcessor(),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    return True
