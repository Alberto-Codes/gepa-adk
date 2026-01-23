"""Contract tests for workflow cloning invariants.

These tests verify the structural contracts that clone_workflow_with_overrides()
must satisfy:
1. Type preservation: Output type matches input type
2. Sub-agents count invariant: Cloned workflows have same number of sub-agents
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent

from gepa_adk.adapters.workflow import clone_workflow_with_overrides


class TestCloneWorkflowTypePreservation:
    """Contract: clone_workflow_with_overrides() returns same type as input."""

    def test_llm_agent_returns_llm_agent(self) -> None:
        """LlmAgent input returns LlmAgent output."""
        agent = LlmAgent(name="test", instruction="Be helpful")
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(agent, candidate)

        assert isinstance(result, LlmAgent)
        assert type(result) is LlmAgent

    def test_sequential_agent_returns_sequential_agent(self) -> None:
        """SequentialAgent input returns SequentialAgent output."""
        inner = LlmAgent(name="inner", instruction="Do task")
        workflow = SequentialAgent(name="seq", sub_agents=[inner])
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, SequentialAgent)
        assert type(result) is SequentialAgent

    def test_loop_agent_returns_loop_agent(self) -> None:
        """LoopAgent input returns LoopAgent output."""
        inner = LlmAgent(name="inner", instruction="Refine")
        workflow = LoopAgent(name="loop", sub_agents=[inner], max_iterations=3)
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, LoopAgent)
        assert type(result) is LoopAgent

    def test_parallel_agent_returns_parallel_agent(self) -> None:
        """ParallelAgent input returns ParallelAgent output."""
        agent_a = LlmAgent(name="a", instruction="Task A")
        agent_b = LlmAgent(name="b", instruction="Task B")
        workflow = ParallelAgent(name="parallel", sub_agents=[agent_a, agent_b])
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, ParallelAgent)
        assert type(result) is ParallelAgent


class TestCloneWorkflowSubAgentsInvariant:
    """Contract: Cloned workflows maintain sub_agents count."""

    def test_sequential_preserves_sub_agents_count(self) -> None:
        """SequentialAgent clone has same number of sub_agents."""
        agents = [
            LlmAgent(name=f"agent_{i}", instruction=f"Task {i}") for i in range(3)
        ]
        workflow = SequentialAgent(name="seq", sub_agents=agents)
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert len(result.sub_agents) == len(workflow.sub_agents)
        assert len(result.sub_agents) == 3

    def test_loop_preserves_sub_agents_count(self) -> None:
        """LoopAgent clone has same number of sub_agents."""
        inner = LlmAgent(name="inner", instruction="Refine")
        workflow = LoopAgent(name="loop", sub_agents=[inner], max_iterations=5)
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert len(result.sub_agents) == len(workflow.sub_agents)
        assert len(result.sub_agents) == 1

    def test_parallel_preserves_sub_agents_count(self) -> None:
        """ParallelAgent clone has same number of sub_agents."""
        agents = [
            LlmAgent(name=f"worker_{i}", instruction=f"Work {i}") for i in range(4)
        ]
        workflow = ParallelAgent(name="parallel", sub_agents=agents)
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert len(result.sub_agents) == len(workflow.sub_agents)
        assert len(result.sub_agents) == 4

    def test_nested_workflow_preserves_structure_depth(self) -> None:
        """Nested workflows preserve structure at all levels."""
        # Level 3: LlmAgents
        llm_a = LlmAgent(name="a", instruction="A")
        llm_b = LlmAgent(name="b", instruction="B")
        llm_c = LlmAgent(name="c", instruction="C")

        # Level 2: ParallelAgent containing two LlmAgents
        parallel = ParallelAgent(name="parallel", sub_agents=[llm_a, llm_b])

        # Level 1: SequentialAgent containing Parallel + LlmAgent
        workflow = SequentialAgent(name="seq", sub_agents=[parallel, llm_c])

        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        # Level 1: Sequential has 2 sub_agents
        assert len(result.sub_agents) == 2

        # Level 2: First sub_agent is ParallelAgent with 2 sub_agents
        cloned_parallel = result.sub_agents[0]
        assert isinstance(cloned_parallel, ParallelAgent)
        assert len(cloned_parallel.sub_agents) == 2

        # Level 3: Both are LlmAgents
        assert isinstance(cloned_parallel.sub_agents[0], LlmAgent)
        assert isinstance(cloned_parallel.sub_agents[1], LlmAgent)


class TestCloneWorkflowLoopAgentMaxIterations:
    """Contract: LoopAgent.max_iterations is preserved during cloning."""

    @pytest.mark.parametrize("max_iterations", [1, 3, 5, 10])
    def test_max_iterations_preserved(self, max_iterations: int) -> None:
        """LoopAgent clone preserves max_iterations value."""
        inner = LlmAgent(name="refiner", instruction="Refine the output")
        workflow = LoopAgent(
            name="refinement_loop",
            sub_agents=[inner],
            max_iterations=max_iterations,
        )
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert result.max_iterations == max_iterations
        assert result.max_iterations == workflow.max_iterations
