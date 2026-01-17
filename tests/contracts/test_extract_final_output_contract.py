"""Contract tests for extract_final_output function.

Verifies the function contract as specified in:
specs/033-event-output-extraction/contracts/extract_final_output.md

Tests ensure the function:
1. Returns str always (never None)
2. Handles missing attributes gracefully
3. Filters thought parts correctly
4. Supports both extraction modes
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.contracts


class MockPart:
    """Mock ADK Part object for testing."""

    def __init__(self, text: str | None = None, thought: bool | None = None) -> None:
        """Initialize mock part.

        Args:
            text: Text content of the part.
            thought: Whether this is a thought/reasoning part.
        """
        self.text = text
        if thought is not None:
            self.thought = thought


class MockContent:
    """Mock ADK Content object for testing."""

    def __init__(self, parts: list[MockPart] | None = None) -> None:
        """Initialize mock content.

        Args:
            parts: List of mock parts.
        """
        self.parts = parts


class MockActions:
    """Mock ADK EventActions object for testing."""

    def __init__(self, response_content: list[MockPart] | None = None) -> None:
        """Initialize mock actions.

        Args:
            response_content: List of response content parts.
        """
        self.response_content = response_content


class MockEvent:
    """Mock ADK Event object for testing."""

    def __init__(
        self,
        is_final: bool = True,
        actions: MockActions | None = None,
        content: MockContent | None = None,
    ) -> None:
        """Initialize mock event.

        Args:
            is_final: Whether this is a final response event.
            actions: Mock actions object.
            content: Mock content object.
        """
        self._is_final = is_final
        self.actions = actions
        self.content = content

    def is_final_response(self) -> bool:
        """Return whether this is a final response event."""
        return self._is_final


class TestExtractFinalOutputContract:
    """Contract tests for extract_final_output function."""

    def test_returns_string_type(self) -> None:
        """Contract: Function MUST return str type (never None)."""
        from gepa_adk.utils.events import extract_final_output

        # Empty list
        result = extract_final_output([])
        assert isinstance(result, str)

        # Event with content
        event = MockEvent(
            is_final=True,
            content=MockContent(parts=[MockPart(text="Hello")]),
        )
        result = extract_final_output([event])
        assert isinstance(result, str)

    def test_empty_events_returns_empty_string(self) -> None:
        """Contract: Empty events list MUST return empty string."""
        from gepa_adk.utils.events import extract_final_output

        result = extract_final_output([])
        assert result == ""

    def test_no_exceptions_for_missing_attributes(self) -> None:
        """Contract: MUST NOT raise exceptions for missing attributes."""
        from gepa_adk.utils.events import extract_final_output

        # Event without actions or content attributes
        minimal_event = MagicMock()
        minimal_event.is_final_response.return_value = True
        del minimal_event.actions
        del minimal_event.content

        # Should not raise
        result = extract_final_output([minimal_event])
        assert isinstance(result, str)

    def test_does_not_modify_input(self) -> None:
        """Contract: Original events list MUST NOT be modified."""
        from gepa_adk.utils.events import extract_final_output

        events = [
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="Test")]),
            )
        ]
        original_len = len(events)

        extract_final_output(events)

        assert len(events) == original_len

    def test_filters_thought_parts(self) -> None:
        """Contract: Parts with thought=True MUST be excluded."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            content=MockContent(
                parts=[
                    MockPart(text="Thinking...", thought=True),
                    MockPart(text="Answer"),
                ]
            ),
        )

        result = extract_final_output([event])
        assert result == "Answer"
        assert "Thinking" not in result

    def test_all_thought_parts_returns_empty(self) -> None:
        """Contract: If all parts have thought=True, MUST return empty string."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            content=MockContent(
                parts=[
                    MockPart(text="Just thinking...", thought=True),
                ]
            ),
        )

        result = extract_final_output([event])
        assert result == ""

    def test_prefers_response_content_over_content_parts(self) -> None:
        """Contract: response_content MUST be preferred over content.parts."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            actions=MockActions(
                response_content=[MockPart(text="From response_content")]
            ),
            content=MockContent(parts=[MockPart(text="From content.parts")]),
        )

        result = extract_final_output([event])
        assert result == "From response_content"

    def test_fallback_to_content_parts(self) -> None:
        """Contract: MUST fallback to content.parts when response_content unavailable."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            actions=None,
            content=MockContent(parts=[MockPart(text="From content.parts")]),
        )

        result = extract_final_output([event])
        assert result == "From content.parts"

    def test_skips_non_final_events(self) -> None:
        """Contract: Non-final events MUST be skipped."""
        from gepa_adk.utils.events import extract_final_output

        events = [
            MockEvent(
                is_final=False,
                content=MockContent(parts=[MockPart(text="Not final")]),
            ),
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="Final answer")]),
            ),
        ]

        result = extract_final_output(events)
        assert result == "Final answer"

    def test_prefer_concatenated_parameter_exists(self) -> None:
        """Contract: Function MUST accept prefer_concatenated parameter."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            content=MockContent(parts=[MockPart(text="Test")]),
        )

        # Should not raise for either value
        result_false = extract_final_output([event], prefer_concatenated=False)
        result_true = extract_final_output([event], prefer_concatenated=True)

        assert isinstance(result_false, str)
        assert isinstance(result_true, str)

    def test_concatenated_mode_joins_all_parts(self) -> None:
        """Contract: prefer_concatenated=True MUST concatenate all parts."""
        from gepa_adk.utils.events import extract_final_output

        events = [
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="chunk1")]),
            ),
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="chunk2")]),
            ),
        ]

        result = extract_final_output(events, prefer_concatenated=True)
        assert "chunk1" in result
        assert "chunk2" in result

    def test_default_mode_returns_first_text_only(self) -> None:
        """Contract: Default mode MUST return first text part only."""
        from gepa_adk.utils.events import extract_final_output

        events = [
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="first")]),
            ),
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="second")]),
            ),
        ]

        result = extract_final_output(events, prefer_concatenated=False)
        assert result == "first"

    def test_missing_thought_attribute_treated_as_false(self) -> None:
        """Contract: Missing thought attribute MUST be treated as False."""
        from gepa_adk.utils.events import extract_final_output

        # Part without thought attribute
        part = MockPart(text="No thought attr")
        # Explicitly remove thought attribute if present
        if hasattr(part, "thought"):
            delattr(part, "thought")

        event = MockEvent(
            is_final=True,
            content=MockContent(parts=[part]),
        )

        result = extract_final_output([event])
        assert result == "No thought attr"
