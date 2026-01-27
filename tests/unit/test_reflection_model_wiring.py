"""Unit tests for reflection_agent wiring to proposer.

These tests verify that reflection_agent is correctly passed through the adapter
chain (ADKAdapter, MultiAgentAdapter) to create an AsyncReflectiveMutationProposer.

Note:
    These tests use mocks to verify wiring without actual LLM calls.
    The original reflection_model parameter has been deprecated in favor of
    reflection_agent, which uses ADK-native reflection via LlmAgent.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters.adk_adapter import ADKAdapter
from gepa_adk.adapters.multi_agent import MultiAgentAdapter
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
def mock_reflection_agent() -> LlmAgent:
    """Create a mock reflection agent for testing."""
    return LlmAgent(
        name="reflection_agent",
        model="gemini-2.5-flash",
        instruction="Reflect on feedback and propose improvements.",
    )


@pytest.fixture
def sample_trainset() -> list[dict[str, str]]:
    """Create a sample training set."""
    return [
        {"input": "What is 2+2?", "expected": "4"},
        {"input": "What is the capital of France?", "expected": "Paris"},
    ]


class TestADKAdapterReflectionAgentWiring:
    """Tests for ADKAdapter reflection_agent parameter wiring."""

    def test_adk_adapter_requires_proposer_or_reflection_agent(
        self, mock_agent: LlmAgent, mock_scorer_factory
    ) -> None:
        """Verify ADKAdapter raises ValueError if neither proposer nor reflection_agent provided."""
        scorer = mock_scorer_factory()
        mock_executor = MagicMock()

        with pytest.raises(
            ValueError,
            match="Either proposer, reflection_agent, or reflection_model must be provided",
        ):
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

    def test_adk_adapter_creates_proposer_from_reflection_agent(
        self, mock_agent: LlmAgent, mock_reflection_agent: LlmAgent, mock_scorer_factory
    ) -> None:
        """Verify ADKAdapter creates proposer from reflection_agent parameter.

        When reflection_agent is provided, ADKAdapter should:
        1. Call create_adk_reflection_fn with the reflection_agent
        2. Create an AsyncReflectiveMutationProposer with the resulting function
        """
        scorer = mock_scorer_factory()
        mock_executor = MagicMock()

        with patch(
            "gepa_adk.adapters.adk_adapter.create_adk_reflection_fn"
        ) as mock_create_fn:
            mock_reflection_fn = AsyncMock()
            mock_create_fn.return_value = mock_reflection_fn

            adapter = ADKAdapter(
                agent=mock_agent,
                scorer=scorer,
                executor=mock_executor,
                reflection_agent=mock_reflection_agent,
            )

            # Verify create_adk_reflection_fn was called with reflection_agent
            mock_create_fn.assert_called_once()
            call_args = mock_create_fn.call_args
            assert call_args[0][0] is mock_reflection_agent

            # Verify proposer was created
            assert isinstance(adapter._proposer, AsyncReflectiveMutationProposer)

    def test_adk_adapter_proposer_takes_precedence_over_reflection_agent(
        self,
        mock_agent: LlmAgent,
        mock_reflection_agent: LlmAgent,
        mock_scorer_factory,
        mock_proposer,
    ) -> None:
        """Verify proposer parameter takes precedence over reflection_agent.

        When both proposer and reflection_agent are provided, the proposer
        should be used and a warning logged.
        """
        scorer = mock_scorer_factory()
        mock_executor = MagicMock()

        with patch(
            "gepa_adk.adapters.adk_adapter.create_adk_reflection_fn"
        ) as mock_create_fn:
            adapter = ADKAdapter(
                agent=mock_agent,
                scorer=scorer,
                executor=mock_executor,
                proposer=mock_proposer,
                reflection_agent=mock_reflection_agent,
            )

            # Verify proposer is used directly (not created from reflection_agent)
            assert adapter._proposer is mock_proposer
            # Verify create_adk_reflection_fn was NOT called
            mock_create_fn.assert_not_called()

    def test_adk_adapter_validates_reflection_agent_type(
        self, mock_agent: LlmAgent, mock_scorer_factory
    ) -> None:
        """Verify ADKAdapter validates reflection_agent is an LlmAgent."""
        scorer = mock_scorer_factory()
        mock_executor = MagicMock()

        with pytest.raises(TypeError, match="reflection_agent must be LlmAgent"):
            ADKAdapter(
                agent=mock_agent,
                scorer=scorer,
                executor=mock_executor,
                reflection_agent="not_an_agent",
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
            AsyncReflectiveMutationProposer(adk_reflection_fn=None)  # type: ignore

    def test_proposer_accepts_adk_reflection_fn(self) -> None:
        """Verify AsyncReflectiveMutationProposer accepts valid adk_reflection_fn."""
        mock_reflection_fn = AsyncMock(return_value="improved text")

        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)

        assert proposer.adk_reflection_fn is mock_reflection_fn

    def test_proposer_logs_initialization(self) -> None:
        """Verify AsyncReflectiveMutationProposer logs at initialization."""
        mock_reflection_fn = AsyncMock(return_value="improved text")

        with patch("gepa_adk.engine.proposer.logger") as mock_logger:
            AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)

            # Verify INFO log was emitted
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "proposer_initialized"


class TestReflectionOutputFieldWiring:
    """Tests for reflection_output_field parameter wiring."""

    def test_adk_adapter_passes_output_field_to_reflection_fn(
        self, mock_agent: LlmAgent, mock_reflection_agent: LlmAgent, mock_scorer_factory
    ) -> None:
        """Verify ADKAdapter passes reflection_output_field to create_adk_reflection_fn.

        When reflection_output_field is provided, it should be passed through
        to the reflection function factory for structured output extraction.
        """
        scorer = mock_scorer_factory()
        mock_executor = MagicMock()

        with patch(
            "gepa_adk.adapters.adk_adapter.create_adk_reflection_fn"
        ) as mock_create_fn:
            mock_reflection_fn = AsyncMock()
            mock_create_fn.return_value = mock_reflection_fn

            ADKAdapter(
                agent=mock_agent,
                scorer=scorer,
                executor=mock_executor,
                reflection_agent=mock_reflection_agent,
                reflection_output_field="class_definition",
            )

            # Verify output_field was passed to create_adk_reflection_fn
            mock_create_fn.assert_called_once()
            call_kwargs = mock_create_fn.call_args[1]
            assert call_kwargs.get("output_field") == "class_definition"
