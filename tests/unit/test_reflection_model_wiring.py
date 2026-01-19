"""Unit tests for reflection_model config wiring to proposer.

These tests verify that `EvolutionConfig.reflection_model` is correctly passed
through the adapter chain (ADKAdapter, MultiAgentAdapter) to the
AsyncReflectiveMutationProposer.

Note:
    These tests use mocks to verify wiring without actual LLM calls.
    See spec: specs/031-wire-reflection-model/spec.md
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from gepa_adk import evolve, evolve_group
from gepa_adk.adapters.adk_adapter import ADKAdapter
from gepa_adk.adapters.multi_agent import MultiAgentAdapter
from gepa_adk.domain.models import EvolutionConfig, EvolutionResult, IterationRecord

pytestmark = pytest.mark.unit


class MockScorer:
    """Mock scorer for testing."""

    def __init__(self, score_value: float = 0.8) -> None:
        """Initialize with a fixed score value."""
        self.score_value = score_value

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict]:
        """Return fixed score."""
        return (self.score_value, {})

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict]:
        """Return fixed score asynchronously."""
        return (self.score_value, {})


@pytest.fixture
def mock_agent() -> LlmAgent:
    """Create a mock LlmAgent for testing."""
    return LlmAgent(
        name="test_agent",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant.",
    )


@pytest.fixture
def sample_trainset() -> list[dict[str, str]]:
    """Create a sample training set."""
    return [
        {"input": "What is 2+2?", "expected": "4"},
        {"input": "What is the capital of France?", "expected": "Paris"},
    ]


@pytest.fixture
def mock_evolution_result() -> EvolutionResult:
    """Create a mock EvolutionResult for testing."""
    return EvolutionResult(
        original_score=0.5,
        final_score=0.8,
        evolved_components={"instruction": "Improved instruction"},
        iteration_history=[
            IterationRecord(
                iteration_number=1,
                score=0.6,
                component_text="Test instruction",
                evolved_component="instruction",
                accepted=True,
            )
        ],
        total_iterations=1,
    )


class TestADKAdapterReflectionModelWiring:
    """Tests for ADKAdapter reflection_model parameter wiring (T002)."""

    def test_adk_adapter_passes_reflection_model_to_proposer(
        self, mock_agent: LlmAgent
    ) -> None:
        """T002: Verify ADKAdapter passes reflection_model to AsyncReflectiveMutationProposer.

        This test verifies that when ADKAdapter is created with a reflection_model
        parameter, it passes that model to the default AsyncReflectiveMutationProposer
        during initialization.
        """
        custom_model = "gemini/gemini-2.5-pro"
        scorer = MockScorer()

        with patch(
            "gepa_adk.adapters.adk_adapter.AsyncReflectiveMutationProposer"
        ) as mock_proposer_class:
            mock_proposer_instance = MagicMock()
            mock_proposer_class.return_value = mock_proposer_instance

            # Create ADKAdapter with custom reflection_model
            ADKAdapter(
                agent=mock_agent,
                scorer=scorer,
                reflection_model=custom_model,
            )

            # Verify proposer was created with the custom model
            mock_proposer_class.assert_called_once()
            call_kwargs = mock_proposer_class.call_args[1]
            assert "model" in call_kwargs
            assert call_kwargs["model"] == custom_model


class TestMultiAgentAdapterReflectionModelWiring:
    """Tests for MultiAgentAdapter reflection_model parameter wiring (T003)."""

    def test_multi_agent_adapter_passes_reflection_model_to_proposer(
        self,
    ) -> None:
        """T003: Verify MultiAgentAdapter passes reflection_model to proposer.

        This test verifies that when MultiAgentAdapter is created with a reflection_model
        parameter, it passes that model to the default AsyncReflectiveMutationProposer
        during initialization.
        """
        custom_model = "anthropic/claude-3-haiku"

        # Create test agents
        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        )

        class CriticSchema(BaseModel):
            score: float

        critic = LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review code",
            output_schema=CriticSchema,
        )

        with patch(
            "gepa_adk.adapters.multi_agent.AsyncReflectiveMutationProposer"
        ) as mock_proposer_class:
            mock_proposer_instance = MagicMock()
            mock_proposer_class.return_value = mock_proposer_instance

            # Create MultiAgentAdapter with custom reflection_model
            MultiAgentAdapter(
                agents=[generator, critic],
                primary="critic",
                reflection_model=custom_model,
            )

            # Verify proposer was created with the custom model
            mock_proposer_class.assert_called_once()
            call_kwargs = mock_proposer_class.call_args[1]
            assert "model" in call_kwargs
            assert call_kwargs["model"] == custom_model


class TestEvolveReflectionModelWiring:
    """Tests for evolve() reflection_model wiring (T004)."""

    @pytest.mark.asyncio
    async def test_evolve_passes_config_reflection_model_to_adapter(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """T004: Verify evolve() passes config.reflection_model to ADKAdapter.

        This test verifies that when evolve() is called with an EvolutionConfig
        containing a custom reflection_model, it passes that model to ADKAdapter.
        """
        custom_model = "ollama_chat/llama3:8b"
        config = EvolutionConfig(
            max_iterations=10,
            reflection_model=custom_model,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.CriticScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_evolution_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MockScorer()
            mock_scorer_class.return_value = mock_scorer_instance

            critic = LlmAgent(
                name="critic",
                model="gemini-2.0-flash",
                instruction="Score responses.",
            )

            # Call evolve with custom reflection_model in config
            await evolve(
                mock_agent,
                sample_trainset,
                critic=critic,
                config=config,
            )

            # Verify ADKAdapter was created with reflection_model
            call_kwargs = mock_adapter_class.call_args[1]
            assert "reflection_model" in call_kwargs
            assert call_kwargs["reflection_model"] == custom_model


class TestEvolveGroupReflectionModelWiring:
    """Tests for evolve_group() reflection_model wiring (T005)."""

    @pytest.mark.asyncio
    async def test_evolve_group_passes_config_reflection_model_to_adapter(
        self,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """T005: Verify evolve_group() passes config.reflection_model to MultiAgentAdapter.

        This test verifies that when evolve_group() is called with an EvolutionConfig
        containing a custom reflection_model, it passes that model to MultiAgentAdapter.
        """
        custom_model = "gemini/gemini-2.5-flash"
        config = EvolutionConfig(
            max_iterations=10,
            reflection_model=custom_model,
        )

        # Create test agents
        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        )

        # Create critic with output_schema for scoring
        class CriticOutput(BaseModel):
            score: float = Field(ge=0.0, le=1.0)

        critic_agent = LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review code",
            output_schema=CriticOutput,
        )

        mock_evolution_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Improved instruction"},
            iteration_history=[],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.MultiAgentAdapter") as mock_adapter_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_evolution_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            # Call evolve_group with custom reflection_model in config
            await evolve_group(
                agents=[generator, critic_agent],
                primary="critic",
                trainset=sample_trainset,
                config=config,
            )

            # Verify MultiAgentAdapter was created with reflection_model
            call_kwargs = mock_adapter_class.call_args[1]
            assert "reflection_model" in call_kwargs
            assert call_kwargs["reflection_model"] == custom_model


class TestDefaultReflectionModelBehavior:
    """Tests for default reflection_model behavior (US2: T014-T015)."""

    def test_default_reflection_model_used_when_not_specified(
        self, mock_agent: LlmAgent
    ) -> None:
        """T014: Verify default reflection_model is used when not specified.

        This test verifies that when ADKAdapter is created without a reflection_model
        parameter, the default model from EvolutionConfig is used.
        """
        scorer = MockScorer()

        with patch(
            "gepa_adk.adapters.adk_adapter.AsyncReflectiveMutationProposer"
        ) as mock_proposer_class:
            mock_proposer_instance = MagicMock()
            mock_proposer_class.return_value = mock_proposer_instance

            # Create ADKAdapter without explicit reflection_model
            ADKAdapter(
                agent=mock_agent,
                scorer=scorer,
            )

            # Verify proposer was created with default model
            # The default should match EvolutionConfig.reflection_model default
            mock_proposer_class.assert_called_once()
            call_kwargs = mock_proposer_class.call_args[1]
            # Should use the default model ("ollama_chat/gpt-oss:20b")
            assert "model" in call_kwargs
            assert call_kwargs["model"] == "ollama_chat/gpt-oss:20b"

    def test_adapter_default_matches_config_default(self) -> None:
        """T015: Verify adapter default reflection_model matches EvolutionConfig default.

        This test verifies that the default reflection_model value used by adapters
        is consistent with EvolutionConfig.reflection_model default.
        """
        # Get the EvolutionConfig default
        config = EvolutionConfig()
        config_default = config.reflection_model

        # The adapter should use the same default
        # This is verified by checking the ADKAdapter default parameter value
        # Since we can't easily inspect default parameter values at runtime,
        # we verify via the docstring or by creating an adapter and checking
        # the proposer's model value

        scorer = MockScorer()
        mock_agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test instruction",
        )

        with patch(
            "gepa_adk.adapters.adk_adapter.AsyncReflectiveMutationProposer"
        ) as mock_proposer_class:
            mock_proposer_instance = MagicMock()
            mock_proposer_class.return_value = mock_proposer_instance

            # Create adapter without explicit reflection_model
            ADKAdapter(agent=mock_agent, scorer=scorer)

            # Verify the proposer was created with the same default as EvolutionConfig
            call_kwargs = mock_proposer_class.call_args[1]
            adapter_default = call_kwargs.get("model")
            assert adapter_default == config_default, (
                f"ADKAdapter default ({adapter_default}) does not match "
                f"EvolutionConfig default ({config_default})"
            )


class TestProposerLogsReflectionModel:
    """Tests for proposer logging reflection_model (US3: T019)."""

    def test_proposer_logs_reflection_model_on_init(self) -> None:
        """T019: Verify AsyncReflectiveMutationProposer logs reflection_model at INFO level.

        This test verifies that when AsyncReflectiveMutationProposer is initialized,
        it logs the reflection_model at INFO level for transparency.
        """
        custom_model = "gemini/gemini-2.5-pro"

        with patch("gepa_adk.engine.proposer.logger") as mock_logger:
            from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

            # Create proposer with custom model
            AsyncReflectiveMutationProposer(model=custom_model)

            # Verify INFO log was emitted with reflection_model
            # The log should contain the model identifier
            info_calls = mock_logger.info.call_args_list
            assert len(info_calls) >= 1, "Expected at least one INFO log call"

            # Check that the model was logged
            log_found = False
            for call in info_calls:
                call_str = str(call)
                if "proposer_initialized" in call_str or custom_model in call_str:
                    log_found = True
                    break

            assert log_found, (
                f"Expected INFO log with 'proposer_initialized' or model "
                f"'{custom_model}', but got: {info_calls}"
            )
