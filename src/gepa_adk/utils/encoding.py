"""Cross-platform encoding support for structured logging.

This module provides the EncodingSafeProcessor, a structlog processor that
sanitizes string values in event dictionaries to prevent UnicodeEncodeError
exceptions on consoles with limited encoding support (e.g., Windows cp1252).

The processor uses a two-phase sanitization strategy:
1. Smart character replacements that preserve semantic meaning (e.g., smart
   quotes → regular quotes, em dash → double hyphen)
2. Fallback encode/decode with 'replace' error handler for any remaining
   unencodable characters

This approach ensures log output is always writable to the console without
raising exceptions, while preserving as much of the original meaning as
possible.

Examples:
    Add to structlog processor chain before the renderer:

    ```python
    import structlog
    from gepa_adk.utils.encoding import EncodingSafeProcessor

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            EncodingSafeProcessor(),  # Before renderer
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    ```

See Also:
    - [`EncodingSafeProcessor`][gepa_adk.utils.encoding.EncodingSafeProcessor]: The
      processor class provided by this module.
    - [`structlog.dev.ConsoleRenderer`][structlog.dev.ConsoleRenderer]: Renderer
      that this processor should precede in the chain.

Note:
    This processor is designed to be transparent on UTF-8 consoles (macOS,
    Linux) while preventing crashes on cp1252 consoles (Windows).
"""

from __future__ import annotations

import sys
from collections.abc import MutableMapping
from typing import Any


class EncodingSafeProcessor:
    r"""Sanitize strings for console encoding compatibility.

    A structlog processor that ensures all string values in the event dict
    can be safely written to the console regardless of its encoding (cp1252
    on Windows, UTF-8 on macOS/Linux).

    The sanitization strategy:
    1. Apply smart character replacements (preserve meaning)
    2. Encode to console encoding with 'replace' error handler
    3. Decode back to string

    This produces strings that are guaranteed to be writable to the console
    without raising UnicodeEncodeError.

    Attributes:
        REPLACEMENTS (dict[str, str]): Class constant mapping Unicode characters
            to ASCII equivalents that preserve semantic meaning.
        encoding (str): The target console encoding detected at initialization.
        sanitize_string (method): Sanitize a single string for console encoding.

    Examples:
        Use as a structlog processor:

        ```python
        processor = EncodingSafeProcessor()
        event = {"event": "User said \u2018hello\u2019"}
        result = processor(None, "info", event)
        # result["event"] == "User said 'hello'"
        ```

    Note:
        All sanitization is idempotent - processing already-sanitized strings
        produces identical output.
    """

    # Smart character replacements (preserve meaning)
    # These map common Unicode characters that cause issues on cp1252
    # to their closest ASCII equivalents
    REPLACEMENTS: dict[str, str] = {
        "\u2018": "'",  # Left single quote → apostrophe
        "\u2019": "'",  # Right single quote → apostrophe
        "\u201c": '"',  # Left double quote → quotation mark
        "\u201d": '"',  # Right double quote → quotation mark
        "\u2011": "-",  # Non-breaking hyphen → hyphen-minus
        "\u2013": "-",  # En dash → hyphen-minus
        "\u2014": "--",  # Em dash → double hyphen
        "\u2026": "...",  # Horizontal ellipsis → three periods
        "\u00a0": " ",  # Non-breaking space → regular space
    }

    def __init__(self) -> None:
        """Initialize the processor with console encoding detection.

        Detects the console encoding from sys.stdout.encoding, falling back
        to UTF-8 if detection fails (e.g., when stdout is redirected or
        unavailable).

        Note:
            Console encoding is cached at initialization time to avoid
            repeated attribute lookups during log processing.
        """
        self.encoding: str = getattr(sys.stdout, "encoding", None) or "utf-8"

    def __call__(
        self,
        logger: Any,
        method_name: str,
        event_dict: MutableMapping[str, Any],
    ) -> MutableMapping[str, Any]:
        """Process event dictionary, sanitizing all string values.

        Implements the structlog processor protocol. Recursively sanitizes
        all string values in the event dictionary, including nested dicts
        and lists.

        Args:
            logger: The wrapped logger instance (unused but required by
                protocol).
            method_name: Name of the log method called (e.g., "info", "debug").
                Unused but required by protocol.
            event_dict: Mutable mapping of log event data to sanitize.

        Returns:
            The event_dict with all string values sanitized for console
            encoding compatibility.

        Note:
            Original event_dict is not modified; a new dict is returned
            with sanitized values.
        """
        return self._sanitize_dict(event_dict)

    def sanitize_string(self, s: str) -> str:
        """Sanitize a single string for console encoding.

        Applies smart character replacements first to preserve meaning,
        then uses encode/decode with 'replace' error handler for any
        remaining unencodable characters.

        Args:
            s (str): The string to sanitize.

        Returns:
            A string that is guaranteed to be encodable to the console
            encoding without raising UnicodeEncodeError.

        Examples:
            Sanitize a string with smart quotes:

            ```python
            processor = EncodingSafeProcessor()
            result = processor.sanitize_string("User said \u2018hello\u2019")
            assert result == "User said 'hello'"
            ```

        Note:
            Order of operations: smart replacements run first to preserve
            semantic meaning, then encode/decode handles remaining characters.
        """
        # Apply smart replacements first (preserve meaning)
        for char, replacement in self.REPLACEMENTS.items():
            s = s.replace(char, replacement)

        # Encode/decode with replace for any remaining unencodable chars
        # This handles any Unicode characters not in our explicit mapping
        return s.encode(self.encoding, errors="replace").decode(self.encoding)

    def _sanitize_value(self, value: Any) -> Any:
        """Recursively sanitize any value.

        Handles strings, dicts, lists, and tuples. Other types pass through
        unchanged.

        Args:
            value: The value to sanitize.

        Returns:
            The sanitized value, with the same type as the input (except
            strings may have different content).
        """
        if isinstance(value, str):
            return self.sanitize_string(value)
        elif isinstance(value, MutableMapping):
            return self._sanitize_dict(value)
        elif isinstance(value, (list, tuple)):
            # Preserve the original type (list or tuple)
            return type(value)(self._sanitize_value(v) for v in value)
        # Non-string, non-collection types pass through unchanged
        return value

    def _sanitize_dict(self, d: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        """Sanitize all values in a dictionary.

        Args:
            d: The dictionary or mutable mapping to sanitize.

        Returns:
            A new dictionary with all string values sanitized.
        """
        return {k: self._sanitize_value(v) for k, v in d.items()}
