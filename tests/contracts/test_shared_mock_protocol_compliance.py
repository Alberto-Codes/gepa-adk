"""Contract tests verifying shared test mocks satisfy their protocols.

The root ``conftest.py`` defines ``MockScorer`` and ``MockExecutor`` which
are referenced 638 times across 27 test files. Unlike ``MockAdapter``
(which inherits from ``AsyncGEPAAdapter``), these mocks are duck-typed
and never verified against their protocols. If a protocol changes and
the mock doesn't keep up, every dependent test silently tests against a
phantom.

Note:
    This module guards the test foundation. A failure here means the
    shared mock infrastructure has drifted from its protocol and all
    tests using it may be giving false confidence.
"""

from __future__ import annotations

import asyncio

import pytest

from gepa_adk.ports.agent_executor import (
    AgentExecutorProtocol,
    ExecutionResult,
    ExecutionStatus,
)
from gepa_adk.ports.scorer import Scorer
from tests.conftest import MockExecutor, MockScorer

pytestmark = pytest.mark.contract


class TestMockScorerProtocolCompliance:
    """Verify conftest.MockScorer satisfies the Scorer protocol."""

    def _make_scorer(self):
        """Instantiate MockScorer from conftest."""
        return MockScorer(score_value=0.7)

    def test_mock_scorer_satisfies_scorer_protocol(self) -> None:
        """MockScorer must pass isinstance check against Scorer."""
        scorer = self._make_scorer()
        assert isinstance(scorer, Scorer), (
            "MockScorer has drifted from Scorer protocol — "
            "all tests using mock_scorer_factory are unreliable"
        )

    def test_mock_scorer_score_returns_correct_type(self) -> None:
        """MockScorer.score() must return tuple[float, dict]."""
        scorer = self._make_scorer()
        result = scorer.score("input", "output", "expected")

        assert isinstance(result, tuple)
        assert len(result) == 2
        score, metadata = result
        assert isinstance(score, float)
        assert isinstance(metadata, dict)

    async def test_mock_scorer_async_score_returns_correct_type(self) -> None:
        """MockScorer.async_score() must return tuple[float, dict]."""
        scorer = self._make_scorer()
        result = await scorer.async_score("input", "output", "expected")

        assert isinstance(result, tuple)
        assert len(result) == 2
        score, metadata = result
        assert isinstance(score, float)
        assert isinstance(metadata, dict)

    async def test_mock_scorer_async_score_is_coroutine(self) -> None:
        """MockScorer.async_score() must be a real coroutine."""
        scorer = self._make_scorer()
        assert asyncio.iscoroutinefunction(scorer.async_score)

    def test_mock_scorer_records_calls(self) -> None:
        """MockScorer.score_calls must track invocations."""
        scorer = self._make_scorer()
        scorer.score("q1", "a1", "e1")
        scorer.score("q2", "a2")

        assert len(scorer.score_calls) == 2
        assert scorer.score_calls[0] == ("q1", "a1", "e1")
        assert scorer.score_calls[1] == ("q2", "a2", None)


class TestMockExecutorProtocolCompliance:
    """Verify conftest.MockExecutor satisfies AgentExecutorProtocol."""

    def _make_executor(self):
        """Instantiate MockExecutor from conftest."""
        return MockExecutor()

    def test_mock_executor_satisfies_agent_executor_protocol(self) -> None:
        """MockExecutor must pass isinstance check against AgentExecutorProtocol."""
        executor = self._make_executor()
        assert isinstance(executor, AgentExecutorProtocol), (
            "MockExecutor has drifted from AgentExecutorProtocol — "
            "all tests using mock_executor fixture are unreliable"
        )

    def test_mock_executor_execute_agent_is_async(self) -> None:
        """MockExecutor.execute_agent must be a coroutine function."""
        executor = self._make_executor()
        assert asyncio.iscoroutinefunction(executor.execute_agent)

    async def test_mock_executor_returns_execution_result(self) -> None:
        """MockExecutor.execute_agent() must return ExecutionResult."""
        executor = self._make_executor()
        result = await executor.execute_agent(
            agent=None,
            input_text="test input",
        )

        assert isinstance(result, ExecutionResult)
        assert result.status == ExecutionStatus.SUCCESS
        assert isinstance(result.session_id, str)

    async def test_mock_executor_tracks_calls(self) -> None:
        """MockExecutor must record execute_agent invocations."""
        executor = self._make_executor()
        await executor.execute_agent(agent="agent1", input_text="hello")
        await executor.execute_agent(agent="agent2", input_text="world")

        assert executor.execute_count == 2
        assert len(executor.calls) == 2
        assert executor.calls[0]["input_text"] == "hello"
        assert executor.calls[1]["input_text"] == "world"
