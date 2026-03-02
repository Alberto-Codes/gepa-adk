"""Contract tests for workflow utilities.

These tests ensure workflow utilities satisfy their contracts with correct
method signatures, return types, and runtime checks. These are contract tests
that verify protocol compliance without requiring actual ADK agent execution.

Note:
    These tests use real ADK agent instances to verify type detection.
    Integration tests (in tests/integration/) verify actual workflow evolution.
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent

from gepa_adk.adapters.workflow.workflow import find_llm_agents, is_workflow_agent
from gepa_adk.api import evolve_workflow

pytestmark = pytest.mark.contract


class TestIsWorkflowAgentContract:
    """Contract tests for is_workflow_agent() function."""

    def test_is_workflow_agent_exists(self):
        """Verify is_workflow_agent() function exists and is callable."""
        assert callable(is_workflow_agent), "is_workflow_agent() must be callable"

    def test_is_workflow_agent_accepts_any_agent(self):
        """Verify is_workflow_agent() accepts any agent type."""
        # Should not raise TypeError for any agent
        sequential = SequentialAgent(name="test", sub_agents=[])
        result = is_workflow_agent(sequential)
        assert isinstance(result, bool)

    def test_is_workflow_agent_returns_bool(self):
        """Verify is_workflow_agent() returns bool type."""
        sequential = SequentialAgent(name="test", sub_agents=[])
        result = is_workflow_agent(sequential)
        assert isinstance(result, bool), "is_workflow_agent() must return bool"

    def test_is_workflow_agent_with_sequential_agent(self):
        """Verify is_workflow_agent() returns True for SequentialAgent."""
        sequential = SequentialAgent(name="test", sub_agents=[])
        assert is_workflow_agent(sequential) is True

    def test_is_workflow_agent_with_loop_agent(self):
        """Verify is_workflow_agent() returns True for LoopAgent."""
        loop = LoopAgent(name="test", sub_agents=[], max_iterations=5)
        assert is_workflow_agent(loop) is True

    def test_is_workflow_agent_with_parallel_agent(self):
        """Verify is_workflow_agent() returns True for ParallelAgent."""
        parallel = ParallelAgent(name="test", sub_agents=[])
        assert is_workflow_agent(parallel) is True

    def test_is_workflow_agent_with_llm_agent(self):
        """Verify is_workflow_agent() returns False for LlmAgent."""
        llm = LlmAgent(name="test", instruction="Be helpful")
        assert is_workflow_agent(llm) is False

    def test_is_workflow_agent_with_non_agent(self):
        """Verify is_workflow_agent() returns False for non-agent objects."""
        assert is_workflow_agent("not an agent") is False
        assert is_workflow_agent(42) is False
        assert is_workflow_agent(None) is False
        assert is_workflow_agent([]) is False


class TestFindLlmAgentsContract:
    """Contract tests for find_llm_agents() function."""

    def test_find_llm_agents_exists(self):
        """Verify find_llm_agents() function exists and is callable."""
        assert callable(find_llm_agents), "find_llm_agents() must be callable"

    def test_find_llm_agents_accepts_agent(self):
        """Verify find_llm_agents() accepts any agent type."""
        llm = LlmAgent(name="test", instruction="Be helpful")
        result = find_llm_agents(llm)
        assert isinstance(result, list)

    def test_find_llm_agents_returns_list(self):
        """Verify find_llm_agents() returns list type."""
        llm = LlmAgent(name="test", instruction="Be helpful")
        result = find_llm_agents(llm)
        assert isinstance(result, list), "find_llm_agents() must return list"

    def test_find_llm_agents_with_llm_agent_returns_list_of_llm_agents(self):
        """Verify find_llm_agents() returns list[LlmAgent] for LlmAgent input."""
        llm = LlmAgent(name="test", instruction="Be helpful")
        result = find_llm_agents(llm)
        assert len(result) == 1
        assert isinstance(result[0], LlmAgent)

    def test_find_llm_agents_with_sequential_agent_returns_list(self):
        """Verify find_llm_agents() returns list for SequentialAgent."""
        sequential = SequentialAgent(name="test", sub_agents=[])
        result = find_llm_agents(sequential)
        assert isinstance(result, list)

    def test_find_llm_agents_accepts_max_depth(self):
        """Verify find_llm_agents() accepts max_depth parameter."""
        llm = LlmAgent(name="test", instruction="Be helpful")
        result = find_llm_agents(llm, max_depth=3)
        assert isinstance(result, list)


class TestEvolveWorkflowContract:
    """Contract tests for evolve_workflow() function."""

    def test_evolve_workflow_exists(self):
        """Verify evolve_workflow() function exists and is callable."""
        assert callable(evolve_workflow), "evolve_workflow() must be callable"

    def test_evolve_workflow_is_async(self):
        """Verify evolve_workflow() is an async function."""
        import inspect

        assert inspect.iscoroutinefunction(evolve_workflow), (
            "evolve_workflow() must be async"
        )

    def test_evolve_workflow_signature(self):
        """Verify evolve_workflow() has correct signature."""
        import inspect

        sig = inspect.signature(evolve_workflow)
        params = list(sig.parameters.keys())

        assert "workflow" in params
        assert "trainset" in params
        assert "critic" in params
        assert "primary" in params
        assert "max_depth" in params
        assert "config" in params

        # Check defaults
        assert sig.parameters["critic"].default is None
        assert sig.parameters["primary"].default is None
        assert sig.parameters["max_depth"].default == 5
        assert sig.parameters["config"].default is None
