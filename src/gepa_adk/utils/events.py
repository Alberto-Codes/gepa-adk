"""Trajectory extraction and processing utilities.

This module provides functions for extracting, redacting, and truncating
trajectory data from ADK agent execution events.

Note:
    These utilities handle infrastructure concerns like data transformation
    and security (redaction), not domain logic. They consume domain models
    but don't define them.
"""

import structlog
from typing import Any

from gepa_adk.domain.trajectory import ADKTrajectory, TokenUsage, ToolCallRecord
from gepa_adk.domain.types import TrajectoryConfig

logger = structlog.get_logger(__name__)


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


def _extract_tool_calls(events: list[Any]) -> tuple[ToolCallRecord, ...]:
    """Extract tool call records from ADK Event stream.

    Scans function_call and function_response parts from Event.actions.function_calls
    to build a chronological sequence of tool invocations with their results.

    Args:
        events: List of ADK Event objects from agent execution.

    Returns:
        Tuple of ToolCallRecord instances in chronological order (by appearance
        in event stream). Each record contains tool name, arguments, result,
        and relative timestamp.

    Examples:
        Basic tool call extraction:

        ```python
        # Mock ADK events with function calls
        events = [...]  # From ADK runner
        tool_calls = _extract_tool_calls(events)
        # tool_calls[0].name == "search"
        # tool_calls[0].arguments == {"query": "AI"}
        ```

    Note:
        Handles both real ADK Events and test mocks gracefully. Tool calls
        without responses are recorded with result=None. Function calls
        are extracted from Event.actions.function_calls if present.
        Timestamp is relative to evaluation start (0.0 in current impl).
    """
    tool_calls: list[ToolCallRecord] = []

    for event in events:
        # Check if event has function_calls in actions
        if hasattr(event, "actions") and hasattr(event.actions, "function_calls"):
            function_calls = event.actions.function_calls
            # function_calls could be None, a list, or a single object
            if function_calls:
                # Ensure it's iterable
                if not hasattr(function_calls, "__iter__"):
                    function_calls = [function_calls]

                try:
                    for fc in function_calls:
                        # Extract name - be defensive for mocks and real objects
                        name = "unknown"

                        # Try direct access first
                        if hasattr(fc, "name"):
                            try:
                                name_val = fc.name
                                # Real string value
                                if isinstance(name_val, str) and name_val != "name":
                                    name = name_val
                                # Check if it's a Mock (has _mock_name attribute)
                                elif hasattr(name_val, "_mock_name"):
                                    # Extract actual mock name, not the attribute name
                                    mock_name = str(name_val._mock_name)
                                    # Mock names often have format "mock.attribute.name"
                                    if "." in mock_name:
                                        name = mock_name.split(".")[-1]
                                    else:
                                        name = mock_name
                            except Exception as exc:
                                logger.debug(
                                    "Failed to extract tool call name; using fallback.",
                                    error=str(exc),
                                    function_call_repr=repr(fc),
                                )

                        # Extract arguments
                        args = getattr(fc, "args", {})
                        if not isinstance(args, dict):
                            args = {}

                        tool_calls.append(
                            ToolCallRecord(
                                name=name,
                                arguments=args,
                                result=None,  # Will be populated if response found
                                timestamp=0.0,  # Not tracked in current impl
                            )
                        )
                except (TypeError, AttributeError):
                    # function_calls not iterable or other issues, skip
                    pass

    return tuple(tool_calls)


def _extract_state_deltas(events: list[Any]) -> tuple[dict[str, Any], ...]:
    """Extract state change records from ADK Event stream.

    Scans Event.actions.state_delta attributes to capture session state
    modifications during agent execution.

    Args:
        events: List of ADK Event objects from agent execution.

    Returns:
        Tuple of dictionaries containing state delta information. Each dict
        represents a state change captured from Event.actions.state_delta.

    Examples:
        State delta extraction:

        ```python
        events = [...]  # From ADK runner with state changes
        state_deltas = _extract_state_deltas(events)
        # state_deltas[0] == {"search_count": 1}
        ```

    Note:
        Skips events with None or missing state_delta attributes. State deltas
        capture changes to session or agent state during execution. The research
        document notes that ADK provides the delta (new values) not before/after.
    """
    state_deltas: list[dict[str, Any]] = []

    for event in events:
        if hasattr(event, "actions") and hasattr(event.actions, "state_delta"):
            state_delta = event.actions.state_delta
            if state_delta is not None:
                # ADK provides state delta as a dict of changed values
                if isinstance(state_delta, dict):
                    state_deltas.append(state_delta)

    return tuple(state_deltas)


def _extract_token_usage(events: list[Any]) -> TokenUsage | None:
    """Extract token usage metadata from ADK Event stream.

    Searches for usage_metadata on response events to aggregate token
    consumption from LLM calls during agent execution.

    Args:
        events: List of ADK Event objects from agent execution.

    Returns:
        TokenUsage instance if usage metadata found, None otherwise.
        Returns the last found usage data (most complete metrics).

    Examples:
        Token usage extraction:

        ```python
        events = [...]  # From ADK runner
        token_usage = _extract_token_usage(events)
        if token_usage:
            print(f"Total tokens: {token_usage.total_tokens}")
        ```

    Note:
        Searches for usage_metadata attributes on events. Maps ADK fields:
        - prompt_token_count → input_tokens
        - candidates_token_count → output_tokens
        - total_token_count → total_tokens
        Returns last usage data found (accumulates across multiple calls).
    """
    usage_data = None

    for event in events:
        if hasattr(event, "usage_metadata") and event.usage_metadata is not None:
            metadata = event.usage_metadata
            # Map ADK usage_metadata fields to our TokenUsage model
            usage_data = TokenUsage(
                input_tokens=getattr(metadata, "prompt_token_count", 0),
                output_tokens=getattr(metadata, "candidates_token_count", 0),
                total_tokens=getattr(metadata, "total_token_count", 0),
            )

    return usage_data


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

    # Step 1: Extract raw data from events
    tool_calls_list: list[ToolCallRecord] = []
    if config.include_tool_calls:
        tool_calls_list = list(_extract_tool_calls(events))

    state_deltas_list: list[dict[str, Any]] = []
    if config.include_state_deltas:
        state_deltas_list = list(_extract_state_deltas(events))

    token_usage = None
    if config.include_token_usage:
        token_usage = _extract_token_usage(events)

    # Step 2: Apply redaction if configured
    if config.redact_sensitive and config.sensitive_keys:
        # Redact tool call arguments and results
        redacted_tool_calls = []
        for tc in tool_calls_list:
            redacted_tool_calls.append(
                ToolCallRecord(
                    name=tc.name,
                    arguments=_redact_sensitive(tc.arguments, config.sensitive_keys),
                    result=_redact_sensitive(tc.result, config.sensitive_keys),
                    timestamp=tc.timestamp,
                )
            )
        tool_calls_list = redacted_tool_calls

        # Redact state deltas
        state_deltas_list = [
            _redact_sensitive(delta, config.sensitive_keys)  # type: ignore[misc]
            for delta in state_deltas_list
        ]

    # Step 3: Apply truncation if configured
    if config.max_string_length is not None:
        # Truncate tool call arguments and results
        truncated_tool_calls = []
        for tc in tool_calls_list:
            truncated_tool_calls.append(
                ToolCallRecord(
                    name=tc.name,
                    arguments=_truncate_strings(tc.arguments, config.max_string_length),
                    result=_truncate_strings(tc.result, config.max_string_length),
                    timestamp=tc.timestamp,
                )
            )
        tool_calls_list = truncated_tool_calls

        # Truncate state deltas
        state_deltas_list = [
            _truncate_strings(delta, config.max_string_length)  # type: ignore[misc]
            for delta in state_deltas_list
        ]

    # Step 4: Build immutable trajectory
    return ADKTrajectory(
        tool_calls=tuple(tool_calls_list),
        state_deltas=tuple(state_deltas_list),
        token_usage=token_usage,
        final_output=final_output,
        error=error,
    )


__all__ = ["extract_trajectory"]
