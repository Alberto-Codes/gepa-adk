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
        model="gemini-2.5-flash",
        instruction="Generate a simple Python function.",
        output_key="generated_code",
        output_schema=CodeOutput,
    )
    agent2 = LlmAgent(
        name="critic",
        model="gemini-2.5-flash",
        instruction="Review the code in {generated_code} and provide feedback.",
    )
    agent3 = LlmAgent(
        name="refactorer",
        model="gemini-2.5-flash",
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
    """End-to-end: evolve_workflow() with round_robin evolves all LlmAgents."""
    from gepa_adk.domain.models import EvolutionConfig

    # Evolve the workflow with round_robin=True to evolve all agents
    result = await evolve_workflow(
        workflow=sequential_workflow,
        trainset=simple_trainset,
        round_robin=True,  # Evolve all agents, not just the first
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
        round_robin=True,  # Evolve all agents to verify shared session
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
        model="gemini-2.5-flash",
        instruction="Review the code and provide feedback.",
        output_key="feedback",
    )
    agent2 = LlmAgent(
        name="refiner",
        model="gemini-2.5-flash",
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
    """End-to-end: evolve_workflow() with round_robin evolves LlmAgents in LoopAgent."""
    from gepa_adk.domain.models import EvolutionConfig

    result = await evolve_workflow(
        workflow=loop_workflow,
        trainset=simple_trainset,
        round_robin=True,  # Evolve all agents, not just the first
        config=EvolutionConfig(max_iterations=1),
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    # Verify both agents have evolved instructions (qualified names)
    assert "critic.instruction" in result.evolved_components
    assert "refiner.instruction" in result.evolved_components

    # Verify loop configuration is preserved
    assert loop_workflow.max_iterations == 3
    assert len(loop_workflow.sub_agents) == 2


@pytest.mark.asyncio
async def test_evolve_workflow_loop_agent_preserves_max_iterations(
    simple_trainset: list[dict[str, Any]],
) -> None:
    """T010: Verify LoopAgent max_iterations is preserved during cloning in _build_pipeline().

    This test verifies that when evolve_workflow() clones a LoopAgent,
    the cloned workflow preserves the max_iterations value. The cloned
    workflow (used for execution) should have the same max_iterations
    as the original.

    Note:
        This is critical for issue #215 - workflows should execute as-is
        without being flattened. LoopAgent iterations must be preserved.
    """
    from gepa_adk.adapters.workflow.workflow import clone_workflow_with_overrides
    from gepa_adk.domain.models import EvolutionConfig

    # Create LoopAgent with specific max_iterations
    inner_agent = LlmAgent(
        name="inner",
        model="gemini-2.5-flash",
        instruction="Process and refine the input.",
        output_schema=CodeOutput,
    )
    loop_workflow = LoopAgent(
        name="IterativeLoop",
        sub_agents=[inner_agent],
        max_iterations=5,  # Specific value to verify preservation
    )

    # Verify clone_workflow_with_overrides preserves max_iterations
    # This is what _build_pipeline() uses internally
    cloned = clone_workflow_with_overrides(loop_workflow, {})
    assert isinstance(cloned, LoopAgent), "Cloned workflow must be LoopAgent"
    assert cloned.max_iterations == 5, "max_iterations must be preserved"
    assert len(cloned.sub_agents) == 1, "sub_agents count must be preserved"

    # Now run full evolution to verify end-to-end flow works
    result = await evolve_workflow(
        workflow=loop_workflow,
        trainset=simple_trainset,
        config=EvolutionConfig(max_iterations=1),
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    assert "inner.instruction" in result.evolved_components
    # Original workflow should be unchanged
    assert loop_workflow.max_iterations == 5


@pytest.fixture
def parallel_workflow() -> ParallelAgent:
    """Create a ParallelAgent workflow with multiple LlmAgent branches."""
    agent1 = LlmAgent(
        name="researcher1",
        model="gemini-2.5-flash",
        instruction="Research topic A.",
        output_schema=CodeOutput,
    )
    agent2 = LlmAgent(
        name="researcher2",
        model="gemini-2.5-flash",
        instruction="Research topic B.",
        output_schema=CodeOutput,
    )
    agent3 = LlmAgent(
        name="researcher3",
        model="gemini-2.5-flash",
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
    """End-to-end: evolve_workflow() with round_robin evolves all parallel branches."""
    from gepa_adk.domain.models import EvolutionConfig

    result = await evolve_workflow(
        workflow=parallel_workflow,
        trainset=simple_trainset,
        round_robin=True,  # Evolve all agents, not just the first
        config=EvolutionConfig(max_iterations=1),
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    # Verify all three parallel branches have evolved instructions (qualified names)
    assert "researcher1.instruction" in result.evolved_components
    assert "researcher2.instruction" in result.evolved_components
    assert "researcher3.instruction" in result.evolved_components

    # Verify parallel structure is preserved
    assert len(parallel_workflow.sub_agents) == 3


@pytest.mark.asyncio
async def test_evolve_workflow_parallel_agent_preserves_type_for_concurrency(
    simple_trainset: list[dict[str, Any]],
) -> None:
    """T017: Verify ParallelAgent type is preserved during cloning in _build_pipeline().

    This test verifies that when evolve_workflow() clones a ParallelAgent,
    the cloned workflow preserves the ParallelAgent type. This is critical
    because ADK Runner executes ParallelAgent sub_agents concurrently
    only if the type is exactly ParallelAgent.

    Note:
        This is critical for issue #215 - workflows should execute as-is
        without being flattened. ParallelAgent concurrency must be preserved.
    """
    from gepa_adk.adapters.workflow.workflow import clone_workflow_with_overrides
    from gepa_adk.domain.models import EvolutionConfig

    # Create ParallelAgent with concurrent branches
    branch_a = LlmAgent(
        name="branch_a",
        model="gemini-2.5-flash",
        instruction="Process data through branch A.",
        output_schema=CodeOutput,
    )
    branch_b = LlmAgent(
        name="branch_b",
        model="gemini-2.5-flash",
        instruction="Process data through branch B.",
        output_schema=CodeOutput,
    )
    parallel_workflow = ParallelAgent(
        name="ConcurrentProcessing",
        sub_agents=[branch_a, branch_b],
    )

    # Verify clone_workflow_with_overrides preserves ParallelAgent type
    # This is what _build_pipeline() uses internally
    cloned = clone_workflow_with_overrides(parallel_workflow, {})
    assert type(cloned) is ParallelAgent, (
        "Cloned workflow must be exactly ParallelAgent"
    )
    assert len(cloned.sub_agents) == 2, "sub_agents count must be preserved"

    # Now run full evolution to verify end-to-end flow works
    result = await evolve_workflow(
        workflow=parallel_workflow,
        trainset=simple_trainset,
        round_robin=True,
        config=EvolutionConfig(max_iterations=1),
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    assert "branch_a.instruction" in result.evolved_components
    assert "branch_b.instruction" in result.evolved_components
    # Original workflow should be unchanged
    assert type(parallel_workflow) is ParallelAgent
    assert len(parallel_workflow.sub_agents) == 2


@pytest.fixture
def nested_workflow() -> SequentialAgent:
    """Create a nested workflow with Sequential containing Parallel and a Synthesizer."""
    # Parallel research stage with two branches
    researcher1 = LlmAgent(
        name="researcher1",
        model="gemini-2.5-flash",
        instruction="Research the first topic.",
        output_key="research1",
        output_schema=CodeOutput,
    )
    researcher2 = LlmAgent(
        name="researcher2",
        model="gemini-2.5-flash",
        instruction="Research the second topic.",
        output_key="research2",
        output_schema=CodeOutput,
    )
    parallel_research = ParallelAgent(
        name="ParallelResearch",
        sub_agents=[researcher1, researcher2],
    )

    # Synthesizer that combines parallel outputs
    synthesizer = LlmAgent(
        name="synthesizer",
        model="gemini-2.5-flash",
        instruction="Synthesize research from {research1} and {research2}.",
        output_schema=CodeOutput,
    )

    return SequentialAgent(
        name="ResearchPipeline",
        sub_agents=[parallel_research, synthesizer],
    )


@pytest.mark.asyncio
async def test_evolve_workflow_with_nested_structure(
    nested_workflow: SequentialAgent, simple_trainset: list[dict[str, Any]]
) -> None:
    """T023: End-to-end test for nested workflow structure preservation.

    Tests Sequential([Parallel([A, B]), C]) pattern to verify:
    - ParallelAgent is preserved within SequentialAgent
    - All agents are evolved correctly
    - Data flows from parallel outputs to synthesizer
    """
    from gepa_adk.domain.models import EvolutionConfig

    result = await evolve_workflow(
        workflow=nested_workflow,
        trainset=simple_trainset,
        round_robin=True,
        config=EvolutionConfig(max_iterations=1),
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    # Verify all agents have evolved instructions
    assert "researcher1.instruction" in result.evolved_components
    assert "researcher2.instruction" in result.evolved_components
    assert "synthesizer.instruction" in result.evolved_components

    # Verify nested structure is preserved
    assert isinstance(nested_workflow, SequentialAgent)
    assert len(nested_workflow.sub_agents) == 2
    assert isinstance(nested_workflow.sub_agents[0], ParallelAgent)
    assert len(nested_workflow.sub_agents[0].sub_agents) == 2


@pytest.mark.asyncio
async def test_evolve_workflow_nested_preserves_structure_during_cloning(
    simple_trainset: list[dict[str, Any]],
) -> None:
    """T023: Verify nested workflow structure is preserved during cloning in _build_pipeline().

    This test verifies that when evolve_workflow() clones a nested workflow,
    all agent types are preserved at every level.

    Note:
        This is critical for issue #215 - complex workflows should execute
        exactly as designed, with parallel stages running concurrently and
        sequential stages running in order.
    """
    from gepa_adk.adapters.workflow.workflow import clone_workflow_with_overrides
    from gepa_adk.domain.models import EvolutionConfig

    # Create nested workflow: Sequential([Parallel([Loop([A]), B]), C])
    inner_agent = LlmAgent(
        name="inner",
        model="gemini-2.5-flash",
        instruction="Inner loop task.",
        output_schema=CodeOutput,
    )
    loop = LoopAgent(
        name="loop",
        sub_agents=[inner_agent],
        max_iterations=2,
    )
    sibling = LlmAgent(
        name="sibling",
        model="gemini-2.5-flash",
        instruction="Parallel sibling.",
        output_schema=CodeOutput,
    )
    parallel = ParallelAgent(
        name="parallel",
        sub_agents=[loop, sibling],
    )
    finalizer = LlmAgent(
        name="finalizer",
        model="gemini-2.5-flash",
        instruction="Final synthesis.",
        output_schema=CodeOutput,
    )
    workflow = SequentialAgent(
        name="DeepWorkflow",
        sub_agents=[parallel, finalizer],
    )

    # Verify clone preserves all types and properties
    cloned = clone_workflow_with_overrides(workflow, {})
    assert isinstance(cloned, SequentialAgent)
    assert isinstance(cloned.sub_agents[0], ParallelAgent)
    assert isinstance(cloned.sub_agents[0].sub_agents[0], LoopAgent)
    assert cloned.sub_agents[0].sub_agents[0].max_iterations == 2
    assert isinstance(cloned.sub_agents[1], LlmAgent)

    # Run full evolution to verify end-to-end flow
    result = await evolve_workflow(
        workflow=workflow,
        trainset=simple_trainset,
        round_robin=True,
        config=EvolutionConfig(max_iterations=1),
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    # All nested agents should have evolved
    assert "inner.instruction" in result.evolved_components
    assert "sibling.instruction" in result.evolved_components
    assert "finalizer.instruction" in result.evolved_components
