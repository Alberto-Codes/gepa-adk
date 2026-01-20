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
def mock_agents() -> list[LlmAgent]:
    """Create mock ADK agents for testing."""
    return [
        LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        ),
        LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review code",
        ),
    ]


@pytest.fixture
def mock_scorer() -> MockScorer:
    """Create a mock scorer."""
    return MockScorer(score_value=0.85)


@pytest.fixture
def adapter(
    mock_agents: list[LlmAgent], mock_scorer: MockScorer, mock_proposer
) -> MultiAgentAdapter:
    """Create a MultiAgentAdapter for testing."""
    return MultiAgentAdapter(
        agents=mock_agents,
        primary="generator",
        scorer=mock_scorer,
        proposer=mock_proposer,
    )


class TestMultiAgentAdapterConstructor:
    """Unit tests for MultiAgentAdapter constructor (Phase 2: Foundational).

    Note:
        Tests verify validation logic for agents, primary, and scorer parameters.
    """

    def test_constructor_accepts_valid_agents(
        self, mock_agents: list[LlmAgent], mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify constructor accepts valid agents list."""
        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            scorer=mock_scorer,
            proposer=mock_proposer,
        )

        assert len(adapter.agents) == 2
        assert adapter.primary == "generator"

    def test_constructor_validates_empty_agents_list(
        self, mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify constructor raises MultiAgentValidationError for empty list."""
        with pytest.raises(
            MultiAgentValidationError, match="agents list cannot be empty"
        ):
            MultiAgentAdapter(
                agents=[],
                primary="generator",
                scorer=mock_scorer,
                proposer=mock_proposer,
            )

    def test_constructor_validates_primary_not_in_agents(
        self, mock_agents: list[LlmAgent], mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify constructor raises error when primary not in agents."""
        with pytest.raises(
            MultiAgentValidationError,
            match="primary agent 'validator' not found in agents list",
        ):
            MultiAgentAdapter(
                agents=mock_agents,
                primary="validator",
                scorer=mock_scorer,
                proposer=mock_proposer,
            )

    def test_constructor_validates_duplicate_agent_names(
        self, mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify constructor raises error for duplicate agent names."""
        agents = [
            LlmAgent(name="generator", model="gemini-2.0-flash"),
            LlmAgent(name="generator", model="gemini-2.0-flash"),  # Duplicate
        ]

        with pytest.raises(
            MultiAgentValidationError, match="duplicate agent name: 'generator'"
        ):
            MultiAgentAdapter(
                agents=agents,
                primary="generator",
                scorer=mock_scorer,
                proposer=mock_proposer,
            )

    def test_constructor_validates_no_scorer_no_schema(
        self, mock_agents: list[LlmAgent], mock_proposer
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

        agents = [
            LlmAgent(
                name="generator",
                model="gemini-2.0-flash",
                instruction="Generate",
                output_schema=OutputSchema,
            ),
        ]

        adapter = MultiAgentAdapter(
            agents=agents,
            primary="generator",
            scorer=None,
            proposer=mock_proposer,
        )

        assert adapter.scorer is None
        assert adapter.primary == "generator"


class TestMultiAgentAdapterBuildPipeline:
    """Unit tests for _build_pipeline helper method.

    Note:
        Tests verify agent cloning and SequentialAgent construction.
    """

    def test_build_pipeline_clones_agents_with_instructions(
        self, adapter: MultiAgentAdapter
    ) -> None:
        """Verify _build_pipeline clones agents with candidate instructions."""
        candidate = {
            "generator_instruction": "Generate high-quality code",
            "critic_instruction": "Review thoroughly",
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
        assert adapter.agents[0].instruction == "Generate code"
        assert adapter.agents[1].instruction == "Review code"

    def test_build_pipeline_uses_original_when_candidate_missing(
        self, adapter: MultiAgentAdapter
    ) -> None:
        """Verify _build_pipeline uses original instruction when candidate key missing."""
        candidate = {
            "generator_instruction": "New instruction",
            # critic_instruction missing
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
            agents=[generator],
            primary="generator",
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
            agents=[generator],
            primary="generator",
            scorer=scorer,
            proposer=mock_proposer,
        )

        candidate = {"generator_instruction": "Be helpful"}
        reflective_dataset = {
            "generator_instruction": [
                {
                    "Inputs": {"input": "test"},
                    "Generated Outputs": "output",
                    "Feedback": "score: 0.8 | needs improvement",
                }
            ]
        }
        components_to_update = ["generator_instruction"]

        # Configure mock to return a proposal
        mock_proposer.propose.return_value = {"generator_instruction": "improved text"}

        result = await adapter_with_proposer.propose_new_texts(
            candidate, reflective_dataset, components_to_update
        )

        # Verify proposer was called
        mock_proposer.propose.assert_called_once_with(
            candidate, reflective_dataset, components_to_update
        )

        # Verify result contains proposed text
        assert result["generator_instruction"] == "improved text"

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
            agents=[generator],
            primary="generator",
            scorer=scorer,
            proposer=mock_proposer,
        )

        # Verify custom proposer is stored
        assert adapter_with_proposer._proposer is mock_proposer

        # Verify custom proposer is called
        candidate = {"generator_instruction": "Be helpful"}
        reflective_dataset = {
            "generator_instruction": [
                {
                    "Inputs": {"input": "test"},
                    "Generated Outputs": "output",
                    "Feedback": "score: 0.8",
                }
            ]
        }
        mock_proposer.propose.return_value = {"generator_instruction": "custom result"}

        result = await adapter_with_proposer.propose_new_texts(
            candidate, reflective_dataset, ["generator_instruction"]
        )

        assert result["generator_instruction"] == "custom result"
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
            agents=[generator],
            primary="generator",
            scorer=scorer,
            proposer=mock_proposer,
        )

        candidate = {"generator_instruction": "original text"}
        reflective_dataset = {}  # Empty dataset
        components_to_update = ["generator_instruction"]

        # Configure mock to return None (empty dataset case)
        mock_proposer.propose.return_value = None

        result = await adapter_with_proposer.propose_new_texts(
            candidate, reflective_dataset, components_to_update
        )

        # Verify fallback to original candidate value
        assert result["generator_instruction"] == "original text"

    @pytest.mark.asyncio
    async def test_propose_new_texts_merges_partial_result(
        self, adapter: MultiAgentAdapter, mock_proposer
    ) -> None:
        """Verify partial results are merged with candidate values."""
        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        )
        scorer = MockScorer()

        adapter_with_proposer = MultiAgentAdapter(
            agents=[generator],
            primary="generator",
            scorer=scorer,
            proposer=mock_proposer,
        )

        candidate = {
            "generator_instruction": "original instruction",
            "critic_instruction": "original critic",
        }
        reflective_dataset = {
            "generator_instruction": [
                {
                    "Inputs": {"input": "test"},
                    "Generated Outputs": "output",
                    "Feedback": "score: 0.8",
                }
            ]
        }
        components_to_update = ["generator_instruction", "critic_instruction"]

        # Proposer only returns result for one component
        mock_proposer.propose.return_value = {
            "generator_instruction": "improved instruction"
        }

        result = await adapter_with_proposer.propose_new_texts(
            candidate, reflective_dataset, components_to_update
        )

        # Verify merged result
        assert result["generator_instruction"] == "improved instruction"
        assert result["critic_instruction"] == "original critic"

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
            agents=[generator],
            primary="generator",
            scorer=scorer,
            proposer=mock_proposer,
        )

        candidate = {"generator_instruction": "original"}
        reflective_dataset = {"generator_instruction": [{"Feedback": "test"}]}
        components_to_update = ["generator_instruction"]

        # Configure mock to raise exception
        mock_proposer.propose.side_effect = ValueError("Proposer error")

        # Verify exception propagates
        with pytest.raises(ValueError, match="Proposer error"):
            await adapter_with_proposer.propose_new_texts(
                candidate, reflective_dataset, components_to_update
            )
