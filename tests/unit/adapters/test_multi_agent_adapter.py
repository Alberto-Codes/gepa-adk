"""Unit tests for MultiAgentAdapter implementation.

These tests verify the business logic of MultiAgentAdapter using mocked dependencies
to isolate the adapter behavior from external ADK services.

Note:
    Unit tests use mocked ADK agents and runners to avoid real API calls.
    Integration tests (in tests/integration/) use real ADK services.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent, SequentialAgent

from gepa_adk.adapters import MultiAgentAdapter
from gepa_adk.domain.exceptions import MultiAgentValidationError

pytestmark = pytest.mark.unit


class MockScorer:
    """Mock scorer that returns predictable scores.

    Properly implements the Scorer protocol with the correct signature:
    - score(input_text, output, expected) -> tuple[float, dict]
    - async_score(input_text, output, expected) -> tuple[float, dict]
    """

    def __init__(self, score_value: float = 0.8) -> None:
        """Initialize mock scorer with fixed score value."""
        self.score_value = score_value
        self.score_calls: list[tuple[str, str, str | None]] = []

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Record call and return fixed score with empty metadata."""
        self.score_calls.append((input_text, output, expected))
        return (self.score_value, {})

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Record call and return fixed score with empty metadata."""
        self.score_calls.append((input_text, output, expected))
        return (self.score_value, {})


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
def adapter(mock_agents: list[LlmAgent], mock_scorer: MockScorer) -> MultiAgentAdapter:
    """Create a MultiAgentAdapter for testing."""
    return MultiAgentAdapter(
        agents=mock_agents,
        primary="generator",
        scorer=mock_scorer,
    )


class TestMultiAgentAdapterConstructor:
    """Unit tests for MultiAgentAdapter constructor (Phase 2: Foundational).

    Note:
        Tests verify validation logic for agents, primary, and scorer parameters.
    """

    def test_constructor_accepts_valid_agents(
        self, mock_agents: list[LlmAgent], mock_scorer: MockScorer
    ) -> None:
        """Verify constructor accepts valid agents list."""
        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            scorer=mock_scorer,
        )

        assert len(adapter.agents) == 2
        assert adapter.primary == "generator"

    def test_constructor_validates_empty_agents_list(
        self, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor raises MultiAgentValidationError for empty list."""
        with pytest.raises(
            MultiAgentValidationError, match="agents list cannot be empty"
        ):
            MultiAgentAdapter(
                agents=[],
                primary="generator",
                scorer=mock_scorer,
            )

    def test_constructor_validates_primary_not_in_agents(
        self, mock_agents: list[LlmAgent], mock_scorer: MockScorer
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
            )

    def test_constructor_validates_duplicate_agent_names(
        self, mock_scorer: MockScorer
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
            )

    def test_constructor_validates_no_scorer_no_schema(
        self, mock_agents: list[LlmAgent]
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
            )

    def test_constructor_accepts_scorer_none_with_output_schema(
        self, mock_scorer: MockScorer
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
