"""Unit tests for evolve_workflow() round_robin functionality.

These tests verify the behavior of the round_robin parameter and components
override in evolve_workflow() using mocks to avoid requiring actual ADK
agent execution or LLM API calls.

Note:
    These tests mock evolve_group to verify that evolve_workflow correctly
    builds the components dict based on round_robin flag.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from google.adk.agents import LlmAgent, SequentialAgent
from pydantic import BaseModel, Field

from gepa_adk import evolve_workflow
from gepa_adk.domain.exceptions import WorkflowEvolutionError
from gepa_adk.domain.models import MultiAgentEvolutionResult

pytestmark = pytest.mark.unit


class CodeOutput(BaseModel):
    """Schema for code generation output."""

    code: str = Field(description="The generated code")
    score: float = Field(ge=0.0, le=1.0, description="Quality score")


@pytest.fixture
def three_agent_workflow() -> SequentialAgent:
    """Create a SequentialAgent with three LlmAgents for testing."""
    generator = LlmAgent(
        name="generator",
        model="gemini-2.5-flash",
        instruction="Generate code",
    )
    refiner = LlmAgent(
        name="refiner",
        model="gemini-2.5-flash",
        instruction="Refine the code",
    )
    writer = LlmAgent(
        name="writer",
        model="gemini-2.5-flash",
        instruction="Write documentation",
        output_schema=CodeOutput,
    )
    return SequentialAgent(
        name="Pipeline",
        sub_agents=[generator, refiner, writer],
    )


@pytest.fixture
def simple_trainset() -> list[dict[str, str]]:
    """Create simple training set for evolution."""
    return [
        {"input": "Create a function", "expected": "def func(): pass"},
    ]


@pytest.fixture
def mock_evolution_result() -> MultiAgentEvolutionResult:
    """Create a mock MultiAgentEvolutionResult for testing."""
    return MultiAgentEvolutionResult(
        evolved_components={
            "generator.instruction": "Evolved generator instruction",
            "refiner.instruction": "Evolved refiner instruction",
            "writer.instruction": "Evolved writer instruction",
        },
        original_score=0.5,
        final_score=0.8,
        primary_agent="writer",
        iteration_history=[],
        total_iterations=1,
    )


class TestEvolveWorkflowValidation:
    """Tests for evolve_workflow() input validation and error guards."""

    @pytest.mark.asyncio
    async def test_evolve_workflow_raises_on_no_llm_agents(
        self,
        simple_trainset: list[dict[str, str]],
    ) -> None:
        """Verify WorkflowEvolutionError when workflow contains no LlmAgents."""
        workflow = SequentialAgent(name="EmptyPipeline", sub_agents=[])

        with pytest.raises(
            WorkflowEvolutionError, match="No LlmAgents found"
        ) as exc_info:
            await evolve_workflow(
                workflow=workflow,
                trainset=simple_trainset,
            )

        assert exc_info.value.workflow_name == "EmptyPipeline"


class TestEvolveWorkflowDefaultBehavior:
    """Tests for evolve_workflow() default behavior (evolve first agent only)."""

    @pytest.mark.asyncio
    async def test_evolve_workflow_default_evolves_first_agent_only(
        self,
        three_agent_workflow: SequentialAgent,
        simple_trainset: list[dict[str, str]],
        mock_evolution_result: MultiAgentEvolutionResult,
    ) -> None:
        """Default behavior evolves only the first agent across all iterations."""
        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = mock_evolution_result

            await evolve_workflow(
                workflow=three_agent_workflow,
                trainset=simple_trainset,
            )

            # Verify evolve_group was called
            mock_evolve_group.assert_called_once()

            # Get the components argument passed to evolve_group
            call_kwargs = mock_evolve_group.call_args.kwargs
            components = call_kwargs["components"]

            # Verify only generator has instruction to evolve
            assert components["generator"] == ["instruction"]
            # Other agents should have empty lists (excluded from evolution)
            assert components["refiner"] == []
            assert components["writer"] == []

    @pytest.mark.asyncio
    async def test_evolve_workflow_default_with_single_agent(
        self,
        simple_trainset: list[dict[str, str]],
        mock_evolution_result: MultiAgentEvolutionResult,
    ) -> None:
        """Default behavior with single agent evolves that agent."""
        single_agent = LlmAgent(
            name="only_agent",
            model="gemini-2.5-flash",
            instruction="Do something",
            output_schema=CodeOutput,
        )
        workflow = SequentialAgent(name="SinglePipeline", sub_agents=[single_agent])

        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = mock_evolution_result

            await evolve_workflow(
                workflow=workflow,
                trainset=simple_trainset,
            )

            call_kwargs = mock_evolve_group.call_args.kwargs
            components = call_kwargs["components"]

            # Single agent should be evolved
            assert components["only_agent"] == ["instruction"]


class TestEvolveWorkflowRoundRobin:
    """Tests for evolve_workflow() with round_robin=True."""

    @pytest.mark.asyncio
    async def test_evolve_workflow_round_robin_evolves_all_agents(
        self,
        three_agent_workflow: SequentialAgent,
        simple_trainset: list[dict[str, str]],
        mock_evolution_result: MultiAgentEvolutionResult,
    ) -> None:
        """round_robin=True evolves all agents in the workflow."""
        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = mock_evolution_result

            await evolve_workflow(
                workflow=three_agent_workflow,
                trainset=simple_trainset,
                round_robin=True,
            )

            # Verify evolve_group was called
            mock_evolve_group.assert_called_once()

            # Get the components argument passed to evolve_group
            call_kwargs = mock_evolve_group.call_args.kwargs
            components = call_kwargs["components"]

            # Verify all agents have instruction to evolve
            assert components["generator"] == ["instruction"]
            assert components["refiner"] == ["instruction"]
            assert components["writer"] == ["instruction"]

    @pytest.mark.asyncio
    async def test_evolve_workflow_round_robin_false_matches_default(
        self,
        three_agent_workflow: SequentialAgent,
        simple_trainset: list[dict[str, str]],
        mock_evolution_result: MultiAgentEvolutionResult,
    ) -> None:
        """round_robin=False is equivalent to default behavior."""
        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = mock_evolution_result

            await evolve_workflow(
                workflow=three_agent_workflow,
                trainset=simple_trainset,
                round_robin=False,
            )

            call_kwargs = mock_evolve_group.call_args.kwargs
            components = call_kwargs["components"]

            # Only first agent should be evolved
            assert components["generator"] == ["instruction"]
            assert components["refiner"] == []
            assert components["writer"] == []


class TestEvolveWorkflowComponentsOverride:
    """Tests for evolve_workflow() with explicit components parameter."""

    @pytest.mark.asyncio
    async def test_evolve_workflow_components_takes_precedence_over_round_robin(
        self,
        three_agent_workflow: SequentialAgent,
        simple_trainset: list[dict[str, str]],
        mock_evolution_result: MultiAgentEvolutionResult,
    ) -> None:
        """Explicit components parameter overrides round_robin flag."""
        explicit_components = {
            "generator": ["instruction"],
            "writer": ["instruction"],
            "refiner": [],  # Excluded
        }

        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = mock_evolution_result

            await evolve_workflow(
                workflow=three_agent_workflow,
                trainset=simple_trainset,
                round_robin=True,  # Should be ignored
                components=explicit_components,
            )

            call_kwargs = mock_evolve_group.call_args.kwargs
            components = call_kwargs["components"]

            # Should use explicit components, not round_robin
            assert components == explicit_components

    @pytest.mark.asyncio
    async def test_evolve_workflow_components_override_excludes_agents(
        self,
        three_agent_workflow: SequentialAgent,
        simple_trainset: list[dict[str, str]],
        mock_evolution_result: MultiAgentEvolutionResult,
    ) -> None:
        """Explicit components can exclude specific agents from evolution."""
        # Only evolve generator, exclude refiner and writer
        explicit_components = {
            "generator": ["instruction"],
            "refiner": [],
            "writer": [],
        }

        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = mock_evolution_result

            await evolve_workflow(
                workflow=three_agent_workflow,
                trainset=simple_trainset,
                components=explicit_components,
            )

            call_kwargs = mock_evolve_group.call_args.kwargs
            components = call_kwargs["components"]

            assert components["generator"] == ["instruction"]
            assert components["refiner"] == []
            assert components["writer"] == []

    @pytest.mark.asyncio
    async def test_evolve_workflow_components_with_round_robin_false(
        self,
        three_agent_workflow: SequentialAgent,
        simple_trainset: list[dict[str, str]],
        mock_evolution_result: MultiAgentEvolutionResult,
    ) -> None:
        """Explicit components works with round_robin=False."""
        explicit_components = {
            "generator": [],  # Excluded
            "refiner": ["instruction"],
            "writer": ["instruction"],
        }

        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = mock_evolution_result

            await evolve_workflow(
                workflow=three_agent_workflow,
                trainset=simple_trainset,
                round_robin=False,
                components=explicit_components,
            )

            call_kwargs = mock_evolve_group.call_args.kwargs
            components = call_kwargs["components"]

            # Should use explicit components
            assert components == explicit_components
