"""Trajectory extraction and processing utilities.

This module provides functions for extracting, redacting, and truncating
trajectory data from ADK agent execution events.

Note:
    These utilities handle infrastructure concerns like data transformation
    and security (redaction), not domain logic. They consume domain models
    but don't define them.
"""

from typing import Any

from gepa_adk.domain.trajectory import ADKTrajectory, TokenUsage, ToolCallRecord
from gepa_adk.domain.types import TrajectoryConfig


def _redact_sensitive(
    data: Any,
    sensitive_keys: tuple[str, ...],
    marker: str = "[REDACTED]",
) -> Any:
    """Recursively redact sensitive fields from nested data structures.

    Traverses dictionaries and sequences to replace values of sensitive keys
    with a redaction marker. Returns a new data structure without modifying
    the input.

    Args:
        data: Data structure to redact (dict, list, tuple, or primitive).
        sensitive_keys: Tuple of exact key names to redact (case-sensitive).
        marker: Replacement value for sensitive fields. Defaults to "[REDACTED]".

    Returns:
        New data structure with sensitive values replaced. Type matches input:
        - dict → dict (with redacted values)
        - list → list (with redacted elements)
        - tuple → tuple (with redacted elements)
        - primitives → unchanged

    Examples:
        Basic dictionary redaction:

        ```python
        data = {"user": "alice", "password": "secret123"}
        result = _redact_sensitive(data, ("password",))
        # result == {"user": "alice", "password": "[REDACTED]"}
        ```

        Nested structure with lists:

        ```python
        data = {
            "configs": [
                {"name": "prod", "api_key": "abc123"},
                {"name": "dev", "api_key": "xyz789"},
            ]
        }
        result = _redact_sensitive(data, ("api_key",))
        # result["configs"][0]["api_key"] == "[REDACTED]"
        ```

        Multiple sensitive keys:

        ```python
        data = {"password": "pass", "token": "tok", "name": "user"}
        result = _redact_sensitive(data, ("password", "token"))
        # result == {"password": "[REDACTED]", "token": "[REDACTED]", "name": "user"}
        ```

    Note:
        Only exact key matches are redacted (case-sensitive). For example,
        "password" will not match "Password" or "user_password".
        Original data structure is never modified.
    """
    if isinstance(data, dict):
        return {
            key: marker if key in sensitive_keys else _redact_sensitive(value, sensitive_keys, marker)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [_redact_sensitive(item, sensitive_keys, marker) for item in data]
    elif isinstance(data, tuple):
        return tuple(_redact_sensitive(item, sensitive_keys, marker) for item in data)
    else:
        return data


def _truncate_strings(
    data: Any,
    max_length: int,
) -> Any:
    """Recursively truncate long strings in nested data structures.

    Traverses dictionaries and sequences to truncate strings exceeding the
    maximum length. Adds a marker indicating how many characters were removed.
    Returns a new data structure without modifying the input.

    Args:
        data: Data structure to truncate (dict, list, tuple, or primitive).
        max_length: Maximum string length before truncation. Must be positive.

    Returns:
        New data structure with strings truncated. Type matches input:
        - dict → dict (with truncated string values)
        - list → list (with truncated string elements)
        - tuple → tuple (with truncated string elements)
        - str → truncated string if len > max_length
        - other primitives → unchanged

    Examples:
        Basic string truncation:

        ```python
        data = "a" * 100
        result = _truncate_strings(data, max_length=50)
        # result == "a" * 50 + "...[truncated 50 chars]"
        ```

        Dictionary with mixed content:

        ```python
        data = {
            "short": "hello",
            "long": "x" * 1000,
            "number": 42,
        }
        result = _truncate_strings(data, max_length=100)
        # result["short"] == "hello"
        # result["long"] == "x" * 100 + "...[truncated 900 chars]"
        # result["number"] == 42
        ```

        Nested structures:

        ```python
        data = {
            "results": [
                {"content": "a" * 200},
                {"content": "b" * 50},
            ]
        }
        result = _truncate_strings(data, max_length=100)
        # result["results"][0]["content"] ends with "...[truncated 100 chars]"
        # result["results"][1]["content"] == "b" * 50
        ```

    Note:
        Only strings are truncated. Numbers, booleans, None, and other types
        pass through unchanged. Original data is never modified.
        Marker format is "...[truncated N chars]" where N is chars removed.
    """
    if isinstance(data, dict):
        return {key: _truncate_strings(value, max_length) for key, value in data.items()}
    elif isinstance(data, list):
        return [_truncate_strings(item, max_length) for item in data]
    elif isinstance(data, tuple):
        return tuple(_truncate_strings(item, max_length) for item in data)
    elif isinstance(data, str) and len(data) > max_length:
        truncated_count = len(data) - max_length
        return f"{data[:max_length]}...[truncated {truncated_count} chars]"
    else:
        return data


def extract_trajectory(
    events: list[Any],
    final_output: str = "",
    error: str | None = None,
    config: TrajectoryConfig | None = None,
) -> ADKTrajectory:
    """Extract trajectory from ADK execution events with optional processing.

    Extracts tool calls, state deltas, and token usage from ADK event stream,
    applying redaction and truncation based on configuration.

    Args:
        events: List of ADK Event objects from agent execution.
        final_output: Final text response from the agent. Defaults to empty string.
        error: Error message if execution failed. Defaults to None.
        config: Extraction configuration. If None, uses TrajectoryConfig defaults.

    Returns:
        ADKTrajectory with extracted and processed data according to config.

    Examples:
        Basic extraction with defaults:

        ```python
        from google.adk.events import Event

        events = [...]  # From ADK runner
        trajectory = extract_trajectory(events, final_output="Response")
        ```

        Custom configuration:

        ```python
        config = TrajectoryConfig(
            include_tool_calls=True,
            include_state_deltas=False,
            redact_sensitive=True,
            max_string_length=5000,
        )
        trajectory = extract_trajectory(events, config=config)
        ```

        With error:

        ```python
        trajectory = extract_trajectory(
            events=[],
            final_output="",
            error="Agent timeout after 30s",
        )
        ```

    Note:
        Extraction follows this order:
        1. Extract raw data from events (tool calls, state, tokens)
        2. Apply redaction if config.redact_sensitive is True
        3. Apply truncation if config.max_string_length is not None
        4. Build immutable ADKTrajectory

        Empty events list is valid and returns empty trajectory.
    """
    if config is None:
        config = TrajectoryConfig()

    # Stub implementation - returns empty trajectory
    # Will be implemented in subsequent phases
    return ADKTrajectory(
        tool_calls=(),
        state_deltas=(),
        token_usage=None,
        final_output=final_output,
        error=error,
    )


__all__ = ["extract_trajectory"]
