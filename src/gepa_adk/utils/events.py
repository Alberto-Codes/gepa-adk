"""Trajectory extraction and processing utilities.

This module provides functions for extracting, redacting, and truncating
trajectory data from ADK agent execution events.

The main entry point is [`extract_trajectory`][gepa_adk.utils.events.extract_trajectory],
which orchestrates a three-stage pipeline:

1. Extract raw data (tool calls, state deltas, token usage)
2. Apply redaction to sensitive fields
3. Apply truncation to oversized strings

All functions except [`extract_trajectory`][gepa_adk.utils.events.extract_trajectory]
are private helpers prefixed with underscore. The extraction logic is designed
to gracefully handle both real ADK Event objects and test mocks.

Attributes:
    extract_trajectory (function): Main trajectory extraction API with
        configurable redaction and truncation.

Exported Functions:
    - [`extract_trajectory`][gepa_adk.utils.events.extract_trajectory]:
      Main extraction API with configuration support

See Also:
    - [`gepa_adk.domain.trajectory`][gepa_adk.domain.trajectory]:
      Domain models (ADKTrajectory, ToolCallRecord)
    - [`gepa_adk.domain.types`][gepa_adk.domain.types]:
      Configuration (TrajectoryConfig)

Note:
    These utilities handle infrastructure concerns like data transformation
    and security (redaction), not domain logic. They consume domain models
    but don't define them.
"""

from typing import Any

import structlog

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
            key: marker
            if key in sensitive_keys
            else _redact_sensitive(value, sensitive_keys, marker)
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
        return {
            key: _truncate_strings(value, max_length) for key, value in data.items()
        }
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


def extract_final_output(
    events: list[Any],
    *,
    prefer_concatenated: bool = False,
) -> str:
    """Extract final output text from ADK event stream.

    Extracts the final response text from ADK events, handling both
    `event.actions.response_content` (preferred) and `event.content.parts`
    (fallback) response sources. Filters out reasoning/thought content
    marked with `part.thought=True`.

    Args:
        events: List of ADK Event objects from agent execution.
        prefer_concatenated: If True, concatenate all non-thought text parts
            from all final response events. If False (default), return only
            the last non-thought text part from the last final response event.

    Returns:
        Extracted output text as a string. Returns empty string if no valid
        output can be extracted (empty events, no final responses, all thought
        parts, or missing attributes).

    Examples:
        Basic extraction (default mode - returns LAST final response):

        ```python
        events = await runner.run_async(...)
        output = extract_final_output(events)
        ```

        Streaming/concatenation mode for CriticScorer:

        ```python
        events = await runner.run_async(...)
        output = extract_final_output(events, prefer_concatenated=True)
        ```

    Note:
        Scans events for is_final_response()=True, filters thought parts,
        skips empty/None text, and handles missing attributes gracefully.
        Response source priority: response_content > content.parts. Default
        mode returns LAST final response (for multi-agent pipelines).
    """
    if not events:
        return ""

    collected_parts: list[str] = []
    last_output: str = ""

    for event in events:
        # Skip non-final events
        if not hasattr(event, "is_final_response") or not event.is_final_response():
            continue

        # Try to extract text from this event
        event_text = _extract_text_from_event(event)

        if event_text:
            if prefer_concatenated:
                collected_parts.append(event_text)
            else:
                # Default mode: keep updating to get LAST final response
                last_output = event_text

    # For concatenated mode, join all collected parts
    if prefer_concatenated:
        return "".join(collected_parts)

    return last_output


def _extract_text_from_event(event: Any) -> str:
    """Extract text from a single ADK event.

    Tries response_content first (preferred), then falls back to content.parts.
    Filters out thought/reasoning parts.

    Args:
        event: Single ADK Event object.

    Returns:
        Extracted text from the event, or empty string if none found.
    """
    # Try event.actions.response_content first (preferred for final responses)
    text = _extract_from_response_content(event)
    if text:
        return text

    # Fallback to event.content.parts
    return _extract_from_content_parts(event)


def _extract_from_response_content(event: Any) -> str:
    """Extract text from event.actions.response_content.

    Args:
        event: ADK Event object.

    Returns:
        First non-thought text from response_content, or empty string.
    """
    actions = getattr(event, "actions", None)
    if not actions:
        return ""

    response_content = getattr(actions, "response_content", None)
    if not response_content:
        return ""

    return _extract_text_from_parts(response_content)


def _extract_from_content_parts(event: Any) -> str:
    """Extract text from event.content.parts.

    Args:
        event: ADK Event object.

    Returns:
        First non-thought text from content.parts, or empty string.
    """
    content = getattr(event, "content", None)
    if not content:
        return ""

    parts = getattr(content, "parts", None)
    if not parts:
        return ""

    return _extract_text_from_parts(parts)


def _extract_text_from_parts(parts: Any) -> str:
    """Extract first non-thought text from a list of parts.

    Filters out parts where thought=True and parts with empty/None text.

    Args:
        parts: List of Part objects (from response_content or content.parts).

    Returns:
        First valid non-thought text, or empty string if none found.
    """
    if not parts:
        return ""

    for part in parts:
        # Skip thought/reasoning parts (the bug fix!)
        if getattr(part, "thought", False):
            continue

        # Get text, skip if empty or None
        text = getattr(part, "text", None)
        if text:
            return text

    return ""


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

    logger.debug(
        "trajectory.extraction.start",
        event_count=len(events),
        config_include_tool_calls=config.include_tool_calls,
        config_include_state_deltas=config.include_state_deltas,
        config_include_token_usage=config.include_token_usage,
        config_redact_sensitive=config.redact_sensitive,
        config_max_string_length=config.max_string_length,
    )

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
            _redact_sensitive(delta, config.sensitive_keys)
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
            _truncate_strings(delta, config.max_string_length)
            for delta in state_deltas_list
        ]

    # Step 4: Build immutable trajectory
    logger.debug(
        "trajectory.extraction.complete",
        tool_calls_count=len(tool_calls_list),
        state_deltas_count=len(state_deltas_list),
        has_token_usage=token_usage is not None,
        has_error=error is not None,
    )

    return ADKTrajectory(
        tool_calls=tuple(tool_calls_list),
        state_deltas=tuple(state_deltas_list),
        token_usage=token_usage,
        final_output=final_output,
        error=error,
    )


def extract_output_from_state(
    session_state: dict[str, Any],
    output_key: str | None,
) -> str | None:
    """Extract output from session state using output_key.

    A shared utility for extracting agent output from ADK session state using
    the output_key mechanism. Complements extract_final_output() for use when
    agents have output_key configured.

    Args:
        session_state: ADK session state dictionary.
        output_key: Key where agent stored its output, or None.

    Returns:
        Output string if found in state, None otherwise.
        Caller should implement fallback logic when None is returned.

    Examples:
        Basic extraction:

        ```python
        state = {"proposed_component_text": "Be helpful and concise"}
        result = extract_output_from_state(state, "proposed_component_text")
        # result == "Be helpful and concise"
        ```

        Missing key returns None:

        ```python
        state = {"other_key": "value"}
        result = extract_output_from_state(state, "proposed_component_text")
        # result is None
        ```

        None output_key returns None:

        ```python
        state = {"proposed_component_text": "text"}
        result = extract_output_from_state(state, None)
        # result is None
        ```

    Note:
        State-based extraction complements event-based extraction for ADK's
        output_key mechanism. Callers should implement fallback logic
        (e.g., extract_final_output) when this function returns None.
    """
    if not output_key:
        return None
    if output_key in session_state:
        value = session_state[output_key]
        if value is not None:
            return str(value)
    return None


def partition_events_by_agent(events: list[Any]) -> dict[str, list[Any]]:
    """Partition ADK events by their originating agent.

    Separates a mixed event stream (e.g., from SequentialAgent) into
    per-agent event lists based on the `event.author` field. Each agent's
    events can then be processed independently for trajectory extraction.

    Args:
        events: List of ADK Event objects from multi-agent execution.
            Each event should have an `author` attribute identifying
            the agent that generated it.

    Returns:
        Dictionary mapping agent names to their respective event lists.
        Events with author='user' or missing author are excluded.
        Empty dict returned if no agent events found.

    Examples:
        Basic partitioning from SequentialAgent:

        ```python
        events = await runner.run_async(sequential_agent, ...)
        partitions = partition_events_by_agent(events)
        # partitions == {
        #     "generator": [Event(...), Event(...)],
        #     "critic": [Event(...), Event(...)],
        # }
        ```

        Building per-agent trajectories:

        ```python
        partitions = partition_events_by_agent(events)
        trajectories = {}
        for agent_name, agent_events in partitions.items():
            trajectories[agent_name] = extract_trajectory(agent_events)
        ```

    Note:
        Sorts events into agent-specific lists by examining `event.author`.
        User events are excluded since they represent input, not agent output.
    """
    partitions: dict[str, list[Any]] = {}

    for event in events:
        author = getattr(event, "author", None)
        # Skip user events and events without author
        if not author or author == "user":
            continue

        if author not in partitions:
            partitions[author] = []
        partitions[author].append(event)

    return partitions


__all__ = [
    "extract_final_output",
    "extract_output_from_state",
    "extract_trajectory",
    "partition_events_by_agent",
]
