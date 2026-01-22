"""Unit tests for MultiAgentAdapter implementation.

These tests verify the business logic of MultiAgentAdapter using mocked dependencies
to isolate the adapter behavior from external ADK services.

Note:
    Unit tests use mocked ADK agents and runners to avoid real API calls.
    Integration tests (in tests/integration/) use real ADK services.
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent, SequentialAgent

from gepa_adk.adapters import MultiAgentAdapter
from gepa_adk.domain.exceptions import MultiAgentValidationError
from tests.conftest import MockScorer

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_agents() -> dict[str, LlmAgent]:
    """Create mock ADK agents dict for testing."""
    return {
        "generator": LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        ),
        "critic": LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review code",
        ),
    }


@pytest.fixture
def mock_components() -> dict[str, list[str]]:
    """Create mock components mapping for testing."""
    return {
        "generator": ["instruction"],
        "critic": ["instruction"],
    }


@pytest.fixture
def mock_scorer() -> MockScorer:
    """Create a mock scorer."""
    return MockScorer(score_value=0.85)


@pytest.fixture
def adapter(
    mock_agents: dict[str, LlmAgent],
    mock_components: dict[str, list[str]],
    mock_scorer: MockScorer,
    mock_proposer,
) -> MultiAgentAdapter:
    """Create a MultiAgentAdapter for testing."""
    return MultiAgentAdapter(
        agents=mock_agents,
        primary="generator",
        components=mock_components,
        scorer=mock_scorer,
        proposer=mock_proposer,
    )


class TestMultiAgentAdapterConstructor:
    """Unit tests for MultiAgentAdapter constructor (Phase 2: Foundational).

    Note:
        Tests verify validation logic for agents, primary, components, and scorer.
    """

    def test_constructor_accepts_valid_agents(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_components: dict[str, list[str]],
        mock_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """Verify constructor accepts valid agents dict."""
        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            components=mock_components,
            scorer=mock_scorer,
            proposer=mock_proposer,
        )

        assert len(adapter.agents) == 2
        assert adapter.primary == "generator"

    def test_constructor_validates_empty_agents_dict(
        self,
        mock_components: dict[str, list[str]],
        mock_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """Verify constructor raises MultiAgentValidationError for empty dict."""
        with pytest.raises(
            MultiAgentValidationError, match="agents dict cannot be empty"
        ):
            MultiAgentAdapter(
                agents={},
                primary="generator",
                components=mock_components,
                scorer=mock_scorer,
                proposer=mock_proposer,
            )

    def test_constructor_validates_primary_not_in_agents(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_components: dict[str, list[str]],
        mock_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """Verify constructor raises error when primary not in agents."""
        with pytest.raises(
            MultiAgentValidationError,
            match="primary agent 'validator' not found in agents dict",
        ):
            MultiAgentAdapter(
                agents=mock_agents,
                primary="validator",
                components=mock_components,
                scorer=mock_scorer,
                proposer=mock_proposer,
            )

    def test_constructor_validates_no_scorer_no_schema(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_components: dict[str, list[str]],
        mock_proposer,
    ) -> None:
        """Verify constructor raises error when no scorer and no output_schema."""
        # Primary agent has no output_schema
        with pytest.raises(
            MultiAgentValidationError,
            match="no scorer and primary agent lacks output_schema",
        ):
            MultiAgentAdapter(
                agents=mock_agents,
                primary="generator",
                components=mock_components,
                scorer=None,
                proposer=mock_proposer,
            )

    def test_constructor_accepts_scorer_none_with_output_schema(
        self, mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify constructor accepts None scorer when primary has output_schema."""
        from pydantic import BaseModel

        class OutputSchema(BaseModel):
            result: str

        agents = {
            "generator": LlmAgent(
                name="generator",
                model="gemini-2.0-flash",
                instruction="Generate",
                output_schema=OutputSchema,
            ),
        }
        components = {"generator": ["instruction"]}

        adapter = MultiAgentAdapter(
            agents=agents,
            primary="generator",
            components=components,
            scorer=None,
            proposer=mock_proposer,
        )

        assert adapter.scorer is None
        assert adapter.primary == "generator"

    def test_constructor_validates_unknown_agent_in_components(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """Verify constructor raises ValueError for unknown agent in components."""
        components = {
            "generator": ["instruction"],
            "critic": ["instruction"],
            "unknown_agent": ["instruction"],  # Not in agents dict
        }

        with pytest.raises(ValueError, match="Agent 'unknown_agent' not found"):
            MultiAgentAdapter(
                agents=mock_agents,
                primary="generator",
                components=components,
                scorer=mock_scorer,
                proposer=mock_proposer,
            )

    def test_constructor_validates_agent_missing_from_components(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """Verify constructor raises ValueError for agent missing from components."""
        # Only specify generator, missing critic
        components = {"generator": ["instruction"]}

        with pytest.raises(ValueError, match="missing from components mapping"):
            MultiAgentAdapter(
                agents=mock_agents,
                primary="generator",
                components=components,
                scorer=mock_scorer,
                proposer=mock_proposer,
            )

    def test_constructor_validates_unknown_component_handler(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """Verify constructor raises ValueError for unknown component handler."""
        components = {
            "generator": ["unknown_component"],  # No handler registered
            "critic": ["instruction"],
        }

        with pytest.raises(ValueError, match="No handler registered"):
            MultiAgentAdapter(
                agents=mock_agents,
                primary="generator",
                components=components,
                scorer=mock_scorer,
                proposer=mock_proposer,
            )

    def test_constructor_accepts_empty_component_list(
        self,
        mock_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """Verify constructor accepts empty component list (excludes agent from evolution)."""
        agents = {
            "generator": LlmAgent(
                name="generator", model="gemini-2.0-flash", instruction="Generate"
            ),
            "validator": LlmAgent(
                name="validator", model="gemini-2.0-flash", instruction="Validate"
            ),
        }
        components = {
            "generator": ["instruction"],
            "validator": [],  # Empty list = excluded from evolution
        }

        adapter = MultiAgentAdapter(
            agents=agents,
            primary="generator",
            components=components,
            scorer=mock_scorer,
            proposer=mock_proposer,
        )

        assert adapter.components["validator"] == []


class TestMultiAgentAdapterBuildPipeline:
    """Unit tests for _build_pipeline helper method.

    Note:
        Tests verify agent cloning and SequentialAgent construction with qualified names.
    """

    def test_build_pipeline_clones_agents_with_instructions(
        self, adapter: MultiAgentAdapter
    ) -> None:
        """Verify _build_pipeline clones agents with candidate instructions."""
        # Use qualified names per ADR-012
        candidate = {
            "generator.instruction": "Generate high-quality code",
            "critic.instruction": "Review thoroughly",
        }

        pipeline = adapter._build_pipeline(candidate)

        assert isinstance(pipeline, SequentialAgent)
        assert len(pipeline.sub_agents) == 2

        # Verify cloned agents have new instructions
        generator_clone = next(
            agent for agent in pipeline.sub_agents if agent.name == "generator"
        )
        critic_clone = next(
            agent for agent in pipeline.sub_agents if agent.name == "critic"
        )

        assert generator_clone.instruction == "Generate high-quality code"
        assert critic_clone.instruction == "Review thoroughly"

        # Verify original agents unchanged
        assert adapter.agents["generator"].instruction == "Generate code"
        assert adapter.agents["critic"].instruction == "Review code"

    def test_build_pipeline_uses_original_when_candidate_missing(
        self, adapter: MultiAgentAdapter
    ) -> None:
        """Verify _build_pipeline uses original instruction when candidate key missing."""
        candidate = {
            "generator.instruction": "New instruction",
            # critic.instruction missing
        }

        pipeline = adapter._build_pipeline(candidate)

        generator_clone = next(
            agent for agent in pipeline.sub_agents if agent.name == "generator"
        )
        critic_clone = next(
            agent for agent in pipeline.sub_agents if agent.name == "critic"
        )

        assert generator_clone.instruction == "New instruction"
        assert critic_clone.instruction == "Review code"  # Original unchanged

    def test_build_pipeline_creates_sequential_agent(
        self, adapter: MultiAgentAdapter
    ) -> None:
        """Verify _build_pipeline returns SequentialAgent with correct name."""
        candidate = {}

        pipeline = adapter._build_pipeline(candidate)

        assert isinstance(pipeline, SequentialAgent)
        assert pipeline.name == "MultiAgentPipeline"
        assert len(pipeline.sub_agents) == 2


class TestMultiAgentAdapterProposerDelegation:
    """Unit tests for MultiAgentAdapter proposer delegation (Phase 4: User Story 2).

    Note:
        Tests verify that MultiAgentAdapter delegates to AsyncReflectiveMutationProposer
        for generating instruction mutations via LLM reflection.
    """

    @pytest.mark.asyncio
    async def test_constructor_accepts_proposer_parameter(
        self, adapter: MultiAgentAdapter, mock_proposer
    ) -> None:
        """Verify constructor accepts proposer parameter."""
        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        )
        scorer = MockScorer()

        adapter_with_proposer = MultiAgentAdapter(
            agents={"generator": generator},
            primary="generator",
            components={"generator": ["instruction"]},
            scorer=scorer,
            proposer=mock_proposer,
        )

        assert adapter_with_proposer._proposer is mock_proposer

    @pytest.mark.asyncio
    async def test_propose_new_texts_delegates_to_proposer(
        self, adapter: MultiAgentAdapter, mock_proposer
    ) -> None:
        """Verify propose_new_texts delegates to proposer."""
        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        )
        scorer = MockScorer()

        adapter_with_proposer = MultiAgentAdapter(
            agents={"generator": generator},
            primary="generator",
            components={"generator": ["instruction"]},
            scorer=scorer,
            proposer=mock_proposer,
        )

        candidate = {"generator.instruction": "Be helpful"}
        reflective_dataset = {
            "generator.instruction": [
                {
                    "Inputs": {"input": "test"},
                    "Generated Outputs": "output",
                    "Feedback": "score: 0.8 | needs improvement",
                }
            ]
        }
        components_to_update = ["generator.instruction"]

        # Configure mock to return a proposal
        mock_proposer.propose.return_value = {"generator.instruction": "improved text"}

        result = await adapter_with_proposer.propose_new_texts(
            candidate, reflective_dataset, components_to_update
        )

        # Verify proposer was called
        mock_proposer.propose.assert_called_once_with(
            candidate, reflective_dataset, components_to_update
        )

        # Verify result contains proposed text
        assert result["generator.instruction"] == "improved text"

    @pytest.mark.asyncio
    async def test_custom_proposer_is_used(
        self, adapter: MultiAgentAdapter, mock_proposer
    ) -> None:
        """Verify custom proposer is used instead of default."""
        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        )
        scorer = MockScorer()

        adapter_with_proposer = MultiAgentAdapter(
            agents={"generator": generator},
            primary="generator",
            components={"generator": ["instruction"]},
            scorer=scorer,
            proposer=mock_proposer,
        )

        # Verify custom proposer is stored
        assert adapter_with_proposer._proposer is mock_proposer

        # Verify custom proposer is called
        candidate = {"generator.instruction": "Be helpful"}
        reflective_dataset = {
            "generator.instruction": [
                {
                    "Inputs": {"input": "test"},
                    "Generated Outputs": "output",
                    "Feedback": "score: 0.8",
                }
            ]
        }
        mock_proposer.propose.return_value = {"generator.instruction": "custom result"}

        result = await adapter_with_proposer.propose_new_texts(
            candidate, reflective_dataset, ["generator.instruction"]
        )

        assert result["generator.instruction"] == "custom result"
        mock_proposer.propose.assert_called_once()

    @pytest.mark.asyncio
    async def test_propose_new_texts_fallback_on_none(
        self, adapter: MultiAgentAdapter, mock_proposer
    ) -> None:
        """Verify fallback to unchanged values when proposer returns None."""
        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        )
        scorer = MockScorer()

        adapter_with_proposer = MultiAgentAdapter(
            agents={"generator": generator},
            primary="generator",
            components={"generator": ["instruction"]},
            scorer=scorer,
            proposer=mock_proposer,
        )

        candidate = {"generator.instruction": "original text"}
        reflective_dataset = {}  # Empty dataset
        components_to_update = ["generator.instruction"]

        # Configure mock to return None (empty dataset case)
        mock_proposer.propose.return_value = None

        result = await adapter_with_proposer.propose_new_texts(
            candidate, reflective_dataset, components_to_update
        )

        # Verify fallback to original candidate value
        assert result["generator.instruction"] == "original text"

    @pytest.mark.asyncio
    async def test_propose_new_texts_merges_partial_result(
        self, adapter: MultiAgentAdapter, mock_proposer
    ) -> None:
        """Verify partial results are merged with candidate values."""
        agents = {
            "generator": LlmAgent(
                name="generator",
                model="gemini-2.0-flash",
                instruction="Generate code",
            ),
            "critic": LlmAgent(
                name="critic", model="gemini-2.0-flash", instruction="Review"
            ),
        }
        scorer = MockScorer()

        adapter_with_proposer = MultiAgentAdapter(
            agents=agents,
            primary="generator",
            components={"generator": ["instruction"], "critic": ["instruction"]},
            scorer=scorer,
            proposer=mock_proposer,
        )

        candidate = {
            "generator.instruction": "original instruction",
            "critic.instruction": "original critic",
        }
        reflective_dataset = {
            "generator.instruction": [
                {
                    "Inputs": {"input": "test"},
                    "Generated Outputs": "output",
                    "Feedback": "score: 0.8",
                }
            ]
        }
        components_to_update = ["generator.instruction", "critic.instruction"]

        # Proposer only returns result for one component
        mock_proposer.propose.return_value = {
            "generator.instruction": "improved instruction"
        }

        result = await adapter_with_proposer.propose_new_texts(
            candidate, reflective_dataset, components_to_update
        )

        # Verify merged result
        assert result["generator.instruction"] == "improved instruction"
        assert result["critic.instruction"] == "original critic"

    @pytest.mark.asyncio
    async def test_propose_new_texts_propagates_proposer_exception(
        self, adapter: MultiAgentAdapter, mock_proposer
    ) -> None:
        """Verify proposer exceptions propagate to caller."""
        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        )
        scorer = MockScorer()

        adapter_with_proposer = MultiAgentAdapter(
            agents={"generator": generator},
            primary="generator",
            components={"generator": ["instruction"]},
            scorer=scorer,
            proposer=mock_proposer,
        )

        candidate = {"generator.instruction": "original"}
        reflective_dataset = {"generator.instruction": [{"Feedback": "test"}]}
        components_to_update = ["generator.instruction"]

        # Configure mock to raise exception
        mock_proposer.propose.side_effect = ValueError("Proposer error")

        # Verify exception propagates
        with pytest.raises(ValueError, match="Proposer error"):
            await adapter_with_proposer.propose_new_texts(
                candidate, reflective_dataset, components_to_update
            )


@pytest.mark.asyncio
class TestADR009ExceptionWrapping:
    """Unit tests for ADR-009 compliant exception wrapping.

    These tests verify that exceptions are wrapped in EvaluationError
    per ADR-009 while preserving batch resilience (graceful degradation).
    """

    async def test_exception_wrapped_in_evaluation_error(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_components: dict[str, list[str]],
        mock_scorer: MockScorer,
        mock_proposer,
        mocker,
    ) -> None:
        """Verify exceptions are wrapped in EvaluationError per ADR-009."""
        from unittest.mock import MagicMock

        mock_executor = MagicMock()
        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            components=mock_components,
            scorer=mock_scorer,
            proposer=mock_proposer,
            executor=mock_executor,
        )

        batch = [{"input": "test"}]
        candidate = {"generator.instruction": "Test"}

        # Configure executor to raise an exception
        mock_executor.execute_agent = mocker.AsyncMock(
            side_effect=RuntimeError("Original error")
        )

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should still return results (batch resilience)
        assert len(result.outputs) == 1
        assert result.outputs[0] == ""
        assert result.scores[0] == 0.0

        # Trajectory error should contain wrapped EvaluationError format
        assert result.trajectories is not None
        error_str = result.trajectories[0].error
        assert error_str is not None
        assert "Example 0 evaluation failed" in error_str
        assert "caused by" in error_str
        assert "Original error" in error_str

    async def test_exception_preserves_example_index_context(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_components: dict[str, list[str]],
        mock_scorer: MockScorer,
        mock_proposer,
        mocker,
    ) -> None:
        """Verify wrapped exception includes example_index context."""
        from unittest.mock import MagicMock

        from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

        mock_executor = MagicMock()
        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            components=mock_components,
            scorer=mock_scorer,
            proposer=mock_proposer,
            executor=mock_executor,
        )

        batch = [
            {"input": "test_0"},
            {"input": "test_1"},
            {"input": "test_2"},
        ]
        candidate = {"generator.instruction": "Test"}

        # Fail only the second example
        mock_executor.execute_agent = mocker.AsyncMock(
            side_effect=[
                ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    extracted_value="output_0",
                    session_id="test_0",
                    error_message=None,
                ),
                RuntimeError("Middle failure"),
                ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    extracted_value="output_2",
                    session_id="test_2",
                    error_message=None,
                ),
            ]
        )

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # All results returned (batch resilience)
        assert len(result.outputs) == 3
        assert result.outputs[0] == "output_0"
        assert result.outputs[1] == ""
        assert result.outputs[2] == "output_2"

        # Failed example trajectory contains index
        assert result.trajectories is not None
        error_str = result.trajectories[1].error
        assert error_str is not None
        assert "Example 1 evaluation failed" in error_str
        assert "example_index=1" in error_str

    async def test_batch_continues_after_wrapped_exception(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_components: dict[str, list[str]],
        mock_scorer: MockScorer,
        mock_proposer,
        mocker,
    ) -> None:
        """Verify batch processing continues after exception (graceful degradation)."""
        from unittest.mock import MagicMock

        from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

        mock_executor = MagicMock()
        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            components=mock_components,
            scorer=mock_scorer,
            proposer=mock_proposer,
            executor=mock_executor,
        )

        batch = [
            {"input": "test_0"},
            {"input": "test_1"},
            {"input": "test_2"},
        ]
        candidate = {"generator.instruction": "Test"}

        # First fails, rest succeed
        mock_executor.execute_agent = mocker.AsyncMock(
            side_effect=[
                ValueError("First failure"),
                ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    extracted_value="output_1",
                    session_id="test_1",
                    error_message=None,
                ),
                ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    extracted_value="output_2",
                    session_id="test_2",
                    error_message=None,
                ),
            ]
        )

        result = await adapter.evaluate(batch, candidate)

        # All results returned despite first failure
        assert len(result.outputs) == 3
        assert len(result.scores) == 3

        # First failed, others succeeded
        assert result.outputs[0] == ""
        assert result.scores[0] == 0.0
        assert result.outputs[1] == "output_1"
        assert result.outputs[2] == "output_2"
