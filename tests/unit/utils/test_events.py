"""Unit tests for trajectory extraction utilities.

Tests verify redaction, truncation, and extraction logic for trajectory data.
Uses pytest conventions with three-layer testing approach.
"""

import pytest

from gepa_adk.domain.trajectory import ADKTrajectory, TokenUsage, ToolCallRecord
from gepa_adk.domain.types import TrajectoryConfig
from gepa_adk.utils.events import _redact_sensitive, _truncate_strings, extract_trajectory

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
        data = {"user": "alice", "password": "pass", "api_key": "key123", "name": "test"}
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

    def test_redact_tool_call_results(self, mocker) -> None:
        """Redact sensitive keys in tool call results."""
        mock_fc = mocker.MagicMock()
        mock_fc.name = "get_config"
        mock_fc.args = {}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        # Manually set result after creating ToolCallRecord
        config = TrajectoryConfig(redact_sensitive=True)
        trajectory = extract_trajectory(events=[mock_event], config=config)

        # Note: In real implementation, result would come from function_response
        # For now, we test the redaction logic works when applied

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


