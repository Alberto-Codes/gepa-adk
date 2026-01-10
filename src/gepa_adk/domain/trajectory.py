"""Trajectory and trace types for agent execution tracking.

This module defines data structures for capturing agent execution traces,
including tool calls, state changes, and token usage metrics.

Note:
    These types are immutable (frozen dataclasses) to ensure trajectory data
    cannot be modified after capture, maintaining audit integrity.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """Record of a single tool call during agent execution.

    Captures the invocation details of a tool/function call made by an agent
    during evaluation, including arguments, results, and timing information.

    Attributes:
        name: Tool or function name that was called.
        arguments: Dictionary of arguments passed to the tool.
        result: Return value from the tool execution.
        timestamp: Relative time in seconds from evaluation start.

    Example:
        >>> record = ToolCallRecord(
        ...     name="get_weather",
        ...     arguments={"city": "Paris"},
        ...     result={"temp": 22, "condition": "sunny"},
        ...     timestamp=0.123,
        ... )
    """

    name: str
    arguments: dict[str, Any]
    result: Any
    timestamp: float


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token usage statistics from LLM calls.

    Tracks token consumption for monitoring costs and performance of
    language model interactions during agent execution.

    Attributes:
        input_tokens: Number of tokens in the prompt/context.
        output_tokens: Number of tokens generated in the response.
        total_tokens: Sum of input_tokens and output_tokens.

    Example:
        >>> usage = TokenUsage(input_tokens=150, output_tokens=50, total_tokens=200)
    """

    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class ADKTrajectory:
    """Execution trace from ADK agent evaluation.

    Captures complete execution details from a single agent evaluation run,
    including all tool calls, state changes, token usage, and final output.
    This data enables debugging, optimization, and reflection-based learning.

    Attributes:
        tool_calls: Immutable sequence of tool invocations during execution.
        state_deltas: Sequence of state changes (session state updates).
        token_usage: Optional token consumption metrics from LLM calls.
        final_output: Final text response from the agent.
        error: Error message if execution failed, None otherwise.

    Example:
        >>> trajectory = ADKTrajectory(
        ...     tool_calls=(
        ...         ToolCallRecord("search", {"query": "AI"}, ["result1"], 0.1),
        ...     ),
        ...     state_deltas=({"search_count": 1},),
        ...     token_usage=TokenUsage(100, 50, 150),
        ...     final_output="Based on the search...",
        ...     error=None,
        ... )

    Note:
        All fields use immutable types (tuples, not lists) to prevent
        accidental modification of captured trace data.
    """

    tool_calls: tuple[ToolCallRecord, ...]
    state_deltas: tuple[dict[str, Any], ...]
    token_usage: TokenUsage | None
    final_output: str
    error: str | None
