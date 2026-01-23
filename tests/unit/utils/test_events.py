"""Unit tests for trajectory extraction utilities.

Tests verify redaction, truncation, and extraction logic for trajectory data.
Uses pytest conventions with three-layer testing approach.
"""

import pytest

from gepa_adk.domain.trajectory import ADKTrajectory
from gepa_adk.domain.types import TrajectoryConfig
from gepa_adk.utils.events import (
    _redact_sensitive,
    _truncate_strings,
    extract_trajectory,
    partition_events_by_agent,
)

pytestmark = pytest.mark.unit


class TestRedactSensitive:
    """Tests for _redact_sensitive function."""

    def test_redact_single_key_in_flat_dict(self) -> None:
        """Redact single sensitive key in flat dictionary."""
        data = {"user": "alice", "password": "secret123"}
        result = _redact_sensitive(data, ("password",))

        assert result["user"] == "alice"
        assert result["password"] == "[REDACTED]"

    def test_redact_multiple_keys(self) -> None:
        """Redact multiple sensitive keys in same dictionary."""
        data = {
            "user": "alice",
            "password": "pass",
            "api_key": "key123",
            "name": "test",
        }
        result = _redact_sensitive(data, ("password", "api_key"))

        assert result["user"] == "alice"
        assert result["name"] == "test"
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"

    def test_redact_nested_dict(self) -> None:
        """Redact sensitive keys in nested dictionaries."""
        data = {
            "config": {
                "db": {"host": "localhost", "password": "dbpass"},
                "api": {"url": "https://api.example.com", "token": "abc123"},
            }
        }
        result = _redact_sensitive(data, ("password", "token"))

        assert result["config"]["db"]["host"] == "localhost"
        assert result["config"]["db"]["password"] == "[REDACTED]"
        assert result["config"]["api"]["url"] == "https://api.example.com"
        assert result["config"]["api"]["token"] == "[REDACTED]"

    def test_redact_in_list(self) -> None:
        """Redact sensitive keys in list of dictionaries."""
        data = [
            {"name": "user1", "password": "pass1"},
            {"name": "user2", "password": "pass2"},
        ]
        result = _redact_sensitive(data, ("password",))

        assert result[0]["name"] == "user1"
        assert result[0]["password"] == "[REDACTED]"
        assert result[1]["name"] == "user2"
        assert result[1]["password"] == "[REDACTED]"

    def test_redact_in_tuple(self) -> None:
        """Redact sensitive keys in tuple of dictionaries."""
        data = (
            {"name": "config1", "api_key": "key1"},
            {"name": "config2", "api_key": "key2"},
        )
        result = _redact_sensitive(data, ("api_key",))

        assert isinstance(result, tuple)
        assert result[0]["name"] == "config1"
        assert result[0]["api_key"] == "[REDACTED]"
        assert result[1]["name"] == "config2"
        assert result[1]["api_key"] == "[REDACTED]"

    def test_redact_deeply_nested(self) -> None:
        """Redact sensitive keys in deeply nested structures."""
        data = {
            "level1": {
                "level2": {
                    "level3": [
                        {"password": "deep_secret", "public": "visible"},
                    ],
                },
            },
        }
        result = _redact_sensitive(data, ("password",))

        assert result["level1"]["level2"]["level3"][0]["public"] == "visible"
        assert result["level1"]["level2"]["level3"][0]["password"] == "[REDACTED]"

    def test_redact_no_sensitive_keys_found(self) -> None:
        """Return unchanged data when no sensitive keys match."""
        data = {"user": "alice", "email": "alice@example.com"}
        result = _redact_sensitive(data, ("password", "api_key"))

        assert result == data

    def test_redact_empty_dict(self) -> None:
        """Handle empty dictionary."""
        data = {}
        result = _redact_sensitive(data, ("password",))

        assert result == {}

    def test_redact_primitives_unchanged(self) -> None:
        """Primitive types pass through unchanged."""
        assert _redact_sensitive("text", ("password",)) == "text"
        assert _redact_sensitive(42, ("password",)) == 42
        assert _redact_sensitive(True, ("password",)) is True
        assert _redact_sensitive(None, ("password",)) is None

    def test_redact_custom_marker(self) -> None:
        """Use custom redaction marker."""
        data = {"password": "secret"}
        result = _redact_sensitive(data, ("password",), marker="***")

        assert result["password"] == "***"

    def test_redact_case_sensitive(self) -> None:
        """Redaction is case-sensitive (exact match only)."""
        data = {"password": "secret", "Password": "secret2", "PASSWORD": "secret3"}
        result = _redact_sensitive(data, ("password",))

        assert result["password"] == "[REDACTED]"
        assert result["Password"] == "secret2"
        assert result["PASSWORD"] == "secret3"

    def test_redact_does_not_mutate_input(self) -> None:
        """Original data structure is not modified."""
        data = {"password": "secret", "user": "alice"}
        original = data.copy()
        _redact_sensitive(data, ("password",))

        assert data == original


class TestTruncateStrings:
    """Tests for _truncate_strings function."""

    def test_truncate_long_string(self) -> None:
        """Truncate string exceeding max length."""
        data = "a" * 100
        result = _truncate_strings(data, max_length=50)

        assert result == "a" * 50 + "...[truncated 50 chars]"

    def test_truncate_short_string_unchanged(self) -> None:
        """String within limit passes through unchanged."""
        data = "short"
        result = _truncate_strings(data, max_length=50)

        assert result == "short"

    def test_truncate_exact_length_unchanged(self) -> None:
        """String at exact limit passes through unchanged."""
        data = "a" * 50
        result = _truncate_strings(data, max_length=50)

        assert result == "a" * 50

    def test_truncate_strings_in_dict(self) -> None:
        """Truncate strings in dictionary values."""
        data = {
            "short": "hello",
            "long": "x" * 200,
            "number": 42,
        }
        result = _truncate_strings(data, max_length=100)

        assert result["short"] == "hello"
        assert result["long"] == "x" * 100 + "...[truncated 100 chars]"
        assert result["number"] == 42

    def test_truncate_strings_in_list(self) -> None:
        """Truncate strings in list elements."""
        data = ["short", "b" * 200, "c" * 50]
        result = _truncate_strings(data, max_length=100)

        assert result[0] == "short"
        assert result[1] == "b" * 100 + "...[truncated 100 chars]"
        assert result[2] == "c" * 50

    def test_truncate_strings_in_tuple(self) -> None:
        """Truncate strings in tuple elements."""
        data = ("short", "d" * 300)
        result = _truncate_strings(data, max_length=100)

        assert isinstance(result, tuple)
        assert result[0] == "short"
        assert result[1] == "d" * 100 + "...[truncated 200 chars]"

    def test_truncate_nested_structures(self) -> None:
        """Truncate strings in deeply nested structures."""
        data = {
            "level1": {
                "level2": [
                    {"content": "e" * 500},
                ],
            },
        }
        result = _truncate_strings(data, max_length=100)

        expected = "e" * 100 + "...[truncated 400 chars]"
        assert result["level1"]["level2"][0]["content"] == expected

    def test_truncate_non_string_types_unchanged(self) -> None:
        """Non-string types pass through unchanged."""
        data = {
            "number": 42,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
        }
        result = _truncate_strings(data, max_length=10)

        assert result == data

    def test_truncate_empty_string(self) -> None:
        """Empty string passes through unchanged."""
        result = _truncate_strings("", max_length=50)
        assert result == ""

    def test_truncate_marker_format(self) -> None:
        """Truncation marker includes correct character count."""
        data = "a" * 1000
        result = _truncate_strings(data, max_length=100)

        assert result.endswith("...[truncated 900 chars]")

    def test_truncate_does_not_mutate_input(self) -> None:
        """Original data structure is not modified."""
        data = {"text": "x" * 200}
        original = data.copy()
        _truncate_strings(data, max_length=50)

        assert data == original


class TestExtractTrajectory:
    """Tests for extract_trajectory function."""

    def test_extract_empty_events(self) -> None:
        """Extract trajectory from empty events list."""
        trajectory = extract_trajectory(events=[], final_output="Empty run")

        assert isinstance(trajectory, ADKTrajectory)
        assert trajectory.tool_calls == ()
        assert trajectory.state_deltas == ()
        assert trajectory.token_usage is None
        assert trajectory.final_output == "Empty run"
        assert trajectory.error is None

    def test_extract_with_default_config(self) -> None:
        """Extract trajectory with default configuration."""
        trajectory = extract_trajectory(events=[], final_output="Test output")

        assert isinstance(trajectory, ADKTrajectory)
        assert trajectory.final_output == "Test output"

    def test_extract_with_custom_config(self) -> None:
        """Extract trajectory with custom configuration."""
        config = TrajectoryConfig(include_tool_calls=False)
        trajectory = extract_trajectory(events=[], config=config)

        assert isinstance(trajectory, ADKTrajectory)

    def test_extract_with_error(self) -> None:
        """Extract trajectory with error message."""
        trajectory = extract_trajectory(
            events=[],
            final_output="",
            error="Agent timeout after 30s",
        )

        assert trajectory.error == "Agent timeout after 30s"
        assert trajectory.final_output == ""

    def test_extract_returns_immutable_trajectory(self) -> None:
        """Extracted trajectory is immutable (frozen dataclass)."""
        trajectory = extract_trajectory(events=[], final_output="Test")

        with pytest.raises(AttributeError, match="cannot assign to field"):
            trajectory.final_output = "Modified"  # type: ignore[misc]


class TestExtractToolCalls:
    """Tests for tool call extraction functionality."""

    def test_extract_tool_calls_with_include_true(self, mocker) -> None:
        """Extract tool calls when include_tool_calls=True (default)."""
        # Create mock event with function call
        mock_fc = mocker.MagicMock()
        mock_fc.name = "search"
        mock_fc.args = {"query": "AI"}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(include_tool_calls=True)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert len(trajectory.tool_calls) == 1
        assert trajectory.tool_calls[0].name == "search"
        assert trajectory.tool_calls[0].arguments == {"query": "AI"}
        assert trajectory.tool_calls[0].result is None
        assert trajectory.tool_calls[0].timestamp == 0.0

    def test_extract_tool_calls_with_include_false(self, mocker) -> None:
        """Skip tool call extraction when include_tool_calls=False."""
        mock_fc = mocker.MagicMock()
        mock_fc.name = "search"
        mock_fc.args = {"query": "AI"}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(include_tool_calls=False)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert trajectory.tool_calls == ()

    def test_extract_multiple_tool_calls(self, mocker) -> None:
        """Extract multiple tool calls in chronological order."""
        mock_fc1 = mocker.MagicMock()
        mock_fc1.name = "search"
        mock_fc1.args = {"query": "AI"}

        mock_fc2 = mocker.MagicMock()
        mock_fc2.name = "calculator"
        mock_fc2.args = {"expression": "2+2"}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc1, mock_fc2]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        trajectory = extract_trajectory(events=[mock_event])

        assert len(trajectory.tool_calls) == 2
        assert trajectory.tool_calls[0].name == "search"
        assert trajectory.tool_calls[1].name == "calculator"

    def test_extract_tool_calls_no_args(self, mocker) -> None:
        """Handle tool calls with missing or non-dict args."""
        mock_fc = mocker.MagicMock()
        mock_fc.name = "hello"
        mock_fc.args = None  # Missing args

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        trajectory = extract_trajectory(events=[mock_event])

        assert len(trajectory.tool_calls) == 1
        assert trajectory.tool_calls[0].arguments == {}

    def test_extract_tool_calls_unknown_name(self, mocker) -> None:
        """Handle tool calls with missing name attribute."""
        mock_fc = mocker.MagicMock(spec=[])  # No 'name' attribute
        mock_fc.args = {"key": "value"}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        trajectory = extract_trajectory(events=[mock_event])

        assert len(trajectory.tool_calls) == 1
        assert trajectory.tool_calls[0].name == "unknown"


class TestExtractStateDeltas:
    """Tests for state delta extraction functionality."""

    def test_extract_state_deltas_with_include_true(self, mocker) -> None:
        """Extract state deltas when include_state_deltas=True (default)."""
        mock_actions = mocker.MagicMock()
        mock_actions.state_delta = {"search_count": 1}

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(include_state_deltas=True)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert len(trajectory.state_deltas) == 1
        assert trajectory.state_deltas[0] == {"search_count": 1}

    def test_extract_state_deltas_with_include_false(self, mocker) -> None:
        """Skip state delta extraction when include_state_deltas=False."""
        mock_actions = mocker.MagicMock()
        mock_actions.state_delta = {"search_count": 1}

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(include_state_deltas=False)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert trajectory.state_deltas == ()

    def test_extract_multiple_state_deltas(self, mocker) -> None:
        """Extract multiple state deltas in order."""
        mock_event1 = mocker.MagicMock()
        mock_event1.actions = mocker.MagicMock()
        mock_event1.actions.state_delta = {"count": 1}

        mock_event2 = mocker.MagicMock()
        mock_event2.actions = mocker.MagicMock()
        mock_event2.actions.state_delta = {"count": 2}

        trajectory = extract_trajectory(events=[mock_event1, mock_event2])

        assert len(trajectory.state_deltas) == 2
        assert trajectory.state_deltas[0] == {"count": 1}
        assert trajectory.state_deltas[1] == {"count": 2}


class TestExtractTokenUsage:
    """Tests for token usage extraction functionality."""

    def test_extract_token_usage_with_include_true(self, mocker) -> None:
        """Extract token usage when include_token_usage=True (default)."""
        mock_metadata = mocker.MagicMock()
        mock_metadata.prompt_token_count = 100
        mock_metadata.candidates_token_count = 50
        mock_metadata.total_token_count = 150

        mock_event = mocker.MagicMock()
        mock_event.usage_metadata = mock_metadata

        config = TrajectoryConfig(include_token_usage=True)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert trajectory.token_usage is not None
        assert trajectory.token_usage.input_tokens == 100
        assert trajectory.token_usage.output_tokens == 50
        assert trajectory.token_usage.total_tokens == 150

    def test_extract_token_usage_with_include_false(self, mocker) -> None:
        """Skip token usage extraction when include_token_usage=False."""
        mock_metadata = mocker.MagicMock()
        mock_metadata.prompt_token_count = 100
        mock_metadata.candidates_token_count = 50
        mock_metadata.total_token_count = 150

        mock_event = mocker.MagicMock()
        mock_event.usage_metadata = mock_metadata

        config = TrajectoryConfig(include_token_usage=False)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert trajectory.token_usage is None


class TestRedactionIntegration:
    """Tests for redaction applied during trajectory extraction."""

    def test_redact_tool_call_arguments(self, mocker) -> None:
        """Redact sensitive keys in tool call arguments."""
        mock_fc = mocker.MagicMock()
        mock_fc.name = "auth"
        mock_fc.args = {"username": "alice", "password": "secret"}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(redact_sensitive=True)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert trajectory.tool_calls[0].arguments["username"] == "alice"
        assert trajectory.tool_calls[0].arguments["password"] == "[REDACTED]"

    def test_extract_tool_call_without_result(self, mocker) -> None:
        """Extract tool call with no result (result field not yet implemented).

        Note: Currently tool call results are not captured from function_response
        events. This test verifies that tool calls can be extracted even when
        the result field is None, which is the current implementation behavior.
        """
        mock_fc = mocker.MagicMock()
        mock_fc.name = "get_config"
        mock_fc.args = {}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(redact_sensitive=True)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        # Verify tool call was extracted
        assert len(trajectory.tool_calls) == 1
        assert trajectory.tool_calls[0].name == "get_config"
        assert trajectory.tool_calls[0].result is None

    def test_redact_state_deltas(self, mocker) -> None:
        """Redact sensitive keys in state deltas."""
        mock_actions = mocker.MagicMock()
        mock_actions.state_delta = {"user": "alice", "api_key": "secret123"}

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(redact_sensitive=True, sensitive_keys=("api_key",))
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert trajectory.state_deltas[0]["user"] == "alice"
        assert trajectory.state_deltas[0]["api_key"] == "[REDACTED]"

    def test_redaction_disabled(self, mocker) -> None:
        """Skip redaction when redact_sensitive=False."""
        mock_fc = mocker.MagicMock()
        mock_fc.name = "auth"
        mock_fc.args = {"password": "secret"}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(redact_sensitive=False)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert trajectory.tool_calls[0].arguments["password"] == "secret"

    def test_custom_sensitive_keys(self, mocker) -> None:
        """Use custom sensitive keys for redaction."""
        mock_fc = mocker.MagicMock()
        mock_fc.name = "store"
        mock_fc.args = {"ssn": "123-45-6789", "name": "Alice"}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(sensitive_keys=("ssn",))
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert trajectory.tool_calls[0].arguments["name"] == "Alice"
        assert trajectory.tool_calls[0].arguments["ssn"] == "[REDACTED]"


class TestTruncationIntegration:
    """Tests for truncation applied during trajectory extraction."""

    def test_truncate_tool_call_arguments(self, mocker) -> None:
        """Truncate long strings in tool call arguments."""
        mock_fc = mocker.MagicMock()
        mock_fc.name = "process"
        mock_fc.args = {"data": "x" * 200}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(max_string_length=100)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        result = trajectory.tool_calls[0].arguments["data"]
        assert result == "x" * 100 + "...[truncated 100 chars]"

    def test_truncate_state_deltas(self, mocker) -> None:
        """Truncate long strings in state deltas."""
        mock_actions = mocker.MagicMock()
        mock_actions.state_delta = {"content": "y" * 300}

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(max_string_length=100)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        result = trajectory.state_deltas[0]["content"]
        assert result == "y" * 100 + "...[truncated 200 chars]"

    def test_truncation_disabled(self, mocker) -> None:
        """Skip truncation when max_string_length=None."""
        mock_fc = mocker.MagicMock()
        mock_fc.name = "store"
        mock_fc.args = {"data": "z" * 1000}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(max_string_length=None)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert trajectory.tool_calls[0].arguments["data"] == "z" * 1000


class TestRedactionAndTruncationOrder:
    """Tests for correct order of redaction before truncation."""

    def test_redaction_before_truncation(self, mocker) -> None:
        """Redacted values are not truncated (already short)."""
        mock_fc = mocker.MagicMock()
        mock_fc.name = "auth"
        mock_fc.args = {"password": "x" * 200, "data": "y" * 200}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        config = TrajectoryConfig(
            redact_sensitive=True,
            max_string_length=100,
        )
        trajectory = extract_trajectory(events=[mock_event], config=config)

        # password is redacted (becomes short "[REDACTED]")
        assert trajectory.tool_calls[0].arguments["password"] == "[REDACTED]"
        # data is truncated (not redacted)
        assert "truncated 100 chars" in trajectory.tool_calls[0].arguments["data"]


class TestEdgeCases:
    """Tests for edge cases and graceful degradation."""

    def test_empty_events_list(self) -> None:
        """Handle empty events list gracefully."""
        trajectory = extract_trajectory(events=[], final_output="No events")

        assert trajectory.tool_calls == ()
        assert trajectory.state_deltas == ()
        assert trajectory.token_usage is None
        assert trajectory.final_output == "No events"
        assert trajectory.error is None

    def test_events_with_missing_attributes(self, mocker) -> None:
        """Handle events with missing or None attributes."""
        mock_event1 = mocker.MagicMock(spec=[])  # No attributes
        mock_event2 = mocker.MagicMock()
        mock_event2.actions = None  # actions is None

        trajectory = extract_trajectory(events=[mock_event1, mock_event2])

        assert trajectory.tool_calls == ()
        assert trajectory.state_deltas == ()

    def test_missing_token_usage_metadata(self, mocker) -> None:
        """Return None token_usage when metadata missing."""
        mock_event = mocker.MagicMock(spec=[])  # No usage_metadata

        config = TrajectoryConfig(include_token_usage=True)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        assert trajectory.token_usage is None

    def test_none_response_handling(self, mocker) -> None:
        """Handle None values in tool call results."""
        mock_fc = mocker.MagicMock()
        mock_fc.name = "test"
        mock_fc.args = None  # None args

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        trajectory = extract_trajectory(events=[mock_event])

        assert len(trajectory.tool_calls) == 1
        assert trajectory.tool_calls[0].arguments == {}  # Empty dict, not None

    def test_graceful_degradation_with_partial_events(self, mocker) -> None:
        """Extract what's available even with incomplete event data."""
        # Event 1: Has tool call but no state delta
        mock_fc1 = mocker.MagicMock()
        mock_fc1.name = "tool1"
        mock_fc1.args = {}

        mock_actions1 = mocker.MagicMock()
        mock_actions1.function_calls = [mock_fc1]
        mock_actions1.state_delta = None

        mock_event1 = mocker.MagicMock()
        mock_event1.actions = mock_actions1
        mock_event1.usage_metadata = None

        # Event 2: Has state delta but no tool call
        mock_actions2 = mocker.MagicMock()
        mock_actions2.function_calls = None
        mock_actions2.state_delta = {"key": "value"}

        mock_event2 = mocker.MagicMock()
        mock_event2.actions = mock_actions2

        # Event 3: Has token usage but nothing else
        mock_metadata = mocker.MagicMock()
        mock_metadata.prompt_token_count = 10
        mock_metadata.candidates_token_count = 5
        mock_metadata.total_token_count = 15

        mock_event3 = mocker.MagicMock()
        mock_event3.usage_metadata = mock_metadata

        trajectory = extract_trajectory(events=[mock_event1, mock_event2, mock_event3])

        # Should extract all available data
        assert len(trajectory.tool_calls) == 1
        assert len(trajectory.state_deltas) == 1
        assert trajectory.token_usage is not None
        assert trajectory.token_usage.total_tokens == 15


# =============================================================================
# Tests for extract_final_output function (TC-001 through TC-010)
# =============================================================================


class MockPart:
    """Mock ADK Part object for testing extract_final_output."""

    def __init__(self, text: str | None = None, thought: bool | None = None) -> None:
        """Initialize mock part."""
        self.text = text
        if thought is not None:
            self.thought = thought


class MockContent:
    """Mock ADK Content object for testing."""

    def __init__(self, parts: list[MockPart] | None = None) -> None:
        """Initialize mock content."""
        self.parts = parts


class MockActions:
    """Mock ADK EventActions object for testing."""

    def __init__(self, response_content: list[MockPart] | None = None) -> None:
        """Initialize mock actions."""
        self.response_content = response_content


class MockEvent:
    """Mock ADK Event object for testing."""

    def __init__(
        self,
        is_final: bool = True,
        actions: MockActions | None = None,
        content: MockContent | None = None,
    ) -> None:
        """Initialize mock event."""
        self._is_final = is_final
        self.actions = actions
        self.content = content

    def is_final_response(self) -> bool:
        """Return whether this is a final response event."""
        return self._is_final


class TestExtractFinalOutput:
    """Unit tests for extract_final_output function.

    Tests cover TC-001 through TC-010 from the contract specification.
    Verifies FR-001, FR-002, FR-003, FR-004, FR-005, FR-012, FR-013.
    """

    def test_tc001_extract_from_response_content(self) -> None:
        """TC-001: Extract from response_content when available."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            actions=MockActions(response_content=[MockPart(text="Hello")]),
        )

        result = extract_final_output([event])
        assert result == "Hello"

    def test_tc002_fallback_to_content_parts(self) -> None:
        """TC-002: Fallback to content.parts when response_content unavailable."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            actions=None,
            content=MockContent(parts=[MockPart(text="World")]),
        )

        result = extract_final_output([event])
        assert result == "World"

    def test_tc003_filter_thought_parts(self) -> None:
        """TC-003: Filter out parts where thought=True."""
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

    def test_tc004_all_thought_parts_returns_empty(self) -> None:
        """TC-004: Return empty string when all parts have thought=True."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            content=MockContent(parts=[MockPart(text="Thinking...", thought=True)]),
        )

        result = extract_final_output([event])
        assert result == ""

    def test_tc005_empty_events_list(self) -> None:
        """TC-005: Return empty string for empty events list."""
        from gepa_adk.utils.events import extract_final_output

        result = extract_final_output([])
        assert result == ""

    def test_tc006_concatenated_mode(self) -> None:
        """TC-006: Concatenate all parts when prefer_concatenated=True."""
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
        assert result == "chunk1chunk2"

    def test_tc007_skip_non_final_events(self) -> None:
        """TC-007: Skip events where is_final_response() returns False."""
        from gepa_adk.utils.events import extract_final_output

        events = [
            MockEvent(
                is_final=False,
                content=MockContent(parts=[MockPart(text="Not final")]),
            ),
        ]

        result = extract_final_output(events)
        assert result == ""

    def test_tc008_multiple_events_default_mode(self) -> None:
        """TC-008: Default mode returns text from LAST final event.

        For multi-agent pipelines (SequentialAgent), the last final response
        is the pipeline result. Returning the first would score intermediate
        outputs instead of the final result.
        """
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

        result = extract_final_output(events)
        assert result == "second"

    def test_multi_agent_pipeline_returns_last_agent_output(self) -> None:
        """Multi-agent pipeline (SequentialAgent) returns final agent's output.

        Simulates a Generator → Refiner → Writer pipeline where each agent
        produces a final response. The scorer should receive Writer's output.
        """
        from gepa_adk.utils.events import extract_final_output

        events = [
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="Generator output")]),
            ),
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="Refiner output")]),
            ),
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="Writer output")]),
            ),
        ]

        result = extract_final_output(events)
        assert result == "Writer output"

    def test_last_output_skips_empty_intermediate_events(self) -> None:
        """Default mode skips empty/thought-only events and returns LAST non-empty.

        Verifies that intermediate events with empty text don't reset the
        last_output tracking - we should get the last event with actual content.
        """
        from gepa_adk.utils.events import extract_final_output

        events = [
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="First output")]),
            ),
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="")]),  # Empty
            ),
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text=None)]),  # None
            ),
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="Last output")]),
            ),
        ]

        result = extract_final_output(events)
        assert result == "Last output"

    def test_tc009_graceful_handling_missing_attributes(self) -> None:
        """TC-009: Gracefully handle event without actions or content."""
        from gepa_adk.utils.events import extract_final_output

        # Create minimal event with only is_final_response method
        class MinimalEvent:
            def is_final_response(self) -> bool:
                return True

        result = extract_final_output([MinimalEvent()])
        assert result == ""

    def test_tc010_part_without_thought_attribute(self) -> None:
        """TC-010: Treat missing thought attribute as False."""
        from gepa_adk.utils.events import extract_final_output

        # Part without thought attribute
        part = MockPart(text="Text")
        if hasattr(part, "thought"):
            delattr(part, "thought")

        event = MockEvent(
            is_final=True,
            content=MockContent(parts=[part]),
        )

        result = extract_final_output([event])
        assert result == "Text"

    def test_empty_text_parts_skipped(self) -> None:
        """Parts with empty or None text should be skipped."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            content=MockContent(
                parts=[
                    MockPart(text=""),
                    MockPart(text=None),
                    MockPart(text="Valid"),
                ]
            ),
        )

        result = extract_final_output([event])
        assert result == "Valid"

    def test_response_content_with_thought_filtering(self) -> None:
        """Thought filtering should work on response_content too."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            actions=MockActions(
                response_content=[
                    MockPart(text="Reasoning...", thought=True),
                    MockPart(text="Final answer"),
                ]
            ),
        )

        result = extract_final_output([event])
        assert result == "Final answer"

    def test_concatenated_mode_filters_thoughts(self) -> None:
        """Concatenated mode should also filter thought parts."""
        from gepa_adk.utils.events import extract_final_output

        events = [
            MockEvent(
                is_final=True,
                content=MockContent(
                    parts=[
                        MockPart(text="Thinking...", thought=True),
                        MockPart(text="chunk1"),
                    ]
                ),
            ),
            MockEvent(
                is_final=True,
                content=MockContent(parts=[MockPart(text="chunk2")]),
            ),
        ]

        result = extract_final_output(events, prefer_concatenated=True)
        assert "Thinking" not in result
        assert result == "chunk1chunk2"

    def test_empty_response_content_falls_back(self) -> None:
        """Empty response_content should fallback to content.parts."""
        from gepa_adk.utils.events import extract_final_output

        event = MockEvent(
            is_final=True,
            actions=MockActions(response_content=[]),
            content=MockContent(parts=[MockPart(text="Fallback")]),
        )

        result = extract_final_output([event])
        assert result == "Fallback"


# =============================================================================
# Tests for partition_events_by_agent function
# =============================================================================


class MockAgentEvent:
    """Mock ADK Event object with author field for testing partition_events_by_agent."""

    def __init__(self, author: str | None = None) -> None:
        """Initialize mock event with author."""
        if author is not None:
            self.author = author


class TestPartitionEventsByAgent:
    """Unit tests for partition_events_by_agent function.

    Verifies event partitioning by agent author field for multi-agent
    trajectory extraction from SequentialAgent/ParallelAgent events.
    """

    def test_partition_single_agent_events(self) -> None:
        """Events from single agent are grouped together."""
        events = [
            MockAgentEvent(author="generator"),
            MockAgentEvent(author="generator"),
            MockAgentEvent(author="generator"),
        ]

        result = partition_events_by_agent(events)

        assert len(result) == 1
        assert "generator" in result
        assert len(result["generator"]) == 3

    def test_partition_multiple_agents(self) -> None:
        """Events are partitioned into separate lists per agent."""
        events = [
            MockAgentEvent(author="generator"),
            MockAgentEvent(author="critic"),
            MockAgentEvent(author="generator"),
            MockAgentEvent(author="refiner"),
            MockAgentEvent(author="critic"),
        ]

        result = partition_events_by_agent(events)

        assert len(result) == 3
        assert "generator" in result
        assert "critic" in result
        assert "refiner" in result
        assert len(result["generator"]) == 2
        assert len(result["critic"]) == 2
        assert len(result["refiner"]) == 1

    def test_partition_empty_events_returns_empty_dict(self) -> None:
        """Empty events list returns empty dictionary."""
        result = partition_events_by_agent([])

        assert result == {}

    def test_partition_excludes_user_events(self) -> None:
        """Events with author='user' are excluded from partitions."""
        events = [
            MockAgentEvent(author="user"),
            MockAgentEvent(author="generator"),
            MockAgentEvent(author="user"),
            MockAgentEvent(author="critic"),
        ]

        result = partition_events_by_agent(events)

        assert "user" not in result
        assert len(result) == 2
        assert len(result["generator"]) == 1
        assert len(result["critic"]) == 1

    def test_partition_excludes_events_without_author_attribute(self) -> None:
        """Events missing author attribute are excluded."""
        # Create event without author attribute
        event_no_author = object()  # Basic object has no author attr
        event_with_author = MockAgentEvent(author="generator")

        events = [event_no_author, event_with_author]

        result = partition_events_by_agent(events)

        assert len(result) == 1
        assert "generator" in result
        assert len(result["generator"]) == 1

    def test_partition_excludes_events_with_none_author(self) -> None:
        """Events with author=None are excluded."""

        # MockAgentEvent with no author set (has attr but value is None)
        class EventWithNoneAuthor:
            author = None

        events = [
            EventWithNoneAuthor(),
            MockAgentEvent(author="generator"),
        ]

        result = partition_events_by_agent(events)

        assert len(result) == 1
        assert "generator" in result

    def test_partition_preserves_event_order_within_agent(self) -> None:
        """Events maintain chronological order within each agent's partition."""
        event1 = MockAgentEvent(author="generator")
        event2 = MockAgentEvent(author="generator")
        event3 = MockAgentEvent(author="generator")

        events = [event1, event2, event3]

        result = partition_events_by_agent(events)

        # Verify order is preserved (same object references)
        assert result["generator"][0] is event1
        assert result["generator"][1] is event2
        assert result["generator"][2] is event3

    def test_partition_all_user_events_returns_empty_dict(self) -> None:
        """Partitioning only user events returns empty dictionary."""
        events = [
            MockAgentEvent(author="user"),
            MockAgentEvent(author="user"),
        ]

        result = partition_events_by_agent(events)

        assert result == {}

    def test_partition_sequential_agent_interleaved_events(self) -> None:
        """Simulates SequentialAgent event stream with interleaved agents."""
        # Simulate: generator -> critic -> refiner execution
        events = [
            MockAgentEvent(author="user"),  # Input
            MockAgentEvent(author="generator"),  # Generator processing
            MockAgentEvent(author="generator"),  # Generator output
            MockAgentEvent(author="critic"),  # Critic processing
            MockAgentEvent(author="critic"),  # Critic feedback
            MockAgentEvent(author="refiner"),  # Refiner processing
            MockAgentEvent(author="refiner"),  # Refiner output
        ]

        result = partition_events_by_agent(events)

        assert len(result) == 3
        assert len(result["generator"]) == 2
        assert len(result["critic"]) == 2
        assert len(result["refiner"]) == 2

    def test_partition_empty_string_author_excluded(self) -> None:
        """Events with empty string author are excluded."""

        class EventWithEmptyAuthor:
            author = ""

        events = [
            EventWithEmptyAuthor(),
            MockAgentEvent(author="generator"),
        ]

        result = partition_events_by_agent(events)

        assert "" not in result
        assert len(result) == 1
        assert "generator" in result
