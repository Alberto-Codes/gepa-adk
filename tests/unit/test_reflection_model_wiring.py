"""Unit tests for proposer wiring to ADKAdapter and MultiAgentAdapter.

These tests verify that the proposer parameter is correctly accepted and stored
by ADKAdapter and MultiAgentAdapter.

Note:
    These tests use mocks to verify wiring without actual LLM calls.
    The reflection_agent parameter has been removed from ADKAdapter in favor of
    requiring a pre-constructed proposer instance.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter
from gepa_adk.adapters.evolution.multi_agent import MultiAgentAdapter
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_agent() -> LlmAgent:
    """Create a mock LlmAgent for testing."""
    return LlmAgent(
        name="test_agent",
        model="gemini-2.5-flash",
        instruction="You are a helpful assistant.",
    )


@pytest.fixture
def sample_trainset() -> list[dict[str, str]]:
    """Create a sample training set."""
    return [
        {"input": "What is 2+2?", "expected": "4"},
        {"input": "What is the capital of France?", "expected": "Paris"},
    ]


class TestADKAdapterProposerWiring:
    """Tests for ADKAdapter proposer parameter wiring."""

    def test_adk_adapter_requires_proposer(
        self, mock_agent: LlmAgent, mock_scorer_factory
    ) -> None:
        """Verify ADKAdapter raises ValueError if proposer is not provided."""
        scorer = mock_scorer_factory()
        mock_executor = MagicMock()

        with pytest.raises(ValueError, match="proposer is required"):
            ADKAdapter(
                agent=mock_agent,
                scorer=scorer,
                executor=mock_executor,
            )

    def test_adk_adapter_accepts_proposer_parameter(
        self, mock_agent: LlmAgent, mock_scorer_factory, mock_proposer
    ) -> None:
        """Verify ADKAdapter accepts proposer parameter and uses it directly."""
        scorer = mock_scorer_factory()
        mock_executor = MagicMock()

        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=scorer,
            executor=mock_executor,
            proposer=mock_proposer,
        )

        assert adapter._proposer is mock_proposer

    def test_adk_adapter_rejects_none_proposer(
        self, mock_agent: LlmAgent, mock_scorer_factory
    ) -> None:
        """Verify ADKAdapter raises ValueError when proposer=None explicitly."""
        scorer = mock_scorer_factory()
        mock_executor = MagicMock()

        with pytest.raises(ValueError, match="proposer is required"):
            ADKAdapter(
                agent=mock_agent,
                scorer=scorer,
                executor=mock_executor,
                proposer=None,
            )


class TestMultiAgentAdapterProposerWiring:
    """Tests for MultiAgentAdapter proposer parameter wiring."""

    def test_multi_agent_adapter_requires_proposer(self, mock_scorer_factory) -> None:
        """Verify MultiAgentAdapter requires proposer parameter."""
        generator = LlmAgent(
            name="generator",
            model="gemini-2.5-flash",
            instruction="Generate content",
        )
        critic = LlmAgent(
            name="critic",
            model="gemini-2.5-flash",
            instruction="Review content",
            output_schema=None,
        )

        scorer = mock_scorer_factory()

        with pytest.raises(ValueError, match="proposer is required"):
            MultiAgentAdapter(
                agents={"generator": generator, "critic": critic},
                primary="generator",
                components={"generator": ["instruction"], "critic": ["instruction"]},
                scorer=scorer,
                proposer=None,
            )

    def test_multi_agent_adapter_accepts_proposer(
        self, mock_scorer_factory, mock_proposer
    ) -> None:
        """Verify MultiAgentAdapter accepts and stores proposer parameter."""
        generator = LlmAgent(
            name="generator",
            model="gemini-2.5-flash",
            instruction="Generate content",
        )
        critic = LlmAgent(
            name="critic",
            model="gemini-2.5-flash",
            instruction="Review content",
        )

        scorer = mock_scorer_factory()

        adapter = MultiAgentAdapter(
            agents={"generator": generator, "critic": critic},
            primary="generator",
            components={"generator": ["instruction"], "critic": ["instruction"]},
            scorer=scorer,
            proposer=mock_proposer,
        )

        assert adapter._proposer is mock_proposer


class TestProposerRequiresReflectionFn:
    """Tests for AsyncReflectiveMutationProposer initialization requirements."""

    def test_proposer_requires_adk_reflection_fn(self) -> None:
        """Verify AsyncReflectiveMutationProposer requires adk_reflection_fn parameter."""
        with pytest.raises(ValueError, match="adk_reflection_fn is required"):
            AsyncReflectiveMutationProposer(adk_reflection_fn=None)

    def test_proposer_accepts_adk_reflection_fn(self) -> None:
        """Verify AsyncReflectiveMutationProposer accepts valid adk_reflection_fn."""
        mock_reflection_fn = AsyncMock(return_value=("improved text", None))

        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)

        assert proposer.adk_reflection_fn is mock_reflection_fn

    def test_proposer_logs_initialization(self) -> None:
        """Verify AsyncReflectiveMutationProposer logs at initialization."""
        mock_reflection_fn = AsyncMock(return_value=("improved text", None))

        with patch("gepa_adk.engine.proposer.logger") as mock_logger:
            AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)

            # Verify INFO log was emitted
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "proposer_initialized"
