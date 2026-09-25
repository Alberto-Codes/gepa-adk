"""Acceptance tests for the run counters the public entry points return.

The engine's ``EvolutionResult`` carries ``baseline_failed_evaluations``,
``total_failed_evaluations``, ``stop_reason`` and ``token_usage``. Each entry
point must return those values unchanged, so a caller that reads the
top-level counter sees what the iteration records show (GitHub issue 444).

Notes:
    A fake executor answers every agent call with a fixed token usage and a
    scorer raises on one row of one iteration, so the expected counters are
    known without an LLM. The expected values are computed from the records
    the run produced, never from the fake's own bookkeeping.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from google.adk.agents import LlmAgent, SequentialAgent

from gepa_adk import evolve, evolve_group, evolve_workflow
from gepa_adk.domain.models import (
    EvolutionConfig,
    EvolutionResult,
    MultiAgentEvolutionResult,
    StopReason,
    TokenRollup,
)
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.unit

_INPUT_TOKENS = 10
_OUTPUT_TOKENS = 5
_TOTAL_TOKENS = 15
_FAILING_ROW = "row-b"


class UsageReportingExecutor:
    """Executor fake that answers every call with one usage-bearing event.

    A reflection call (its session state carries ``component_text``) gets a
    proposal that differs on every call, so no iteration is skipped as a
    duplicate. Any other call gets an answer that names the row.

    Attributes:
        reflection_calls (int): Reflection calls answered so far.
        agent_calls (int): Evaluation calls answered so far.
    """

    def __init__(self) -> None:
        """Start the call counters at zero."""
        self.reflection_calls = 0
        self.agent_calls = 0

    async def execute_agent(
        self, agent: Any, input_text: str, **kwargs: Any
    ) -> ExecutionResult:
        """Return a successful result whose one event reports token usage.

        Args:
            agent: The agent to run; recorded only through the counters.
            input_text: The user message.
            **kwargs: The executor keyword arguments; ``session_state`` tells
                a reflection call apart from an evaluation call.

        Returns:
            A success result with an event carrying ``usage_metadata``.
        """
        state = kwargs.get("session_state") or {}
        if "component_text" in state:
            self.reflection_calls += 1
            text = f"Proposal {self.reflection_calls}: answer the question well."
        else:
            self.agent_calls += 1
            text = f"answer for {input_text}"
        event = SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=_INPUT_TOKENS,
                candidates_token_count=_OUTPUT_TOKENS,
                total_token_count=_TOTAL_TOKENS,
            )
        )
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id=f"session-{self.agent_calls + self.reflection_calls}",
            extracted_value=text,
            captured_events=[event],
        )


class RaiseOnceScorer:
    """Scorer that raises the second time it sees the failing row.

    The first sighting is the baseline pass, so the raise lands in the
    first iteration's evaluation and nowhere else.

    Attributes:
        failing_row_sightings (int): Times the failing row has been scored.
    """

    def __init__(self) -> None:
        """Start with no sightings of the failing row."""
        self.failing_row_sightings = 0

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Score 1.0, or raise on the second sighting of the failing row.

        Args:
            input_text: The row's input.
            output: The agent's output.
            expected: The row's expected value, unused.

        Returns:
            A perfect score and empty metadata.

        Raises:
            RuntimeError: On the second sighting of the failing row.
        """
        if input_text == _FAILING_ROW:
            self.failing_row_sightings += 1
            if self.failing_row_sightings == 2:
                raise RuntimeError("scorer failed on this row")
        return 1.0, {}

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Delegate to ``score``.

        Args:
            input_text: The row's input.
            output: The agent's output.
            expected: The row's expected value, unused.

        Returns:
            The synchronous score.
        """
        return self.score(input_text, output, expected)


def _trainset() -> list[dict[str, Any]]:
    """Return three rows, one of which the scorer will fail once.

    Returns:
        Three rows with distinct inputs.
    """
    return [
        {"input": "row-a", "expected": "a"},
        {"input": _FAILING_ROW, "expected": "b"},
        {"input": "row-c", "expected": "c"},
    ]


def _config() -> EvolutionConfig:
    """Return a two-iteration config with no patience stop in the way.

    Returns:
        The evolution config.
    """
    return EvolutionConfig(max_iterations=2, patience=10, seed=7)


def _assert_counters_match_records(
    result: EvolutionResult | MultiAgentEvolutionResult, trainset_size: int
) -> None:
    """Assert the top-level counters equal the baseline plus the records.

    Args:
        result: The result an entry point returned.
        trainset_size: Rows in the baseline pass, each of which reported
            usage.
    """
    records = result.iteration_history
    assert len(records) == 2
    assert [r.failed_evaluations for r in records] == [1, 0]
    assert result.baseline_failed_evaluations == 0
    assert result.total_failed_evaluations == 1
    assert result.total_failed_evaluations == (
        result.baseline_failed_evaluations + sum(r.failed_evaluations for r in records)
    )
    assert result.stop_reason == StopReason.MAX_ITERATIONS

    assert isinstance(result.token_usage, TokenRollup)
    for record in records:
        assert isinstance(record.token_usage, TokenRollup)
    record_usage: list[TokenRollup] = [
        r.token_usage for r in records if r.token_usage is not None
    ]
    baseline_usage = TokenRollup(
        input_tokens=_INPUT_TOKENS * trainset_size,
        output_tokens=_OUTPUT_TOKENS * trainset_size,
        total_tokens=_TOTAL_TOKENS * trainset_size,
        rows_counted=trainset_size,
        rows_unknown=0,
    )
    expected = baseline_usage
    for usage in record_usage:
        expected = expected.combine(usage)
    assert result.token_usage == expected
    assert result.token_usage.rows_counted > trainset_size


@pytest.mark.asyncio
async def test_evolve_returns_the_engine_counters_and_rollup() -> None:
    """``evolve()`` returns the failed-evaluation counters, stop reason and rollup."""
    agent = LlmAgent(
        name="answerer",
        model="ollama_chat/gpt-oss:20b",
        instruction="Answer the question.",
    )
    reflector = LlmAgent(
        name="reflector",
        model="ollama_chat/gpt-oss:20b",
        instruction="Improve the component.",
    )
    executor = UsageReportingExecutor()
    trainset = _trainset()

    result = await evolve(
        agent,
        trainset,
        scorer=RaiseOnceScorer(),
        reflection_agent=reflector,
        config=_config(),
        executor=executor,
    )

    assert isinstance(result, EvolutionResult)
    assert executor.reflection_calls == 2
    _assert_counters_match_records(result, len(trainset))
    assert result.original_components == {"instruction": "Answer the question."}
    assert result.valset_score is not None


@pytest.mark.asyncio
async def test_evolve_group_returns_the_engine_counters_and_rollup() -> None:
    """``evolve_group()`` keeps returning the counters, stop reason and rollup."""
    agent = LlmAgent(
        name="answerer",
        model="ollama_chat/gpt-oss:20b",
        instruction="Answer the question.",
    )
    reflector = LlmAgent(
        name="reflector",
        model="ollama_chat/gpt-oss:20b",
        instruction="Improve the component.",
    )
    executor = UsageReportingExecutor()
    trainset = _trainset()

    with patch("gepa_adk.api.AgentExecutor", return_value=executor):
        result = await evolve_group(
            {"answerer": agent},
            "answerer",
            trainset,
            scorer=RaiseOnceScorer(),
            reflection_agent=reflector,
            config=_config(),
        )

    assert isinstance(result, MultiAgentEvolutionResult)
    assert executor.reflection_calls == 2
    _assert_counters_match_records(result, len(trainset))


@pytest.mark.asyncio
async def test_evolve_workflow_returns_the_engine_counters_and_rollup() -> None:
    """``evolve_workflow()`` keeps returning the counters, stop reason and rollup."""
    agent = LlmAgent(
        name="answerer",
        model="ollama_chat/gpt-oss:20b",
        instruction="Answer the question.",
    )
    workflow = SequentialAgent(name="pipeline", sub_agents=[agent])
    executor = UsageReportingExecutor()
    trainset = _trainset()

    with patch("gepa_adk.api.AgentExecutor", return_value=executor):
        result = await evolve_workflow(
            workflow,
            trainset,
            scorer=RaiseOnceScorer(),
            primary="answerer",
            config=_config(),
        )

    assert isinstance(result, MultiAgentEvolutionResult)
    assert executor.reflection_calls == 2
    _assert_counters_match_records(result, len(trainset))
