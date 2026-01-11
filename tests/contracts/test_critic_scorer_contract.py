"""Contract tests for CriticScorer protocol compliance.

These tests ensure CriticScorer satisfies the Scorer protocol with correct
method signatures, return types, and runtime checks. These are contract tests
that verify protocol compliance without requiring actual ADK agent execution.

Note:
    These tests use mocks to avoid requiring real ADK agents or API calls.
    Integration tests (in tests/integration/) verify actual ADK integration.
"""

from __future__ import annotations

import asyncio

import pytest
from google.adk.agents import LlmAgent
from pytest_mock import MockerFixture

from gepa_adk.adapters.critic_scorer import CriticScorer
from gepa_adk.ports.scorer import Scorer

pytestmark = pytest.mark.contract


@pytest.fixture
def mock_agent() -> LlmAgent:
    """Create a real LlmAgent for testing."""
    return LlmAgent(
        name="test_critic",
        model="gemini-2.0-flash",
        instruction="Test critic agent",
    )


class TestCriticScorerContract:
    """Contract tests for CriticScorer protocol compliance."""

    def test_critic_scorer_is_runtime_checkable(self, mock_agent: LlmAgent):
        """Verify CriticScorer satisfies Scorer protocol at runtime."""
        scorer = CriticScorer(critic_agent=mock_agent)
        assert isinstance(scorer, Scorer), "CriticScorer should satisfy Scorer protocol"

    def test_critic_scorer_has_required_methods(self, mock_agent: LlmAgent):
        """Verify CriticScorer implements both score() and async_score()."""
        scorer = CriticScorer(critic_agent=mock_agent)

        # Verify both methods exist and are callable
        assert hasattr(scorer, "score")
        assert hasattr(scorer, "async_score")
        assert callable(scorer.score)
        assert callable(scorer.async_score)

    def test_score_method_signature(self, mock_agent: LlmAgent):
        """Verify score() method has correct signature."""
        scorer = CriticScorer(critic_agent=mock_agent)

        # Check method signature via introspection
        import inspect

        sig = inspect.signature(scorer.score)
        params = list(sig.parameters.keys())

        assert "input_text" in params
        assert "output" in params
        assert "expected" in params

        # Check expected has default None
        assert sig.parameters["expected"].default is None

    def test_async_score_method_signature(self, mock_agent: LlmAgent):
        """Verify async_score() method has correct signature."""
        scorer = CriticScorer(critic_agent=mock_agent)

        import inspect

        sig = inspect.signature(scorer.async_score)
        params = list(sig.parameters.keys())

        assert "input_text" in params
        assert "output" in params
        assert "expected" in params
        assert "session_id" in params

        # Check expected and session_id have default None
        assert sig.parameters["expected"].default is None
        assert sig.parameters["session_id"].default is None

    @pytest.mark.asyncio
    async def test_async_score_returns_tuple_float_dict(
        self, mock_agent: LlmAgent, mocker: MockerFixture
    ):
        """Verify async_score() returns tuple[float, dict] format."""
        scorer = CriticScorer(critic_agent=mock_agent)

        # Mock the async_score implementation to return valid format
        mock_async_score = mocker.patch.object(
            scorer, "async_score", new_callable=mocker.AsyncMock
        )
        mock_async_score.return_value = (0.75, {"feedback": "Good"})

        result = await scorer.async_score("input", "output", "expected")

        assert isinstance(result, tuple)
        assert len(result) == 2
        score, metadata = result

        assert isinstance(score, float)
        assert isinstance(metadata, dict)

    def test_score_returns_tuple_float_dict(
        self, mock_agent: LlmAgent, mocker: MockerFixture
    ):
        """Verify score() returns tuple[float, dict] format."""
        scorer = CriticScorer(critic_agent=mock_agent)

        # Mock the score implementation to return valid format
        mock_score = mocker.patch.object(scorer, "score")
        mock_score.return_value = (0.75, {"feedback": "Good"})

        result = scorer.score("input", "output", "expected")

        assert isinstance(result, tuple)
        assert len(result) == 2
        score, metadata = result

        assert isinstance(score, float)
        assert isinstance(metadata, dict)

    @pytest.mark.asyncio
    async def test_async_score_is_awaitable(
        self, mock_agent: LlmAgent, mocker: MockerFixture
    ):
        """Verify async_score() method is a coroutine."""
        scorer = CriticScorer(critic_agent=mock_agent)

        # Mock async_score to return a coroutine
        mock_async_score = mocker.patch.object(
            scorer, "async_score", new_callable=mocker.AsyncMock
        )
        mock_async_score.return_value = (0.5, {})

        coro = scorer.async_score("input", "output", "expected")
        assert asyncio.iscoroutine(coro), "async_score() must be a coroutine"

        result = await coro
        assert isinstance(result, tuple)

    def test_score_with_none_expected(
        self, mock_agent: LlmAgent, mocker: MockerFixture
    ):
        """Verify score() handles None expected parameter."""
        scorer = CriticScorer(critic_agent=mock_agent)

        # Mock score to handle None expected
        mock_score = mocker.patch.object(scorer, "score")
        mock_score.return_value = (0.8, {"evaluation": "open_ended"})

        result = scorer.score("input", "output", expected=None)
        assert isinstance(result, tuple)
        score, metadata = result
        assert isinstance(score, float)

    @pytest.mark.asyncio
    async def test_async_score_with_none_expected(
        self, mock_agent: LlmAgent, mocker: MockerFixture
    ):
        """Verify async_score() handles None expected parameter."""
        scorer = CriticScorer(critic_agent=mock_agent)

        # Mock async_score to handle None expected
        mock_async_score = mocker.patch.object(
            scorer, "async_score", new_callable=mocker.AsyncMock
        )
        mock_async_score.return_value = (0.8, {"evaluation": "open_ended"})

        result = await scorer.async_score("input", "output", expected=None)
        assert isinstance(result, tuple)
        score, metadata = result
        assert isinstance(score, float)

    def test_metadata_accepts_any_dict(
        self, mock_agent: LlmAgent, mocker: MockerFixture
    ):
        """Verify metadata dict can contain various types."""
        scorer = CriticScorer(critic_agent=mock_agent)

        # Mock score to return complex metadata
        mock_score = mocker.patch.object(scorer, "score")
        mock_score.return_value = (
            0.7,
            {
                "feedback": "Good output",
                "dimension_scores": {"accuracy": 0.8, "fluency": 0.6},
                "nested": {"level1": {"level2": "value"}},
                "list_value": [1, 2, 3],
            },
        )

        score, metadata = scorer.score("input", "output")
        assert isinstance(metadata, dict)
        assert "feedback" in metadata
        assert "dimension_scores" in metadata
        assert isinstance(metadata["dimension_scores"], dict)

    def test_boundary_scores(self, mock_agent: LlmAgent, mocker: MockerFixture):
        """Verify 0.0 and 1.0 are valid scores (edge case)."""
        scorer = CriticScorer(critic_agent=mock_agent)

        # Test with 0.0
        mock_score = mocker.patch.object(scorer, "score")
        mock_score.return_value = (0.0, {"boundary": "zero"})
        score, metadata = scorer.score("input", "output")
        assert score == 0.0

        # Test with 1.0
        mock_score.return_value = (1.0, {"boundary": "one"})
        score, metadata = scorer.score("input", "output")
        assert score == 1.0
