"""Integration tests for multi-agent per-agent component routing.

These tests verify end-to-end multi-agent evolution with per-agent component
configuration, testing the routing of candidates to correct agents.

Note:
    These tests require API keys and may take significant time to run.
    They are skipped by default in local development.

Test IDs: T028, T029
User Story: US1 - Route Components to Correct Agents
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from gepa_adk import MultiAgentEvolutionResult, evolve_group
from gepa_adk.domain.models import EvolutionConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.api,
    pytest.mark.requires_gemini,
]


class CodeOutput(BaseModel):
    """Schema for code generation output."""

    code: str = Field(description="The generated code")
    explanation: str = Field(description="Explanation of the code")


class ReviewOutput(BaseModel):
    """Schema for code review output."""

    feedback: str = Field(description="Review feedback")
    score: float = Field(ge=0.0, le=1.0, description="Quality score")


@pytest.fixture
def per_agent_components_setup() -> dict[str, Any]:
    """Create agents with per-agent component configuration.

    Returns dict with agents, components, and trainset for testing
    multi-agent component routing.
    """
    agents = {
        "generator": LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate a simple Python function.",
            output_key="generated_code",
        ),
        "reviewer": LlmAgent(
            name="reviewer",
            model="gemini-2.0-flash",
            instruction="Review the code: {generated_code}",
            output_schema=ReviewOutput,
        ),
    }

    # Per-agent components: generator evolves instruction,
    # reviewer also evolves instruction
    components = {
        "generator": ["instruction"],
        "reviewer": ["instruction"],
    }

    trainset = [
        {
            "input": "Create a function that adds two numbers",
            "expected": "def add(a, b): return a + b",
        },
        {
            "input": "Create a function that multiplies two numbers",
            "expected": "def multiply(a, b): return a * b",
        },
    ]

    return {
        "agents": agents,
        "components": components,
        "trainset": trainset,
    }


@pytest.fixture
def three_agent_setup() -> dict[str, Any]:
    """Create three agents with different component types.

    Tests the routing of candidates across three agents, each with
    different component configurations.
    """
    agents = {
        "planner": LlmAgent(
            name="planner",
            model="gemini-2.0-flash",
            instruction="Plan the solution approach.",
            output_key="plan",
        ),
        "implementer": LlmAgent(
            name="implementer",
            model="gemini-2.0-flash",
            instruction="Implement based on plan: {plan}",
            output_key="implementation",
        ),
        "validator": LlmAgent(
            name="validator",
            model="gemini-2.0-flash",
            instruction="Validate implementation: {implementation}",
            output_schema=ReviewOutput,
        ),
    }

    # Different components for each agent
    components = {
        "planner": ["instruction"],
        "implementer": ["instruction"],
        "validator": ["instruction"],
    }

    trainset = [
        {
            "input": "Create a function to calculate factorial",
            "expected": "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
        },
    ]

    return {
        "agents": agents,
        "components": components,
        "trainset": trainset,
    }


class TestMultiAgentPerAgentComponents:
    """Integration tests for per-agent component routing (T028)."""

    @pytest.mark.asyncio
    async def test_evolve_group_with_per_agent_components(
        self, per_agent_components_setup: dict[str, Any]
    ) -> None:
        """T028: Multi-agent evolution with per-agent component configuration.

        Verifies that:
        1. evolve_group accepts per-agent components configuration
        2. Evolved components use qualified names (agent.component format)
        3. Both agents' instructions are evolved
        """
        agents = per_agent_components_setup["agents"]
        components = per_agent_components_setup["components"]
        trainset = per_agent_components_setup["trainset"]

        result = await evolve_group(
            agents=agents,
            primary="reviewer",
            trainset=trainset,
            components=components,
            config=EvolutionConfig(max_iterations=2),
        )

        assert isinstance(result, MultiAgentEvolutionResult)

        # Verify qualified names in evolved_components
        assert "generator.instruction" in result.evolved_components
        assert "reviewer.instruction" in result.evolved_components

        # Verify values are strings (the evolved instructions)
        assert isinstance(result.evolved_components["generator.instruction"], str)
        assert isinstance(result.evolved_components["reviewer.instruction"], str)

        # Verify primary agent is set correctly
        assert result.primary_agent == "reviewer"

    @pytest.mark.asyncio
    async def test_evolve_group_excludes_agent_from_evolution(
        self, per_agent_components_setup: dict[str, Any]
    ) -> None:
        """T028: Agent with empty component list excluded from evolution.

        Verifies that specifying an empty component list for an agent
        excludes that agent from evolution while still including others.
        """
        agents = per_agent_components_setup["agents"]
        trainset = per_agent_components_setup["trainset"]

        # Only generator evolves, reviewer is excluded
        components = {
            "generator": ["instruction"],
            "reviewer": [],  # Empty list excludes from evolution
        }

        result = await evolve_group(
            agents=agents,
            primary="reviewer",
            trainset=trainset,
            components=components,
            config=EvolutionConfig(max_iterations=2),
        )

        assert isinstance(result, MultiAgentEvolutionResult)

        # Generator should have evolved instruction
        assert "generator.instruction" in result.evolved_components

        # Reviewer should not have any evolved components
        reviewer_components = [
            k for k in result.evolved_components if k.startswith("reviewer.")
        ]
        assert len(reviewer_components) == 0


class TestThreeAgentComponentRouting:
    """Integration tests for three agents with different component types (T029)."""

    @pytest.mark.asyncio
    async def test_three_agents_different_components(
        self, three_agent_setup: dict[str, Any]
    ) -> None:
        """T029: Three agents with different component configurations.

        Verifies that:
        1. All three agents can be evolved together
        2. Each agent's components are routed correctly
        3. Qualified names follow agent.component format
        """
        agents = three_agent_setup["agents"]
        components = three_agent_setup["components"]
        trainset = three_agent_setup["trainset"]

        result = await evolve_group(
            agents=agents,
            primary="validator",
            trainset=trainset,
            components=components,
            config=EvolutionConfig(max_iterations=2),
        )

        assert isinstance(result, MultiAgentEvolutionResult)

        # Verify all three agents have evolved components
        assert "planner.instruction" in result.evolved_components
        assert "implementer.instruction" in result.evolved_components
        assert "validator.instruction" in result.evolved_components

        # Verify agent_names computed property
        assert len(result.agent_names) == 3
        assert "planner" in result.agent_names
        assert "implementer" in result.agent_names
        assert "validator" in result.agent_names

    @pytest.mark.asyncio
    async def test_three_agents_selective_evolution(
        self, three_agent_setup: dict[str, Any]
    ) -> None:
        """T029: Three agents with selective component evolution.

        Verifies that only specified agents/components are evolved
        when some agents have empty component lists.
        """
        agents = three_agent_setup["agents"]
        trainset = three_agent_setup["trainset"]

        # Only planner and validator evolve, implementer is excluded
        components = {
            "planner": ["instruction"],
            "implementer": [],  # Excluded from evolution
            "validator": ["instruction"],
        }

        result = await evolve_group(
            agents=agents,
            primary="validator",
            trainset=trainset,
            components=components,
            config=EvolutionConfig(max_iterations=2),
        )

        assert isinstance(result, MultiAgentEvolutionResult)

        # Planner and validator should have evolved instructions
        assert "planner.instruction" in result.evolved_components
        assert "validator.instruction" in result.evolved_components

        # Implementer should not have any evolved components
        implementer_components = [
            k for k in result.evolved_components if k.startswith("implementer.")
        ]
        assert len(implementer_components) == 0
