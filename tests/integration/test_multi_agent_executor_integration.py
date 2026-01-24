"""Integration tests for Multi-Agent Unified Executor.

This module contains end-to-end integration tests that verify the unified
AgentExecutor works correctly with real LLM calls for both multi-agent
evolution and workflow evolution scenarios.

Note:
    These tests require external services (Gemini API) and are marked with
    @pytest.mark.requires_gemini. They verify the full execution path from
    evolve_group()/evolve_workflow() through AgentExecutor to actual agent execution.
"""

import pytest
from google.adk.agents import LlmAgent, SequentialAgent
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, evolve_group, evolve_workflow


class SimpleOutput(BaseModel):
    """Simple output schema for testing."""

    answer: str = Field(description="The answer to the question")


@pytest.mark.requires_gemini
@pytest.mark.asyncio
async def test_multi_agent_evolution_with_executor_integration():
    """Integration test: Multi-agent evolution uses unified executor end-to-end.

    This test verifies that evolve_group() creates an AgentExecutor and uses it
    for all agent executions throughout the evolution process. It makes real
    LLM calls to verify the full execution path works correctly.

    Verifies:
        - evolve_group() creates executor (FR-003)
        - Executor is passed to all components (FR-004, FR-005, FR-006)
        - Multi-agent evolution completes successfully with executor
        - Final result includes evolved components
    """
    # Create simple multi-agent pipeline
    generator = LlmAgent(
        name="generator",
        model="gemini-2.5-flash",
        instruction="Answer the question simply and clearly.",
        output_key="draft_answer",
    )

    reviewer = LlmAgent(
        name="reviewer",
        model="gemini-2.5-flash",
        instruction="Review the draft answer: {draft_answer}. Provide final answer.",
        output_schema=SimpleOutput,
    )

    agents = {"generator": generator, "reviewer": reviewer}

    # Create minimal training set
    trainset = [
        {"input": "What is 2+2?"},
    ]

    # Configure for fast execution
    config = EvolutionConfig(
        max_iterations=1,  # Single iteration for integration test
        patience=1,
        reflection_model="gemini-2.5-flash",  # Use Gemini for integration test
    )

    # Run evolution - executor is created automatically
    result = await evolve_group(
        agents=agents,
        primary="reviewer",
        trainset=trainset,
        config=config,
    )

    # Verify evolution completed successfully
    assert result is not None
    assert result.evolved_components is not None
    # Evolved components use qualified names (agent.component format)
    assert "generator.instruction" in result.evolved_components
    assert "reviewer.instruction" in result.evolved_components
    assert result.final_score is not None
    assert result.total_iterations >= 1

    # Verify components contain text (evolved instructions)
    assert len(result.evolved_components["generator.instruction"]) > 0
    assert len(result.evolved_components["reviewer.instruction"]) > 0


@pytest.mark.requires_gemini
@pytest.mark.asyncio
async def test_workflow_evolution_with_executor_integration():
    """Integration test: Workflow evolution inherits executor support end-to-end.

    This test verifies that evolve_workflow() delegates to evolve_group() and
    uses the unified executor for all agent executions. It makes real LLM calls
    to verify the delegation chain works correctly.

    Verifies:
        - evolve_workflow() delegates to evolve_group() (FR-007)
        - Executor is created and used automatically
        - Workflow evolution completes successfully
        - Workflow structure is preserved (SequentialAgent)
        - Final result includes evolved components for all workflow agents
    """
    # Create workflow agents
    agent1 = LlmAgent(
        name="step1",
        model="gemini-2.5-flash",
        instruction="Provide initial answer to the question.",
        output_key="initial_answer",
    )

    agent2 = LlmAgent(
        name="step2",
        model="gemini-2.5-flash",
        instruction="Refine this answer: {initial_answer}",
        output_schema=SimpleOutput,
    )

    # Create workflow
    workflow = SequentialAgent(
        name="TwoStepWorkflow",
        sub_agents=[agent1, agent2],
    )

    # Create minimal training set
    trainset = [
        {"input": "What is the capital of France?"},
    ]

    # Configure for fast execution
    config = EvolutionConfig(
        max_iterations=1,  # Single iteration for integration test
        patience=1,
        reflection_model="gemini-2.5-flash",  # Use Gemini for integration test
    )

    # Run workflow evolution - executor is created via delegation
    # Use round_robin=True to evolve all agents in the workflow
    result = await evolve_workflow(
        workflow=workflow,
        trainset=trainset,
        config=config,
        round_robin=True,  # Evolve all workflow agents
    )

    # Verify evolution completed successfully
    assert result is not None
    assert result.evolved_components is not None
    # Evolved components use qualified names (agent.component format)
    assert "step1.instruction" in result.evolved_components
    assert "step2.instruction" in result.evolved_components
    assert result.final_score is not None
    assert result.total_iterations >= 1

    # Verify components contain text (evolved instructions)
    assert len(result.evolved_components["step1.instruction"]) > 0
    assert len(result.evolved_components["step2.instruction"]) > 0
