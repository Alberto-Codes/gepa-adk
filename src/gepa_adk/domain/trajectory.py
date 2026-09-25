"""Trajectory and trace types for agent execution tracking.

This module defines data structures for capturing agent execution traces,
including tool calls, state changes, and token usage metrics.

Examples:
    Creating a trajectory from an agent evaluation:

    ```python
    from gepa_adk.domain.trajectory import ADKTrajectory, TokenUsage, ToolCallRecord

    trajectory = ADKTrajectory(
        tool_calls=(ToolCallRecord("search", {"q": "AI"}, ["result"], 0.1),),
        state_deltas=(),
        token_usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        final_output="Search complete.",
        error=None,
    )
    ```

Notes:
    These types are immutable (frozen dataclasses) to ensure trajectory data
    cannot be modified after capture, maintaining audit integrity.
    Each type has ``to_dict()`` and ``from_dict()`` for JSON-safe
    serialisation: tuples become lists and back, and a tool-call argument,
    tool-call result or state-delta value that ``json`` cannot encode is
    stored as its ``str()``.

See Also:
    - [`gepa_adk.ports.adapter.EvaluationBatch`][gepa_adk.ports.adapter.EvaluationBatch]:
        Adapter protocol that produces trajectory data during evaluation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


def _json_safe(value: Any) -> Any:
    """Return a value unchanged when JSON can encode it, else its ``str()``.

    Args:
        value: Any value captured in a trace.

    Returns:
        ``value`` itself when ``json.dumps`` accepts it, otherwise
        ``str(value)``.
    """
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return str(value)
    return value


def _json_safe_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Apply ``_json_safe`` to every value of a dict.

    Args:
        data: Dict whose values may not be JSON-encodable.

    Returns:
        A new dict with the same keys and JSON-safe values.
    """
    return {key: _json_safe(value) for key, value in data.items()}


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """Record of a single tool call during agent execution.

    Captures the invocation details of a tool/function call made by an agent
    during evaluation, including arguments, results, and timing information.
    ``to_dict()`` and ``from_dict()`` convert it to and from a JSON-safe dict.

    Attributes:
        name (str): Tool or function name that was called.
        arguments (dict[str, Any]): Dictionary of arguments passed to the tool.
        result (Any): Return value from the tool execution.
        timestamp (float): Relative time in seconds from evaluation start.

    Examples:
        ```python
        record = ToolCallRecord(
            name="get_weather",
            arguments={"city": "Paris"},
            result={"temp": 22, "condition": "sunny"},
            timestamp=0.123,
        )
        ```
    """

    name: str
    arguments: dict[str, Any]
    result: Any
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        """Serialise this record to a JSON-safe dict.

        Returns:
            Dict with ``name``, ``arguments``, ``result`` and ``timestamp``.
            An argument value or result that JSON cannot encode is stored as
            its ``str()``.
        """
        return {
            "name": self.name,
            "arguments": _json_safe_dict(self.arguments),
            "result": _json_safe(self.result),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCallRecord:
        """Rebuild a record from ``to_dict()`` output.

        Args:
            data: Dict produced by ``to_dict()``.

        Returns:
            The reconstructed record.

        Raises:
            KeyError: If a field is missing from ``data``.
        """
        return cls(
            name=data["name"],
            arguments=dict(data["arguments"]),
            result=data["result"],
            timestamp=data["timestamp"],
        )


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token usage statistics from LLM calls.

    Tracks token consumption for monitoring costs and performance of
    language model interactions during agent execution.
    ``to_dict()`` and ``from_dict()`` convert it to and from a JSON-safe dict.

    Attributes:
        input_tokens (int): Number of tokens in the prompt/context.
        output_tokens (int): Number of tokens generated in the response.
        total_tokens (int): Sum of input_tokens and output_tokens.

    Examples:
        ```python
        usage = TokenUsage(input_tokens=150, output_tokens=50, total_tokens=200)
        ```
    """

    input_tokens: int
    output_tokens: int
    total_tokens: int

    def to_dict(self) -> dict[str, Any]:
        """Serialise these counts to a JSON-safe dict.

        Returns:
            Dict with ``input_tokens``, ``output_tokens`` and
            ``total_tokens``.
        """
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenUsage:
        """Rebuild token counts from ``to_dict()`` output.

        Args:
            data: Dict produced by ``to_dict()``.

        Returns:
            The reconstructed counts.

        Raises:
            KeyError: If a field is missing from ``data``.
        """
        return cls(
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
            total_tokens=data["total_tokens"],
        )


def _usage_from_dict(data: dict[str, Any] | None) -> TokenUsage | None:
    """Rebuild optional token counts.

    Args:
        data: ``TokenUsage.to_dict()`` output, or None.

    Returns:
        The counts, or None when ``data`` is None.
    """
    return None if data is None else TokenUsage.from_dict(data)


@dataclass(frozen=True, slots=True)
class ADKTrajectory:
    """Execution trace from ADK agent evaluation.

    Captures complete execution details from a single agent evaluation run,
    including all tool calls, state changes, token usage, and final output.
    This data enables debugging, optimization, and reflection-based learning.
    ``to_dict()`` and ``from_dict()`` convert it to and from a JSON-safe dict,
    turning tuples into lists and back.

    Attributes:
        tool_calls (tuple[ToolCallRecord, ...]): Immutable sequence of tool
            invocations during execution.
        state_deltas (tuple[dict[str, Any], ...]): Sequence of state changes
            (session state updates).
        token_usage (TokenUsage | None): Optional token consumption metrics
            from LLM calls.
        final_output (str): Final text response from the agent.
        error (str | None): Error message if execution failed, None otherwise.

    Examples:
        ```python
        trajectory = ADKTrajectory(
            tool_calls=(ToolCallRecord("search", {"query": "AI"}, ["result1"], 0.1),),
            state_deltas=({"search_count": 1},),
            token_usage=TokenUsage(100, 50, 150),
            final_output="Based on the search...",
            error=None,
        )
        ```

    Notes:
        All fields use immutable types (tuples, not lists) to prevent
        accidental modification of captured trace data.
    """

    tool_calls: tuple[ToolCallRecord, ...]
    state_deltas: tuple[dict[str, Any], ...]
    token_usage: TokenUsage | None
    final_output: str
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialise this trace to a JSON-safe dict.

        Returns:
            Dict with ``tool_calls`` and ``state_deltas`` as lists,
            ``token_usage`` as a dict or None, ``final_output`` and
            ``error``. A state-delta value that JSON cannot encode is stored
            as its ``str()``.
        """
        return {
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "state_deltas": [_json_safe_dict(delta) for delta in self.state_deltas],
            "token_usage": (
                None if self.token_usage is None else self.token_usage.to_dict()
            ),
            "final_output": self.final_output,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ADKTrajectory:
        """Rebuild a trace from ``to_dict()`` output.

        Args:
            data: Dict produced by ``to_dict()``.

        Returns:
            The reconstructed trace, with lists turned back into tuples.

        Raises:
            KeyError: If a field is missing from ``data``.
        """
        return cls(
            tool_calls=tuple(ToolCallRecord.from_dict(c) for c in data["tool_calls"]),
            state_deltas=tuple(dict(delta) for delta in data["state_deltas"]),
            token_usage=_usage_from_dict(data["token_usage"]),
            final_output=data["final_output"],
            error=data["error"],
        )


@dataclass(frozen=True, slots=True)
class MultiAgentTrajectory:
    """Execution trace from multi-agent pipeline evaluation.

    Captures individual agent trajectories and overall pipeline metrics.
    ``to_dict()`` and ``from_dict()`` convert it to and from a JSON-safe dict,
    nesting each agent's ``ADKTrajectory`` dict.

    Attributes:
        agent_trajectories (dict[str, ADKTrajectory]): Mapping of agent name to trajectory.
        pipeline_output (str): Final output from the primary agent.
        total_token_usage (TokenUsage | None): Aggregated token usage across all agents.
        error (str | None): Error message if pipeline execution failed.

    Examples:
        Creating a multi-agent trajectory:

        ```python
        from gepa_adk.domain.trajectory import (
            MultiAgentTrajectory,
            ADKTrajectory,
            TokenUsage,
        )

        trajectory = MultiAgentTrajectory(
            agent_trajectories={
                "generator": ADKTrajectory(...),
                "critic": ADKTrajectory(...),
            },
            pipeline_output="Generated code output",
            total_token_usage=TokenUsage(200, 100, 300),
            error=None,
        )
        ```

    Notes:
        All fields use immutable types to prevent accidental modification
        of captured trace data. agent_trajectories maps agent names to
        their individual ADKTrajectory records.
    """

    agent_trajectories: dict[str, ADKTrajectory]
    pipeline_output: str
    total_token_usage: TokenUsage | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise this pipeline trace to a JSON-safe dict.

        Returns:
            Dict with ``agent_trajectories`` (agent name to
            ``ADKTrajectory.to_dict()``), ``pipeline_output``,
            ``total_token_usage`` as a dict or None, and ``error``.
        """
        return {
            "agent_trajectories": {
                name: trajectory.to_dict()
                for name, trajectory in self.agent_trajectories.items()
            },
            "pipeline_output": self.pipeline_output,
            "total_token_usage": (
                None
                if self.total_token_usage is None
                else self.total_token_usage.to_dict()
            ),
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MultiAgentTrajectory:
        """Rebuild a pipeline trace from ``to_dict()`` output.

        Args:
            data: Dict produced by ``to_dict()``. ``error`` may be absent.

        Returns:
            The reconstructed pipeline trace.

        Raises:
            KeyError: If a required field is missing from ``data``.
        """
        return cls(
            agent_trajectories={
                name: ADKTrajectory.from_dict(trajectory)
                for name, trajectory in data["agent_trajectories"].items()
            },
            pipeline_output=data["pipeline_output"],
            total_token_usage=_usage_from_dict(data["total_token_usage"]),
            error=data.get("error"),
        )
