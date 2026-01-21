"""Integration tests for workflow evolution.

These tests verify end-to-end workflow evolution with real ADK agents.
Tests are marked as slow and integration since they make real LLM API calls.

Note:
    These tests require API keys and may take significant time to run.
    They are skipped by default in local development.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from pydantic import BaseModel, Field

from gepa_adk import MultiAgentEvolutionResult, evolve_workflow

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


@pytest.fixture
def sequential_workflow() -> SequentialAgent:
    """Create a SequentialAgent workflow with multiple LlmAgents."""
    agent1 = LlmAgent(
        name="generator",
        model="gemini-2.0-flash",
        instruction="Generate a simple Python function.",
        output_key="generated_code",
        output_schema=CodeOutput,
    )
    agent2 = LlmAgent(
        name="critic",
        model="gemini-2.0-flash",
        instruction="Review the code in {generated_code} and provide feedback.",
    )
    agent3 = LlmAgent(
        name="refactorer",
        model="gemini-2.0-flash",
        instruction="Refactor the code based on {generated_code}.",
        output_schema=CodeOutput,  # Primary agent needs output_schema for scoring
    )
    return SequentialAgent(
        name="CodePipeline",
        sub_agents=[agent1, agent2, agent3],
    )


@pytest.fixture
def simple_trainset() -> list[dict[str, Any]]:
    """Create simple training set for evolution."""
    return [
        {
            "input": "Create a function that adds two numbers",
            "expected": "def add(a, b): return a + b",
        },
    ]


@pytest.mark.asyncio
async def test_evolve_workflow_with_sequential_agent(
    sequential_workflow: SequentialAgent, simple_trainset: list[dict[str, Any]]
) -> None:
    """End-to-end: evolve_workflow() evolves all LlmAgents in SequentialAgent."""
    from gepa_adk.domain.models import EvolutionConfig

    # Evolve the workflow
    result = await evolve_workflow(
        workflow=sequential_workflow,
        trainset=simple_trainset,
        config=EvolutionConfig(max_iterations=1),  # Minimal for testing
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    # Verify all three agents have evolved instructions (qualified names)
    assert "generator.instruction" in result.evolved_components
    assert "critic.instruction" in result.evolved_components
    assert "refactorer.instruction" in result.evolved_components

    # Verify workflow structure is preserved
    assert len(sequential_workflow.sub_agents) == 3
    assert sequential_workflow.sub_agents[0].name == "generator"
    assert sequential_workflow.sub_agents[1].name == "critic"
    assert sequential_workflow.sub_agents[2].name == "refactorer"

    # Verify share_session=True was used (agents can access earlier outputs)
    # This is verified by the fact that evolution succeeded with agents
    # that reference each other's outputs via template strings


@pytest.mark.asyncio
async def test_evolve_workflow_uses_share_session_true(
    sequential_workflow: SequentialAgent, simple_trainset: list[dict[str, Any]]
) -> None:
    """Verify evolve_workflow() passes share_session=True to evolve_group (FR-010)."""
    from gepa_adk.domain.models import EvolutionConfig

    # This test verifies that share_session=True is used by checking that
    # agents with template string references (e.g., {generated_code}) work correctly
    # If share_session=False, the template references would fail
    result = await evolve_workflow(
        workflow=sequential_workflow,
        trainset=simple_trainset,
        config=EvolutionConfig(max_iterations=1),
    )

    # If share_session=True was used, evolution should succeed
    # If share_session=False, template references would cause errors
    assert isinstance(result, MultiAgentEvolutionResult)
    assert len(result.evolved_components) == 3


@pytest.fixture
def loop_workflow() -> LoopAgent:
    """Create a LoopAgent workflow with multiple LlmAgents."""
    agent1 = LlmAgent(
        name="critic",
        model="gemini-2.0-flash",
        instruction="Review the code and provide feedback.",
        output_key="feedback",
    )
    agent2 = LlmAgent(
        name="refiner",
        model="gemini-2.0-flash",
        instruction="Refine the code based on {feedback}.",
        output_schema=CodeOutput,
    )
    return LoopAgent(
        name="RefinementLoop",
        sub_agents=[agent1, agent2],
        max_iterations=3,
    )


@pytest.mark.asyncio
async def test_evolve_workflow_with_loop_agent(
    loop_workflow: LoopAgent, simple_trainset: list[dict[str, Any]]
) -> None:
    """End-to-end: evolve_workflow() evolves LlmAgents in LoopAgent."""
    from gepa_adk.domain.models import EvolutionConfig

    result = await evolve_workflow(
        workflow=loop_workflow,
        trainset=simple_trainset,
        config=EvolutionConfig(max_iterations=1),
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    # Verify both agents have evolved instructions (qualified names)
    assert "critic.instruction" in result.evolved_components
    assert "refiner.instruction" in result.evolved_components

    # Verify loop configuration is preserved
    assert loop_workflow.max_iterations == 3
    assert len(loop_workflow.sub_agents) == 2


@pytest.fixture
def parallel_workflow() -> ParallelAgent:
    """Create a ParallelAgent workflow with multiple LlmAgent branches."""
    agent1 = LlmAgent(
        name="researcher1",
        model="gemini-2.0-flash",
        instruction="Research topic A.",
        output_schema=CodeOutput,
    )
    agent2 = LlmAgent(
        name="researcher2",
        model="gemini-2.0-flash",
        instruction="Research topic B.",
        output_schema=CodeOutput,
    )
    agent3 = LlmAgent(
        name="researcher3",
        model="gemini-2.0-flash",
        instruction="Research topic C.",
        output_schema=CodeOutput,
    )
    return ParallelAgent(
        name="ParallelResearch",
        sub_agents=[agent1, agent2, agent3],
    )


@pytest.mark.asyncio
async def test_evolve_workflow_with_parallel_agent(
    parallel_workflow: ParallelAgent, simple_trainset: list[dict[str, Any]]
) -> None:
    """End-to-end: evolve_workflow() evolves all parallel branch agents."""
    from gepa_adk.domain.models import EvolutionConfig

    result = await evolve_workflow(
        workflow=parallel_workflow,
        trainset=simple_trainset,
        config=EvolutionConfig(max_iterations=1),
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    # Verify all three parallel branches have evolved instructions (qualified names)
    assert "researcher1.instruction" in result.evolved_components
    assert "researcher2.instruction" in result.evolved_components
    assert "researcher3.instruction" in result.evolved_components

    # Verify parallel structure is preserved
    assert len(parallel_workflow.sub_agents) == 3
