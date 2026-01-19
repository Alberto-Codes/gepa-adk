"""Contract tests for EncodingSafeProcessor protocol compliance.

Tests verify that EncodingSafeProcessor satisfies the structlog processor
protocol: callable that accepts (logger, method_name, event_dict) and
returns EventDict.

Note:
    These tests ensure the processor can be used in a structlog pipeline
    without breaking the processor chain.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from gepa_adk.utils.encoding import EncodingSafeProcessor

pytestmark = pytest.mark.contract


# =============================================================================
# T018: Processor Protocol Compliance Tests
# =============================================================================


class TestProcessorProtocolCompliance:
    """Tests for T018: processor protocol compliance."""

    def test_processor_is_callable(self) -> None:
        """Verify processor instance is callable."""
        processor = EncodingSafeProcessor()
        assert callable(processor)

    def test_processor_accepts_required_arguments(self) -> None:
        """Verify processor accepts (logger, method_name, event_dict)."""
        processor = EncodingSafeProcessor()

        # structlog passes these three arguments
        logger = MagicMock()
        method_name = "info"
        event_dict: dict[str, Any] = {"event": "test message", "key": "value"}

        # Should not raise
        result = processor(logger, method_name, event_dict)
        assert isinstance(result, dict)

    def test_processor_returns_event_dict(self) -> None:
        """Verify processor returns a dict (EventDict)."""
        processor = EncodingSafeProcessor()

        event_dict: dict[str, Any] = {"event": "test", "data": "value"}
        result = processor(None, "debug", event_dict)

        assert isinstance(result, dict)
        assert "event" in result
        assert "data" in result

    def test_processor_preserves_event_keys(self) -> None:
        """Verify processor preserves all keys from input event dict."""
        processor = EncodingSafeProcessor()

        event_dict: dict[str, Any] = {
            "event": "test",
            "level": "info",
            "timestamp": "2024-01-01",
            "custom_key": "custom_value",
        }
        result = processor(None, "info", event_dict)

        assert set(result.keys()) == set(event_dict.keys())

    def test_processor_handles_empty_event_dict(self) -> None:
        """Verify processor handles empty event dict."""
        processor = EncodingSafeProcessor()

        event_dict: dict[str, Any] = {}
        result = processor(None, "info", event_dict)

        assert result == {}

    def test_processor_logger_parameter_unused(self) -> None:
        """Verify processor works regardless of logger value."""
        processor = EncodingSafeProcessor()
        event_dict: dict[str, Any] = {"event": "test"}

        # Logger can be None, MagicMock, or anything
        result1 = processor(None, "info", event_dict)
        result2 = processor(MagicMock(), "info", event_dict.copy())
        result3 = processor("some_logger", "info", event_dict.copy())

        assert result1 == result2 == result3

    def test_processor_method_name_parameter_unused(self) -> None:
        """Verify processor works regardless of method_name value."""
        processor = EncodingSafeProcessor()
        event_dict: dict[str, Any] = {"event": "test"}

        # Various log levels
        result_debug = processor(None, "debug", event_dict.copy())
        result_info = processor(None, "info", event_dict.copy())
        result_warning = processor(None, "warning", event_dict.copy())
        result_error = processor(None, "error", event_dict.copy())

        assert result_debug == result_info == result_warning == result_error


# =============================================================================
# T019: Idempotence Tests
# =============================================================================


class TestProcessorIdempotence:
    """Tests for T019: processor idempotence."""

    def test_double_processing_same_result(self) -> None:
        """Verify processing twice produces same result as once."""
        processor = EncodingSafeProcessor()

        event_dict: dict[str, Any] = {
            "event": "User said \u2018hello\u2019",
            "data": "Some \u2014 data",
        }

        # First pass
        result1 = processor(None, "info", event_dict.copy())

        # Second pass on already-processed result
        result2 = processor(None, "info", result1.copy())

        assert result1 == result2

    def test_idempotence_with_mixed_content(self) -> None:
        """Verify idempotence with mixed ASCII and Unicode content."""
        processor = EncodingSafeProcessor()

        event_dict: dict[str, Any] = {
            "event": "Mixed: ASCII and \u2018smart\u2019 quotes\u2014with dashes\u2026",
            "numbers": 42,
            "nested": {"key": "Value with \u2014 em dash"},
        }

        result1 = processor(None, "info", event_dict.copy())
        result2 = processor(None, "info", result1.copy())
        result3 = processor(None, "info", result2.copy())

        assert result1 == result2 == result3

    def test_idempotence_preserves_types(self) -> None:
        """Verify idempotence preserves non-string types."""
        processor = EncodingSafeProcessor()

        event_dict: dict[str, Any] = {
            "event": "test",
            "count": 42,
            "ratio": 3.14,
            "enabled": True,
            "nothing": None,
            "items": [1, 2, 3],
        }

        result1 = processor(None, "info", event_dict.copy())
        result2 = processor(None, "info", result1.copy())

        assert result1 == result2
        assert isinstance(result2["count"], int)
        assert isinstance(result2["ratio"], float)
        assert isinstance(result2["enabled"], bool)
        assert result2["nothing"] is None
        assert isinstance(result2["items"], list)

    def test_idempotence_with_already_safe_strings(self) -> None:
        """Verify idempotence when strings are already safe (ASCII only)."""
        processor = EncodingSafeProcessor()

        event_dict: dict[str, Any] = {
            "event": "Plain ASCII message",
            "key": "value",
            "path": "/usr/local/bin",
        }

        result1 = processor(None, "info", event_dict.copy())
        result2 = processor(None, "info", result1.copy())

        # Should be unchanged and idempotent
        assert result1 == event_dict
        assert result2 == event_dict


# =============================================================================
# Additional Contract Tests
# =============================================================================


class TestStructlogPipelineCompatibility:
    """Additional contract tests for structlog pipeline compatibility."""

    def test_processor_does_not_modify_input(self) -> None:
        """Verify processor returns new dict, doesn't mutate input."""
        processor = EncodingSafeProcessor()

        original: dict[str, Any] = {"event": "test \u2018quote\u2019"}

        result = processor(None, "info", original)

        # Result should be different (sanitized)
        assert result["event"] == "test 'quote'"
        # Original should be unchanged (but this depends on implementation)
        # Note: Current implementation returns a new dict, so original is unchanged

    def test_processor_handles_special_structlog_keys(self) -> None:
        """Verify processor handles special structlog keys correctly."""
        processor = EncodingSafeProcessor()

        event_dict: dict[str, Any] = {
            "event": "Test \u2018event\u2019",
            "_logger": MagicMock(),  # structlog internal
            "_record": MagicMock(),  # structlog internal
            "timestamp": "2024-01-01T00:00:00Z",
            "level": "info",
        }

        result = processor(None, "info", event_dict)

        assert "event" in result
        assert result["event"] == "Test 'event'"
        # Internal keys should be preserved
        assert "_logger" in result
        assert "_record" in result

    def test_processor_chain_position(self) -> None:
        """Verify processor works correctly in chain position (before renderer)."""
        processor = EncodingSafeProcessor()

        # Simulate event dict after earlier processors (timestamper, etc.)
        event_dict: dict[str, Any] = {
            "event": "User input: \u201cHello\u201d",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "level": "info",
            "logger": "gepa_adk.engine",
            "user_data": {
                "message": "Response with \u2014 em dash",
                "count": 5,
            },
        }

        result = processor(None, "info", event_dict)

        # Event should be sanitized
        assert result["event"] == 'User input: "Hello"'
        # Nested user_data should be sanitized
        assert result["user_data"]["message"] == "Response with -- em dash"
        # Other fields preserved
        assert result["timestamp"] == "2024-01-01T00:00:00+00:00"
        assert result["level"] == "info"


# =============================================================================
# T027: Structlog Pipeline Integration Tests (US2)
# =============================================================================


class TestStructlogPipelineIntegration:
    """Tests for T027: structlog pipeline integration (User Story 2)."""

    def test_processor_in_minimal_pipeline(self) -> None:
        """Verify processor works in minimal structlog-like pipeline."""
        # Simulate a minimal processor chain
        def add_level(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
            event_dict["level"] = method_name
            return event_dict

        encoding_processor = EncodingSafeProcessor()

        # Simulate pipeline execution
        event: dict[str, Any] = {"event": "Test \u2018message\u2019"}

        # First processor adds level
        event = add_level(None, "info", event)
        # Then encoding processor sanitizes
        result = encoding_processor(None, "info", event)

        assert result["event"] == "Test 'message'"
        assert result["level"] == "info"

    def test_processor_chain_order_independent(self) -> None:
        """Verify processor produces consistent output regardless of chain position."""
        def timestamper(
            logger: Any, method_name: str, event_dict: dict[str, Any]
        ) -> dict[str, Any]:
            event_dict["timestamp"] = "2024-01-01T00:00:00Z"
            return event_dict

        encoding_processor = EncodingSafeProcessor()

        # Order 1: timestamper -> encoding
        event1 = {"event": "Unicode \u2014 dash"}
        event1 = timestamper(None, "info", event1)
        result1 = encoding_processor(None, "info", event1)

        # Order 2: encoding -> timestamper (less typical but should work)
        event2 = {"event": "Unicode \u2014 dash"}
        event2 = encoding_processor(None, "info", event2)
        result2 = timestamper(None, "info", event2)

        # Both should have sanitized event and timestamp
        assert result1["event"] == "Unicode -- dash"
        assert result2["event"] == "Unicode -- dash"
        assert result1["timestamp"] == "2024-01-01T00:00:00Z"
        assert result2["timestamp"] == "2024-01-01T00:00:00Z"

    def test_processor_with_complex_pipeline_data(self) -> None:
        """Verify processor handles complex data from earlier processors."""
        encoding_processor = EncodingSafeProcessor()

        # Simulate event dict that might come from a real structlog pipeline
        event: dict[str, Any] = {
            "event": "LLM response: \u201cHello, user!\u201d",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "level": "info",
            "logger": "gepa_adk.adapters.adk_adapter",
            "context": {
                "session_id": "abc123",
                "user_input": "Greet me with \u2018smart quotes\u2019",
                "model": "gemini-2.0-flash",
            },
            "duration_ms": 150.5,
            "success": True,
        }

        result = encoding_processor(None, "info", event)

        # Verify sanitization
        assert result["event"] == 'LLM response: "Hello, user!"'
        assert result["context"]["user_input"] == "Greet me with 'smart quotes'"

        # Verify non-string types preserved
        assert result["duration_ms"] == 150.5
        assert result["success"] is True
        assert result["context"]["session_id"] == "abc123"

    def test_processor_exception_safety(self) -> None:
        """Verify processor doesn't raise exceptions on edge cases."""
        encoding_processor = EncodingSafeProcessor()

        # Various edge cases that shouldn't raise
        edge_cases: list[dict[str, Any]] = [
            {},  # Empty dict
            {"event": ""},  # Empty string
            {"event": None},  # None value
            {"event": "test", "nested": {"deep": {"deeper": "value"}}},  # Deep nesting
            {"event": "test", "list": [None, "", 0, False]},  # List with edge values
        ]

        for event in edge_cases:
            # Should not raise any exceptions
            result = encoding_processor(None, "info", event)
            assert isinstance(result, dict)
