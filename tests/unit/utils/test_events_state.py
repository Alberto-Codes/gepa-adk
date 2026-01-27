"""Unit tests for extract_output_from_state utility function.

Tests verify the shared utility for extracting agent output from ADK session
state using the output_key mechanism. Contract defined in:
specs/122-adk-session-state/contracts/extract-output-from-state.md
"""

from typing import Any

import pytest

from gepa_adk.utils.events import extract_output_from_state

pytestmark = pytest.mark.unit


class TestExtractOutputFromState:
    """Tests for extract_output_from_state function.

    Contract requirements:
    - Returns str if output_key found in state with non-None value
    - Returns None if output_key is None
    - Returns None if output_key not in session_state
    - Returns None if session_state[output_key] is None
    - Converts non-string values to string via str()
    - Does NOT raise exceptions for missing keys
    - Does NOT modify session_state
    - Function is pure (no side effects)
    """

    def test_extract_output_found(self) -> None:
        """Returns string when output_key exists in state with valid value."""
        state = {"proposed_instruction": "Be helpful and concise"}
        result = extract_output_from_state(state, "proposed_instruction")

        assert result == "Be helpful and concise"
        assert isinstance(result, str)

    def test_extract_output_missing_key(self) -> None:
        """Returns None when output_key not in state."""
        state = {"other_key": "value"}
        result = extract_output_from_state(state, "proposed_instruction")

        assert result is None

    def test_extract_output_none_output_key(self) -> None:
        """Returns None when output_key is None."""
        state = {"proposed_instruction": "text"}
        result = extract_output_from_state(state, None)

        assert result is None

    def test_extract_output_none_value(self) -> None:
        """Returns None when state value is None."""
        state: dict[str, Any] = {"proposed_instruction": None}
        result = extract_output_from_state(state, "proposed_instruction")

        assert result is None

    def test_extract_output_empty_state(self) -> None:
        """Returns None for empty state dict."""
        state: dict[str, Any] = {}
        result = extract_output_from_state(state, "proposed_instruction")

        assert result is None

    def test_extract_output_converts_to_string(self) -> None:
        """Converts non-string values to string."""
        state = {"count": 42}
        result = extract_output_from_state(state, "count")

        assert result == "42"
        assert isinstance(result, str)

    def test_extract_output_converts_float_to_string(self) -> None:
        """Converts float values to string."""
        state = {"score": 0.95}
        result = extract_output_from_state(state, "score")

        assert result == "0.95"
        assert isinstance(result, str)

    def test_extract_output_extracts_single_field_dict(self) -> None:
        """Extracts value from single-field dicts (structured output)."""
        state = {"data": {"selected_model": "gpt-4o"}}
        result = extract_output_from_state(state, "data")

        # Single-field dicts extract the field value directly
        assert result == "gpt-4o"
        assert isinstance(result, str)

    def test_extract_output_converts_multi_field_dict_to_string(self) -> None:
        """Converts multi-field dict values to string representation."""
        state = {"data": {"field1": "a", "field2": "b"}}
        result = extract_output_from_state(state, "data")

        # Multi-field dicts are stringified
        assert "field1" in result
        assert "field2" in result
        assert isinstance(result, str)

    def test_extract_output_converts_list_to_string(self) -> None:
        """Converts list values to string representation."""
        state = {"items": [1, 2, 3]}
        result = extract_output_from_state(state, "items")

        assert result == "[1, 2, 3]"
        assert isinstance(result, str)

    def test_extract_output_empty_string_value(self) -> None:
        """Returns empty string when state value is empty string."""
        state = {"proposed_instruction": ""}
        result = extract_output_from_state(state, "proposed_instruction")

        # Empty string is truthy in the context of "is not None"
        assert result == ""
        assert isinstance(result, str)

    def test_extract_output_whitespace_string(self) -> None:
        """Returns whitespace string when state value is whitespace."""
        state = {"proposed_instruction": "   "}
        result = extract_output_from_state(state, "proposed_instruction")

        assert result == "   "
        assert isinstance(result, str)

    def test_extract_output_multiline_string(self) -> None:
        """Handles multiline string values."""
        state = {"proposed_instruction": "Line 1\nLine 2\nLine 3"}
        result = extract_output_from_state(state, "proposed_instruction")

        assert result == "Line 1\nLine 2\nLine 3"

    def test_extract_output_empty_output_key(self) -> None:
        """Returns None when output_key is empty string (falsy)."""
        state = {"": "value", "other": "data"}
        result = extract_output_from_state(state, "")

        # Empty string is falsy, so should return None
        assert result is None

    def test_does_not_mutate_state(self) -> None:
        """Function does not modify the session_state dict."""
        state = {"proposed_instruction": "original"}
        original = state.copy()

        extract_output_from_state(state, "proposed_instruction")

        assert state == original

    def test_different_output_keys(self) -> None:
        """Works with different output_key names."""
        state = {
            "proposed_instruction": "instruction text",
            "critic_feedback": "feedback text",
            "generated_code": "code text",
        }

        result1 = extract_output_from_state(state, "proposed_instruction")
        result2 = extract_output_from_state(state, "critic_feedback")
        result3 = extract_output_from_state(state, "generated_code")

        assert result1 == "instruction text"
        assert result2 == "feedback text"
        assert result3 == "code text"


class TestExtractOutputFromStateEdgeCases:
    """Edge case tests for extract_output_from_state."""

    def test_boolean_true_value(self) -> None:
        """Converts boolean True to string."""
        state = {"flag": True}
        result = extract_output_from_state(state, "flag")

        assert result == "True"

    def test_boolean_false_value(self) -> None:
        """Converts boolean False to string (falsy but not None)."""
        state = {"flag": False}
        result = extract_output_from_state(state, "flag")

        assert result == "False"

    def test_zero_value(self) -> None:
        """Converts zero to string (falsy but not None)."""
        state = {"count": 0}
        result = extract_output_from_state(state, "count")

        assert result == "0"

    def test_special_characters_in_key(self) -> None:
        """Handles special characters in output_key."""
        state = {"output_key_with_underscore": "value"}
        result = extract_output_from_state(state, "output_key_with_underscore")

        assert result == "value"

    def test_unicode_string_value(self) -> None:
        """Handles unicode string values."""
        state = {"proposed_instruction": "こんにちは世界 🌍"}
        result = extract_output_from_state(state, "proposed_instruction")

        assert result == "こんにちは世界 🌍"

    def test_long_string_value(self) -> None:
        """Handles very long string values."""
        long_text = "x" * 10000
        state = {"proposed_instruction": long_text}
        result = extract_output_from_state(state, "proposed_instruction")

        assert result == long_text
        assert result is not None  # Type narrowing for len()
        assert len(result) == 10000


class TestExtractOutputFromStateUsagePattern:
    """Tests demonstrating the intended usage pattern with fallback."""

    def test_usage_with_fallback_state_found(self) -> None:
        """Demonstrates usage pattern: state extraction succeeds."""
        state = {"proposed_instruction": "Improved instruction"}

        # Primary: try state extraction
        output = extract_output_from_state(state, "proposed_instruction")

        # Fallback logic would go here if output is None
        if output is None:
            output = "fallback from events"

        assert output == "Improved instruction"

    def test_usage_with_fallback_state_missing(self) -> None:
        """Demonstrates usage pattern: state extraction fails, use fallback."""
        state = {"other_key": "value"}  # Missing proposed_instruction

        # Primary: try state extraction
        output = extract_output_from_state(state, "proposed_instruction")

        # Fallback logic
        if output is None:
            output = "fallback from events"

        assert output == "fallback from events"

    def test_usage_with_fallback_no_output_key(self) -> None:
        """Demonstrates usage pattern: no output_key configured."""
        state = {"proposed_instruction": "text"}

        # Primary: try state extraction with None output_key
        output = extract_output_from_state(state, None)

        # Fallback logic
        if output is None:
            output = "fallback from events"

        assert output == "fallback from events"
