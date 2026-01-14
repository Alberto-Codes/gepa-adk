"""Unit tests for evolve() and evolve_sync() API functions.

These tests verify the behavior of the public API functions using mocks
to avoid requiring actual ADK agent execution or LLM API calls.

Note:
    These tests use mocks for AsyncGEPAEngine, ADKAdapter, and Scorer
    to test the API logic without external dependencies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from gepa_adk import evolve, evolve_sync
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import EvolutionConfig, EvolutionResult, IterationRecord
from gepa_adk.domain.types import TrajectoryConfig

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
def mock_evolution_result() -> EvolutionResult:
    """Create a mock EvolutionResult for testing."""
    return EvolutionResult(
        original_score=0.5,
        final_score=0.8,
        evolved_instruction="Improved instruction",
        iteration_history=[
            IterationRecord(
                iteration_number=1,
                score=0.6,
                instruction="Test instruction",
                accepted=True,
            )
        ],
        total_iterations=1,
    )


@pytest.fixture
def sample_trainset() -> list[dict[str, str]]:
    """Create a sample training set."""
    return [
        {"input": "What is 2+2?", "expected": "4"},
        {"input": "What is the capital of France?", "expected": "Paris"},
    ]


class TestEvolve:
    """Unit tests for evolve() function."""

    @pytest.mark.asyncio
    async def test_evolve_with_mocked_engine(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """Test evolve() with mocked engine returns EvolutionResult."""
        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.CriticScorer") as mock_scorer_class,
            patch("gepa_adk.api.SchemaBasedScorer"),
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_evolution_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MockScorer()
            mock_scorer_class.return_value = mock_scorer_instance

            # Create critic agent
            critic = LlmAgent(
                name="critic",
                model="gemini-2.0-flash",
                instruction="Score responses.",
            )

            # Call evolve
            result = await evolve(mock_agent, sample_trainset, critic=critic)

            # Verify result
            assert isinstance(result, EvolutionResult)
            assert result.evolved_instruction == "Improved instruction"
            assert result.final_score == 0.8

            # Verify engine was called correctly
            mock_engine_class.assert_called_once()
            mock_engine_instance.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_evolve_validation_errors(
        self, mock_agent: LlmAgent, sample_trainset: list[dict[str, str]]
    ) -> None:
        """Test evolve() raises ConfigurationError for invalid inputs."""
        # Test empty trainset
        with pytest.raises(ConfigurationError, match="trainset cannot be empty"):
            await evolve(mock_agent, [])

        # Test trainset without "input" key
        invalid_trainset = [{"expected": "4"}]  # Missing "input" key
        with pytest.raises(ConfigurationError, match="must have 'input' key"):
            await evolve(mock_agent, invalid_trainset)

        # Test invalid agent type (not LlmAgent)
        with pytest.raises(
            ConfigurationError, match="agent must be an LlmAgent instance"
        ):
            await evolve("not an agent", sample_trainset)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_evolve_with_schema_based_scorer(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """Test evolve() uses schema-based scorer when agent has output_schema."""

        # Create schema for agent
        class OutputSchema(BaseModel):
            score: float = Field(ge=0.0, le=1.0)
            result: str

        agent_with_schema = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="You are helpful.",
            output_schema=OutputSchema,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_evolution_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MockScorer()
            mock_scorer_class.return_value = mock_scorer_instance

            # Call evolve without critic (should use schema-based scorer)
            result = await evolve(agent_with_schema, sample_trainset)

            # Verify schema-based scorer was created
            mock_scorer_class.assert_called_once_with(output_schema=OutputSchema)

            # Verify result
            assert isinstance(result, EvolutionResult)

    @pytest.mark.asyncio
    async def test_evolve_requires_critic_or_schema(
        self, mock_agent: LlmAgent, sample_trainset: list[dict[str, str]]
    ) -> None:
        """Test evolve() raises error if no critic and no output_schema."""
        with pytest.raises(
            ConfigurationError,
            match="Either critic must be provided or agent must have output_schema",
        ):
            await evolve(mock_agent, sample_trainset)


class TestEvolveOptionalParameters:
    """Unit tests for evolve() optional parameters (US3)."""

    @pytest.mark.asyncio
    async def test_evolve_with_custom_config(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """Test evolve() accepts custom EvolutionConfig."""
        custom_config = EvolutionConfig(
            max_iterations=100,
            patience=10,
            min_improvement_threshold=0.02,
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

            # Call evolve with custom config
            result = await evolve(
                mock_agent, sample_trainset, critic=critic, config=custom_config
            )

            # Verify engine was created with custom config
            call_kwargs = mock_engine_class.call_args[1]
            assert call_kwargs["config"] == custom_config

            # Verify result
            assert isinstance(result, EvolutionResult)

    @pytest.mark.asyncio
    async def test_evolve_with_critic_agent(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """Test evolve() uses CriticScorer when critic agent provided."""
        critic = LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Score responses.",
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

            # Call evolve with critic
            result = await evolve(mock_agent, sample_trainset, critic=critic)

            # Verify CriticScorer was created with critic agent
            mock_scorer_class.assert_called_once_with(critic_agent=critic)

            # Verify result
            assert isinstance(result, EvolutionResult)

    @pytest.mark.asyncio
    async def test_evolve_with_trajectory_config(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """Test evolve() accepts custom TrajectoryConfig."""
        trajectory_config = TrajectoryConfig(
            redact_sensitive=True,
            max_string_length=5000,
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

            # Call evolve with trajectory_config
            result = await evolve(
                mock_agent,
                sample_trainset,
                critic=critic,
                trajectory_config=trajectory_config,
            )

            # Verify adapter was created with trajectory_config
            call_kwargs = mock_adapter_class.call_args[1]
            assert call_kwargs["trajectory_config"] == trajectory_config

            # Verify result
            assert isinstance(result, EvolutionResult)

    @pytest.mark.asyncio
    async def test_evolve_logs_debug_for_reflection_agent(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """Test evolve() logs debug when reflection_agent is provided."""
        reflection_agent = LlmAgent(
            name="reflection",
            model="gemini-2.0-flash",
            instruction="Propose improvements.",
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.CriticScorer") as mock_scorer_class,
            patch("gepa_adk.api.logger") as mock_logger,
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

            # Call evolve with reflection_agent
            result = await evolve(
                mock_agent,
                sample_trainset,
                critic=critic,
                reflection_agent=reflection_agent,
            )

            # Verify debug was logged
            mock_logger.debug.assert_called_once()
            debug_call = mock_logger.debug.call_args
            assert "reflection_agent" in str(debug_call).lower()

            # Verify result still works
            assert isinstance(result, EvolutionResult)


class TestEvolveValset:
    """Unit tests for evolve() with validation dataset (US4)."""

    @pytest.mark.asyncio
    async def test_evolve_with_valset(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """Test evolve() evaluates final instruction on valset."""
        valset = [
            {"input": "What is 3+3?", "expected": "6"},
            {"input": "What is the capital of Spain?", "expected": "Madrid"},
        ]

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.CriticScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_evolution_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = AsyncMock()
            # Mock valset evaluation
            from gepa_adk.ports.adapter import EvaluationBatch

            mock_adapter_instance.evaluate = AsyncMock(
                return_value=EvaluationBatch(
                    outputs=["6", "Madrid"],
                    scores=[0.9, 0.85],
                    trajectories=None,
                )
            )
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MockScorer()
            mock_scorer_class.return_value = mock_scorer_instance

            critic = LlmAgent(
                name="critic",
                model="gemini-2.0-flash",
                instruction="Score responses.",
            )

            # Call evolve with valset
            result = await evolve(
                mock_agent, sample_trainset, valset=valset, critic=critic
            )

            # Verify adapter.evaluate was called for valset
            assert mock_adapter_instance.evaluate.call_count >= 1

            # Verify result
            assert isinstance(result, EvolutionResult)


class TestEvolveSync:
    """Unit tests for evolve_sync() function."""

    def test_evolve_sync_calls_evolve(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """Test evolve_sync() calls evolve() and returns result."""
        with (
            patch("gepa_adk.api.evolve") as mock_evolve,
            patch("asyncio.run") as mock_asyncio_run,
        ):
            # Setup mocks
            mock_evolve.return_value = mock_evolution_result
            mock_asyncio_run.return_value = mock_evolution_result

            # Call evolve_sync
            result = evolve_sync(mock_agent, sample_trainset, critic=None)

            # Verify asyncio.run was called
            mock_asyncio_run.assert_called_once()

            # Verify result
            assert isinstance(result, EvolutionResult)


class TestEvolveReflectionAgent:
    """Unit tests for evolve() with reflection_agent parameter (US1)."""

    @pytest.mark.asyncio
    async def test_evolve_passes_reflection_agent_to_adapter(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """T003: Verify evolve() passes reflection_agent to ADKAdapter."""
        reflection_agent = LlmAgent(
            name="reflection_agent",
            model="gemini-2.0-flash",
            instruction="Improve instructions based on feedback.",
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

            # Call evolve with reflection_agent
            result = await evolve(
                mock_agent,
                sample_trainset,
                critic=critic,
                reflection_agent=reflection_agent,
            )

            # Verify ADKAdapter was created with reflection_agent
            call_kwargs = mock_adapter_class.call_args[1]
            assert "reflection_agent" in call_kwargs
            assert call_kwargs["reflection_agent"] is reflection_agent

            # Verify result
            assert isinstance(result, EvolutionResult)


class TestEvolveDefaultReflectionBehavior:
    """Unit tests for evolve() default reflection behavior (US2)."""

    @pytest.mark.asyncio
    async def test_evolve_without_reflection_agent_uses_default(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """T012: Verify evolve() uses default behavior when reflection_agent omitted."""
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

            # Call evolve without reflection_agent
            result = await evolve(mock_agent, sample_trainset, critic=critic)

            # Verify ADKAdapter was created without reflection_agent
            call_kwargs = mock_adapter_class.call_args[1]
            assert (
                "reflection_agent" not in call_kwargs
                or call_kwargs["reflection_agent"] is None
            )

            # Verify result
            assert isinstance(result, EvolutionResult)

    @pytest.mark.asyncio
    async def test_evolve_no_warning_when_reflection_agent_omitted(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """T013: Verify no warning logged when reflection_agent omitted."""
        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.CriticScorer") as mock_scorer_class,
            patch("gepa_adk.api.logger") as mock_logger,
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

            # Call evolve without reflection_agent
            result = await evolve(mock_agent, sample_trainset, critic=critic)

            # Verify no warning was logged
            warning_calls = [
                call
                for call in mock_logger.warning.call_args_list
                if "reflection_agent" in str(call).lower()
            ]
            assert len(warning_calls) == 0, (
                "No warning should be logged when reflection_agent is omitted"
            )

            # Verify result
            assert isinstance(result, EvolutionResult)
            assert result.evolved_instruction == "Improved instruction"

    def test_evolve_sync_nested_event_loop_handling(
        self,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """Test evolve_sync() handles nested event loops with nest_asyncio."""
        import sys

        # Create agent with output_schema to satisfy validation requirements
        class TestOutputSchema(BaseModel):
            score: float = Field(ge=0.0, le=1.0)
            result: str

        agent_with_schema = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="You are a helpful assistant.",
            output_schema=TestOutputSchema,
        )

        # Create a mock nest_asyncio module
        mock_nest_asyncio = MagicMock()
        mock_nest_asyncio.apply = MagicMock()

        # Track asyncio.run calls
        asyncio_run_mock = MagicMock()
        nested_error = RuntimeError(
            "asyncio.run() cannot be called from a running event loop"
        )

        def asyncio_run_side_effect(*args, **kwargs):
            if asyncio_run_mock.call_count == 1:
                raise nested_error
            return mock_evolution_result

        asyncio_run_mock.side_effect = asyncio_run_side_effect

        with patch.dict(sys.modules, {"nest_asyncio": mock_nest_asyncio}):
            with patch("asyncio.run", asyncio_run_mock):
                # Call evolve_sync - should handle nested loop
                result = evolve_sync(agent_with_schema, sample_trainset)

                # Verify nest_asyncio was applied
                mock_nest_asyncio.apply.assert_called_once()

                # Verify asyncio.run was called twice (once failing, once succeeding)
                assert asyncio_run_mock.call_count == 2

                # Verify result
                assert isinstance(result, EvolutionResult)

    def test_evolve_sync_passes_kwargs(
        self,
        mock_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        mock_evolution_result: EvolutionResult,
    ) -> None:
        """Test evolve_sync() passes **kwargs to evolve()."""
        with (
            patch("gepa_adk.api.evolve") as mock_evolve,
            patch("asyncio.run") as mock_asyncio_run,
        ):
            # Setup mocks
            async def mock_evolve_func(*args, **kwargs):
                return mock_evolution_result

            mock_evolve.side_effect = mock_evolve_func
            mock_asyncio_run.return_value = mock_evolution_result

            config = EvolutionConfig(max_iterations=50)
            trajectory_config = TrajectoryConfig()

            # Call evolve_sync with kwargs
            result = evolve_sync(
                mock_agent,
                sample_trainset,
                config=config,
                trajectory_config=trajectory_config,
            )

            # Verify asyncio.run was called
            mock_asyncio_run.assert_called_once()

            # Verify result
            assert isinstance(result, EvolutionResult)
