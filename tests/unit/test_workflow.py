"""Unit tests for workflow utilities.

These tests verify the business logic of workflow utilities using real ADK
agent instances to isolate workflow behavior from external services.

Note:
    Unit tests use real ADK agent instances for type detection.
    Integration tests (in tests/integration/) use real workflow execution.
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent

from gepa_adk.adapters.workflow import find_llm_agents, is_workflow_agent

pytestmark = pytest.mark.unit


class TestIsWorkflowAgent:
    """Unit tests for is_workflow_agent() function."""

    def test_sequential_agent_returns_true(self):
        """Verify SequentialAgent is detected as workflow agent."""
        sequential = SequentialAgent(name="pipeline", sub_agents=[])
        assert is_workflow_agent(sequential) is True

    def test_loop_agent_returns_true(self):
        """Verify LoopAgent is detected as workflow agent."""
        loop = LoopAgent(name="refinement", sub_agents=[], max_iterations=5)
        assert is_workflow_agent(loop) is True

    def test_parallel_agent_returns_true(self):
        """Verify ParallelAgent is detected as workflow agent."""
        parallel = ParallelAgent(name="parallel", sub_agents=[])
        assert is_workflow_agent(parallel) is True

    def test_llm_agent_returns_false(self):
        """Verify LlmAgent is not detected as workflow agent."""
        llm = LlmAgent(name="agent", instruction="Be helpful")
        assert is_workflow_agent(llm) is False

    def test_sequential_with_sub_agents_returns_true(self):
        """Verify SequentialAgent with sub-agents is still detected."""
        sub_agent = LlmAgent(name="sub", instruction="Help")
        sequential = SequentialAgent(name="pipeline", sub_agents=[sub_agent])
        assert is_workflow_agent(sequential) is True

    def test_loop_with_sub_agents_returns_true(self):
        """Verify LoopAgent with sub-agents is still detected."""
        sub_agent = LlmAgent(name="sub", instruction="Help")
        loop = LoopAgent(name="refinement", sub_agents=[sub_agent], max_iterations=3)
        assert is_workflow_agent(loop) is True

    def test_parallel_with_sub_agents_returns_true(self):
        """Verify ParallelAgent with sub-agents is still detected."""
        sub_agent = LlmAgent(name="sub", instruction="Help")
        parallel = ParallelAgent(name="parallel", sub_agents=[sub_agent])
        assert is_workflow_agent(parallel) is True

    def test_non_agent_returns_false(self):
        """Verify non-agent objects return False."""
        assert is_workflow_agent("string") is False
        assert is_workflow_agent(123) is False
        assert is_workflow_agent(None) is False
        assert is_workflow_agent([]) is False
        assert is_workflow_agent({}) is False


class TestFindLlmAgents:
    """Unit tests for find_llm_agents() function (single-level only for US1)."""

    def test_find_llm_agents_with_single_llm_agent(self):
        """Verify find_llm_agents() returns single LlmAgent for LlmAgent input."""
        llm = LlmAgent(name="agent", instruction="Be helpful")
        result = find_llm_agents(llm)
        assert len(result) == 1
        assert result[0] is llm

    def test_find_llm_agents_with_sequential_agent_single_level(self):
        """Verify find_llm_agents() finds LlmAgents in SequentialAgent (single-level)."""
        agent1 = LlmAgent(name="agent1", instruction="First")
        agent2 = LlmAgent(name="agent2", instruction="Second")
        sequential = SequentialAgent(name="pipeline", sub_agents=[agent1, agent2])
        result = find_llm_agents(sequential)
        assert len(result) == 2
        assert agent1 in result
        assert agent2 in result

    def test_find_llm_agents_with_empty_sequential_agent(self):
        """Verify find_llm_agents() returns empty list for empty SequentialAgent."""
        sequential = SequentialAgent(name="pipeline", sub_agents=[])
        result = find_llm_agents(sequential)
        assert result == []

    def test_find_llm_agents_with_sequential_agent_mixed_types(self):
        """Verify find_llm_agents() only finds LlmAgents, skips non-LlmAgents."""
        agent1 = LlmAgent(name="agent1", instruction="First")
        # Non-LlmAgent sub-agent (workflow agent)
        nested_workflow = SequentialAgent(name="nested", sub_agents=[])
        sequential = SequentialAgent(
            name="pipeline", sub_agents=[agent1, nested_workflow]
        )
        result = find_llm_agents(sequential)
        # Single-level only: should find agent1, but NOT agents inside nested_workflow
        assert len(result) == 1
        assert agent1 in result


class TestFindLlmAgentsRecursive:
    """Unit tests for find_llm_agents() with recursive traversal (US3)."""

    def test_find_llm_agents_with_nested_workflows(self):
        """Verify find_llm_agents() recursively finds LlmAgents in nested workflows."""
        # Create nested structure: Sequential -> Parallel -> LlmAgents
        agent1 = LlmAgent(name="agent1", instruction="First")
        agent2 = LlmAgent(name="agent2", instruction="Second")
        agent3 = LlmAgent(name="agent3", instruction="Third")

        parallel = ParallelAgent(name="parallel", sub_agents=[agent2, agent3])
        sequential = SequentialAgent(name="pipeline", sub_agents=[agent1, parallel])

        result = find_llm_agents(sequential, max_depth=5)
        # Should find all 3 agents across both levels
        assert len(result) == 3
        assert agent1 in result
        assert agent2 in result
        assert agent3 in result

    def test_find_llm_agents_with_deeply_nested_workflows(self):
        """Verify find_llm_agents() handles deeply nested workflows (3+ levels)."""
        # Level 3: Innermost agents
        agent1 = LlmAgent(name="agent1", instruction="Level 3")
        agent2 = LlmAgent(name="agent2", instruction="Level 3")

        # Level 2: Parallel workflow
        parallel = ParallelAgent(name="parallel", sub_agents=[agent1, agent2])

        # Level 1: Sequential workflow
        agent3 = LlmAgent(name="agent3", instruction="Level 1")
        sequential = SequentialAgent(name="pipeline", sub_agents=[agent3, parallel])

        result = find_llm_agents(sequential, max_depth=5)
        # Should find all 3 agents across all levels
        assert len(result) == 3
        assert agent1 in result
        assert agent2 in result
        assert agent3 in result

    def test_find_llm_agents_with_max_depth_limiting(self):
        """Verify find_llm_agents() respects max_depth parameter."""
        # Create 4-level deep structure
        agent_deep = LlmAgent(name="deep", instruction="Level 4")
        level3 = SequentialAgent(name="level3", sub_agents=[agent_deep])
        level2 = SequentialAgent(name="level2", sub_agents=[level3])
        level1 = SequentialAgent(name="level1", sub_agents=[level2])

        # With max_depth=2, should only find agents up to depth 2
        result = find_llm_agents(level1, max_depth=2)
        # Should not find agent_deep (at depth 4)
        assert len(result) == 0

        # With max_depth=3, should find agent_deep
        result = find_llm_agents(level1, max_depth=3)
        assert len(result) == 1
        assert agent_deep in result

    def test_find_llm_agents_skips_non_string_instructions(self):
        """Verify find_llm_agents() skips LlmAgents with InstructionProvider callables."""
        # Create agent with string instruction (should be included)
        agent_string = LlmAgent(name="agent_string", instruction="String instruction")

        # Create agent with callable instruction (should be skipped)
        def instruction_provider() -> str:
            return "Dynamic instruction"

        agent_callable = LlmAgent(
            name="agent_callable", instruction=instruction_provider
        )

        sequential = SequentialAgent(
            name="pipeline", sub_agents=[agent_string, agent_callable]
        )

        result = find_llm_agents(sequential)
        # Should only find agent_string, skip agent_callable
        assert len(result) == 1
        assert agent_string in result
        assert agent_callable not in result

    def test_find_llm_agents_with_max_depth_zero(self):
        """Verify find_llm_agents() returns empty list when max_depth=0."""
        agent = LlmAgent(name="agent", instruction="Test")
        sequential = SequentialAgent(name="pipeline", sub_agents=[agent])

        result = find_llm_agents(sequential, max_depth=0)
        # Should return empty list (immediate return at depth check)
        assert result == []

    def test_find_llm_agents_with_nested_loop_agent(self):
        """Verify find_llm_agents() handles LoopAgent in nested structure."""
        agent1 = LlmAgent(name="agent1", instruction="First")
        agent2 = LlmAgent(name="agent2", instruction="Second")

        loop = LoopAgent(name="loop", sub_agents=[agent2], max_iterations=5)
        sequential = SequentialAgent(name="pipeline", sub_agents=[agent1, loop])

        result = find_llm_agents(sequential, max_depth=5)
        # Should find both agents
        assert len(result) == 2
        assert agent1 in result
        assert agent2 in result


class TestFindLlmAgentsLoopAgent:
    """Unit tests for find_llm_agents() with LoopAgent (US4)."""

    def test_find_llm_agents_with_loop_agent(self):
        """Verify find_llm_agents() finds LlmAgents in LoopAgent."""
        agent1 = LlmAgent(name="agent1", instruction="First")
        agent2 = LlmAgent(name="agent2", instruction="Second")

        loop = LoopAgent(
            name="refinement", sub_agents=[agent1, agent2], max_iterations=5
        )
        result = find_llm_agents(loop)

        assert len(result) == 2
        assert agent1 in result
        assert agent2 in result

    def test_find_llm_agents_with_empty_loop_agent(self):
        """Verify find_llm_agents() returns empty list for empty LoopAgent."""
        loop = LoopAgent(name="refinement", sub_agents=[], max_iterations=5)
        result = find_llm_agents(loop)
        assert result == []


class TestFindLlmAgentsParallelAgent:
    """Unit tests for find_llm_agents() with ParallelAgent (US5)."""

    def test_find_llm_agents_with_parallel_agent(self):
        """Verify find_llm_agents() finds LlmAgents in ParallelAgent."""
        agent1 = LlmAgent(name="agent1", instruction="First")
        agent2 = LlmAgent(name="agent2", instruction="Second")
        agent3 = LlmAgent(name="agent3", instruction="Third")

        parallel = ParallelAgent(name="parallel", sub_agents=[agent1, agent2, agent3])
        result = find_llm_agents(parallel)

        assert len(result) == 3
        assert agent1 in result
        assert agent2 in result
        assert agent3 in result

    def test_find_llm_agents_with_empty_parallel_agent(self):
        """Verify find_llm_agents() returns empty list for empty ParallelAgent."""
        parallel = ParallelAgent(name="parallel", sub_agents=[])
        result = find_llm_agents(parallel)
        assert result == []
