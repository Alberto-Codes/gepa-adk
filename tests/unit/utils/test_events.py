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
