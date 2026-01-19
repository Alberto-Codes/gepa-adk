"""Integration tests for EncodingSafeProcessor with real structlog pipeline.

Tests verify that EncodingSafeProcessor correctly integrates with structlog's
processor chain and produces console-safe output when logging LLM-generated
content with problematic Unicode characters.

Note:
    These tests use structlog's testing utilities to capture log output
    and verify the processor works in a real pipeline context.
"""

from __future__ import annotations

from io import StringIO
from typing import Any
from unittest.mock import patch

import pytest
import structlog

from gepa_adk.utils.encoding import EncodingSafeProcessor

pytestmark = pytest.mark.integration


class TestRealStructlogIntegration:
    """Integration tests for T027a: real structlog console output."""

    def test_processor_in_real_structlog_pipeline(self) -> None:
        """Verify processor works in actual structlog.configure() pipeline."""
        # Test the processor directly in a pipeline-like flow
        # capture_logs captures events BEFORE processors run, so we test differently
        processor = EncodingSafeProcessor()

        # Simulate what structlog does: pass through processor chain
        event_dict: dict[str, Any] = {
            "event": "LLM said",
            "response": "User said \u2018hello\u2019 with \u2014 emphasis",
        }

        result = processor(None, "info", event_dict)

        assert result["event"] == "LLM said"
        assert result["response"] == "User said 'hello' with -- emphasis"

    def test_processor_with_nested_log_data(self) -> None:
        """Verify processor handles nested data in structlog pipeline."""
        processor = EncodingSafeProcessor()

        event_dict: dict[str, Any] = {
            "event": "agent.response",
            "context": {
                "user_input": "Tell me about \u201cquotes\u201d",
                "model_output": "Here\u2019s what I found\u2026",
            },
        }

        result = processor(None, "info", event_dict)

        assert result["context"]["user_input"] == 'Tell me about "quotes"'
        assert result["context"]["model_output"] == "Here's what I found..."

    def test_processor_preserves_log_level(self) -> None:
        """Verify processor doesn't interfere with log level processing."""
        processor = EncodingSafeProcessor()

        # Test with different log levels
        log_levels = ["debug", "info", "warning", "error"]

        for level in log_levels:
            event_dict: dict[str, Any] = {
                "event": f"{level.title()} \u2018message\u2019",
                "log_level": level,
            }

            result = processor(None, level, event_dict)

            assert result["log_level"] == level
            assert "'message'" in result["event"]
            assert "\u2018" not in result["event"]

    def test_processor_with_bound_logger_context(self) -> None:
        """Verify processor works with structlog's bound logger context."""
        processor = EncodingSafeProcessor()

        # Simulate bound logger context (already merged into event_dict)
        event_dict: dict[str, Any] = {
            "event": "Processing \u2018request\u2019",
            "session_id": "abc123",
            "user_query": "What\u2019s the weather?",
        }

        result = processor(None, "info", event_dict)

        assert result["session_id"] == "abc123"
        assert result["user_query"] == "What's the weather?"
        assert result["event"] == "Processing 'request'"

    def test_console_output_no_unicode_error(self) -> None:
        """Verify logging to simulated cp1252 console doesn't raise."""

        # Create a StringIO that simulates cp1252 encoding limitations
        class Cp1252StringIO(StringIO):
            """StringIO that raises on non-cp1252 characters like real console."""

            def write(self, s: str, /) -> int:  # type: ignore[override]
                # Verify string can be encoded to cp1252
                s.encode("cp1252")  # Will raise if invalid
                return super().write(s)

        # Configure structlog with EncodingSafeProcessor
        output = Cp1252StringIO()

        # Create a processor with cp1252 encoding
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "cp1252"
            processor = EncodingSafeProcessor()

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                processor,
                structlog.dev.ConsoleRenderer(colors=False),
            ],
            wrapper_class=structlog.BoundLogger,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(output),
            cache_logger_on_first_use=False,
        )

        try:
            logger = structlog.get_logger()

            # This would raise UnicodeEncodeError without the processor
            # U+2011 (non-breaking hyphen) is particularly problematic
            logger.info(
                "LLM output",
                message="self\u2011aware AI said \u201cHello\u201d with\u2014style\u2026",
            )

            # If we get here without exception, the test passes
            logged_output = output.getvalue()
            assert "LLM output" in logged_output
            # Verify the sanitized characters appear
            assert "self-aware" in logged_output  # U+2011 -> -
            assert '"Hello"' in logged_output  # U+201C/U+201D -> "
            assert "--" in logged_output  # U+2014 -> --
            assert "..." in logged_output  # U+2026 -> ...
        finally:
            structlog.reset_defaults()


class TestEncodingConsistencyAcrossPlatforms:
    """Tests for cross-platform consistency (User Story 2)."""

    def test_same_output_on_utf8_and_cp1252(self) -> None:
        """Verify same input produces same sanitized output regardless of encoding."""
        # Create processors for both encodings
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "cp1252"
            cp1252_processor = EncodingSafeProcessor()

        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "utf-8"
            utf8_processor = EncodingSafeProcessor()

        event_dict: dict[str, Any] = {
            "event": "Test \u2018smart quotes\u2019 and \u2014 dashes",
            "nested": {
                "data": "More \u201cquotes\u201d here\u2026",
            },
        }

        result_cp1252 = cp1252_processor(None, "info", event_dict.copy())
        result_utf8 = utf8_processor(None, "info", event_dict.copy())

        # Smart replacements should be identical (explicit mappings)
        assert result_cp1252["event"] == result_utf8["event"]
        assert result_cp1252["nested"]["data"] == result_utf8["nested"]["data"]

        # Verify the actual replacements
        assert result_cp1252["event"] == "Test 'smart quotes' and -- dashes"
        assert result_cp1252["nested"]["data"] == 'More "quotes" here...'

    def test_utf8_preserves_more_characters(self) -> None:
        """Verify UTF-8 preserves characters that cp1252 would replace."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "cp1252"
            cp1252_processor = EncodingSafeProcessor()

        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "utf-8"
            utf8_processor = EncodingSafeProcessor()

        # Emoji is in UTF-8 but not cp1252
        event_dict: dict[str, Any] = {
            "event": "Emoji test \U0001f600",
        }

        result_cp1252 = cp1252_processor(None, "info", event_dict.copy())
        result_utf8 = utf8_processor(None, "info", event_dict.copy())

        # cp1252 should replace emoji, UTF-8 should preserve it
        assert "\U0001f600" not in result_cp1252["event"]
        assert "\U0001f600" in result_utf8["event"]
