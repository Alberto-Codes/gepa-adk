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

from gepa_adk.adapters.workflow import (
    clone_workflow_with_overrides,
    find_llm_agents,
    is_workflow_agent,
)

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
        # Create 4-level deep structure:
        # level1 (depth 0) -> level2 (depth 1) -> level3 (depth 2) -> agent_deep (depth 3)
        agent_deep = LlmAgent(name="deep", instruction="Level 3")
        level3 = SequentialAgent(name="level3", sub_agents=[agent_deep])
        level2 = SequentialAgent(name="level2", sub_agents=[level3])
        level1 = SequentialAgent(name="level1", sub_agents=[level2])

        # With max_depth=2, should only find agents up to depth 2 (exclusive)
        # agent_deep is at depth 3, so should not be found
        result = find_llm_agents(level1, max_depth=2)
        assert len(result) == 0

        # With max_depth=3, should find agent_deep (at depth 3, inclusive)
        result = find_llm_agents(level1, max_depth=3)
        assert len(result) == 1
        assert agent_deep in result

    def test_find_llm_agents_skips_non_string_instructions(self):
        """Verify find_llm_agents() skips LlmAgents with InstructionProvider callables."""
        from google.adk.agents.readonly_context import ReadonlyContext

        # Create agent with string instruction (should be included)
        agent_string = LlmAgent(name="agent_string", instruction="String instruction")

        # Create agent with callable instruction (should be skipped)
        # InstructionProvider signature: (ReadonlyContext) -> str | Awaitable[str]
        def instruction_provider(ctx: ReadonlyContext) -> str:
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


class TestCloneWorkflowWithOverridesLlmAgent:
    """Unit tests for clone_workflow_with_overrides() with LlmAgent."""

    def test_clone_llm_agent_no_override(self) -> None:
        """Verify cloning LlmAgent without override preserves instruction."""
        agent = LlmAgent(name="test_agent", instruction="Original instruction")
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(agent, candidate)

        assert isinstance(result, LlmAgent)
        assert result.name == "test_agent"
        assert result.instruction == "Original instruction"
        # Verify it's a different instance
        assert result is not agent

    def test_clone_llm_agent_with_instruction_override(self) -> None:
        """Verify cloning LlmAgent applies instruction override."""
        agent = LlmAgent(name="test_agent", instruction="Original instruction")
        candidate = {"test_agent.instruction": "New instruction from candidate"}

        result = clone_workflow_with_overrides(agent, candidate)

        assert isinstance(result, LlmAgent)
        assert result.name == "test_agent"
        assert result.instruction == "New instruction from candidate"
        # Original should be unchanged
        assert agent.instruction == "Original instruction"

    def test_clone_llm_agent_clears_parent_agent(self) -> None:
        """Verify cloning clears parent_agent to avoid ADK ValueError."""
        parent = SequentialAgent(name="parent", sub_agents=[])
        agent = LlmAgent(name="child", instruction="Child instruction")
        # Simulate having a parent (normally set by ADK during construction)
        agent_with_parent = agent.model_copy(update={"parent_agent": parent})

        candidate: dict[str, str] = {}
        result = clone_workflow_with_overrides(agent_with_parent, candidate)

        assert result.parent_agent is None


class TestCloneWorkflowWithOverridesLoopAgent:
    """Unit tests for clone_workflow_with_overrides() with LoopAgent (US1)."""

    def test_clone_loop_agent_preserves_max_iterations(self) -> None:
        """Verify cloning LoopAgent preserves max_iterations value."""
        inner = LlmAgent(name="refiner", instruction="Refine the output")
        workflow = LoopAgent(name="loop", sub_agents=[inner], max_iterations=5)
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, LoopAgent)
        assert result.max_iterations == 5
        assert result.max_iterations == workflow.max_iterations

    def test_clone_loop_agent_applies_instruction_override_to_inner(self) -> None:
        """Verify instruction overrides are applied to inner LlmAgent."""
        inner = LlmAgent(name="refiner", instruction="Original instruction")
        workflow = LoopAgent(name="loop", sub_agents=[inner], max_iterations=3)
        candidate = {"refiner.instruction": "New refined instruction"}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, LoopAgent)
        cloned_inner = result.sub_agents[0]
        assert isinstance(cloned_inner, LlmAgent)
        assert cloned_inner.instruction == "New refined instruction"
        # Original unchanged
        assert inner.instruction == "Original instruction"

    def test_clone_loop_agent_with_multiple_sub_agents(self) -> None:
        """Verify LoopAgent with multiple sub_agents is cloned correctly."""
        agent1 = LlmAgent(name="drafter", instruction="Draft")
        agent2 = LlmAgent(name="critic", instruction="Critique")
        workflow = LoopAgent(
            name="draft_critique_loop",
            sub_agents=[agent1, agent2],
            max_iterations=3,
        )
        candidate = {
            "drafter.instruction": "Draft better",
            "critic.instruction": "Critique harder",
        }

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, LoopAgent)
        assert result.max_iterations == 3
        assert len(result.sub_agents) == 2
        assert result.sub_agents[0].instruction == "Draft better"
        assert result.sub_agents[1].instruction == "Critique harder"

    def test_clone_loop_agent_preserves_name(self) -> None:
        """Verify LoopAgent name is preserved during cloning."""
        inner = LlmAgent(name="inner", instruction="Do task")
        workflow = LoopAgent(
            name="refinement_loop",
            sub_agents=[inner],
            max_iterations=2,
        )
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert result.name == "refinement_loop"

    def test_clone_loop_agent_different_instance(self) -> None:
        """Verify cloned LoopAgent is a different instance."""
        inner = LlmAgent(name="inner", instruction="Do task")
        workflow = LoopAgent(name="loop", sub_agents=[inner], max_iterations=3)
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert result is not workflow
        assert result.sub_agents[0] is not inner


class TestCloneWorkflowWithOverridesSequentialAgent:
    """Unit tests for clone_workflow_with_overrides() with SequentialAgent."""

    def test_clone_sequential_agent_preserves_structure(self) -> None:
        """Verify cloning SequentialAgent preserves sub_agents structure."""
        agent1 = LlmAgent(name="agent1", instruction="First")
        agent2 = LlmAgent(name="agent2", instruction="Second")
        workflow = SequentialAgent(name="pipeline", sub_agents=[agent1, agent2])
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, SequentialAgent)
        assert result.name == "pipeline"
        assert len(result.sub_agents) == 2
        # Verify sub_agents are cloned (different instances)
        assert result.sub_agents[0] is not agent1
        assert result.sub_agents[1] is not agent2

    def test_clone_sequential_agent_applies_overrides_to_children(self) -> None:
        """Verify instruction overrides are applied to child LlmAgents."""
        agent1 = LlmAgent(name="agent1", instruction="Original 1")
        agent2 = LlmAgent(name="agent2", instruction="Original 2")
        workflow = SequentialAgent(name="pipeline", sub_agents=[agent1, agent2])
        candidate = {
            "agent1.instruction": "New instruction 1",
            "agent2.instruction": "New instruction 2",
        }

        result = clone_workflow_with_overrides(workflow, candidate)

        cloned_agent1 = result.sub_agents[0]
        cloned_agent2 = result.sub_agents[1]
        assert isinstance(cloned_agent1, LlmAgent)
        assert isinstance(cloned_agent2, LlmAgent)
        assert cloned_agent1.instruction == "New instruction 1"
        assert cloned_agent2.instruction == "New instruction 2"

    def test_clone_sequential_preserves_order(self) -> None:
        """Verify cloning preserves sub_agents order."""
        agents = [
            LlmAgent(name=f"agent_{i}", instruction=f"Instruction {i}")
            for i in range(5)
        ]
        workflow = SequentialAgent(name="pipeline", sub_agents=agents)
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        for i, cloned_agent in enumerate(result.sub_agents):
            assert isinstance(cloned_agent, LlmAgent)
            assert cloned_agent.name == f"agent_{i}"
            assert cloned_agent.instruction == f"Instruction {i}"


class TestCloneWorkflowWithOverridesParallelAgent:
    """Unit tests for clone_workflow_with_overrides() with ParallelAgent (US2)."""

    def test_clone_parallel_agent_preserves_structure(self) -> None:
        """T016: Verify cloning ParallelAgent preserves sub_agents structure."""
        agent1 = LlmAgent(name="researcher1", instruction="Research topic A")
        agent2 = LlmAgent(name="researcher2", instruction="Research topic B")
        agent3 = LlmAgent(name="researcher3", instruction="Research topic C")
        workflow = ParallelAgent(name="parallel_research", sub_agents=[agent1, agent2, agent3])
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, ParallelAgent)
        assert result.name == "parallel_research"
        assert len(result.sub_agents) == 3
        # Verify sub_agents are cloned (different instances)
        assert result.sub_agents[0] is not agent1
        assert result.sub_agents[1] is not agent2
        assert result.sub_agents[2] is not agent3

    def test_clone_parallel_agent_applies_overrides_to_branches(self) -> None:
        """Verify instruction overrides are applied to parallel branches."""
        agent1 = LlmAgent(name="researcher1", instruction="Original 1")
        agent2 = LlmAgent(name="researcher2", instruction="Original 2")
        workflow = ParallelAgent(name="parallel", sub_agents=[agent1, agent2])
        candidate = {
            "researcher1.instruction": "New research instruction 1",
            "researcher2.instruction": "New research instruction 2",
        }

        result = clone_workflow_with_overrides(workflow, candidate)

        cloned1 = result.sub_agents[0]
        cloned2 = result.sub_agents[1]
        assert isinstance(cloned1, LlmAgent)
        assert isinstance(cloned2, LlmAgent)
        assert cloned1.instruction == "New research instruction 1"
        assert cloned2.instruction == "New research instruction 2"
        # Originals unchanged
        assert agent1.instruction == "Original 1"
        assert agent2.instruction == "Original 2"

    def test_clone_parallel_agent_preserves_name(self) -> None:
        """Verify ParallelAgent name is preserved during cloning."""
        agent = LlmAgent(name="worker", instruction="Work")
        workflow = ParallelAgent(name="parallel_workers", sub_agents=[agent])
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert result.name == "parallel_workers"

    def test_clone_parallel_agent_different_instance(self) -> None:
        """Verify cloned ParallelAgent is a different instance."""
        agent = LlmAgent(name="agent", instruction="Do task")
        workflow = ParallelAgent(name="parallel", sub_agents=[agent])
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert result is not workflow
        assert result.sub_agents[0] is not agent

    def test_clone_parallel_agent_single_sub_agent(self) -> None:
        """Verify ParallelAgent with single sub-agent clones correctly (edge case)."""
        agent = LlmAgent(name="solo", instruction="Solo task")
        workflow = ParallelAgent(name="parallel_solo", sub_agents=[agent])
        candidate = {"solo.instruction": "Updated solo task"}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, ParallelAgent)
        assert len(result.sub_agents) == 1
        assert result.sub_agents[0].instruction == "Updated solo task"

    def test_clone_parallel_agent_preserves_type_for_concurrent_execution(self) -> None:
        """Verify cloned ParallelAgent maintains type for ADK concurrent execution.

        This is critical for US2 - ParallelAgent type must be preserved so
        ADK Runner executes sub_agents concurrently, not sequentially.
        """
        agents = [LlmAgent(name=f"agent_{i}", instruction=f"Task {i}") for i in range(3)]
        workflow = ParallelAgent(name="concurrent", sub_agents=agents)
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        # Type must be exactly ParallelAgent (not SequentialAgent or other)
        assert type(result) is ParallelAgent
        # All sub_agents should be LlmAgents
        for sub in result.sub_agents:
            assert isinstance(sub, LlmAgent)


class TestCloneWorkflowWithOverridesNestedWorkflows:
    """Unit tests for clone_workflow_with_overrides() with nested workflows (US3)."""

    def test_clone_nested_workflow_sequential_containing_parallel(self) -> None:
        """Verify cloning Sequential([Parallel([A, B]), C]) preserves structure."""
        agent_a = LlmAgent(name="agent_a", instruction="Task A")
        agent_b = LlmAgent(name="agent_b", instruction="Task B")
        agent_c = LlmAgent(name="synthesizer", instruction="Synthesize A and B")

        parallel_stage = ParallelAgent(name="parallel", sub_agents=[agent_a, agent_b])
        workflow = SequentialAgent(
            name="pipeline", sub_agents=[parallel_stage, agent_c]
        )
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        # Verify outer structure
        assert isinstance(result, SequentialAgent)
        assert len(result.sub_agents) == 2
        # Verify nested ParallelAgent is preserved
        cloned_parallel = result.sub_agents[0]
        assert isinstance(cloned_parallel, ParallelAgent)
        assert len(cloned_parallel.sub_agents) == 2
        # Verify inner LlmAgents
        assert isinstance(cloned_parallel.sub_agents[0], LlmAgent)
        assert isinstance(cloned_parallel.sub_agents[1], LlmAgent)

    def test_clone_deeply_nested_workflow_4_levels(self) -> None:
        """T022: Verify cloning workflow with 4+ levels of nesting."""
        # Level 4: LlmAgent (leaf)
        inner_agent = LlmAgent(name="inner", instruction="Innermost task")

        # Level 3: LoopAgent
        loop = LoopAgent(name="loop", sub_agents=[inner_agent], max_iterations=3)

        # Level 2: ParallelAgent containing the LoopAgent and another LlmAgent
        sibling = LlmAgent(name="sibling", instruction="Sibling task")
        parallel = ParallelAgent(name="parallel", sub_agents=[loop, sibling])

        # Level 1: SequentialAgent (root)
        finalizer = LlmAgent(name="finalizer", instruction="Final task")
        workflow = SequentialAgent(name="root", sub_agents=[parallel, finalizer])

        candidate = {
            "inner.instruction": "Updated inner",
            "sibling.instruction": "Updated sibling",
            "finalizer.instruction": "Updated finalizer",
        }

        result = clone_workflow_with_overrides(workflow, candidate)

        # Verify Level 1: SequentialAgent
        assert isinstance(result, SequentialAgent)
        assert result.name == "root"
        assert len(result.sub_agents) == 2

        # Verify Level 2: ParallelAgent
        cloned_parallel = result.sub_agents[0]
        assert isinstance(cloned_parallel, ParallelAgent)
        assert len(cloned_parallel.sub_agents) == 2

        # Verify Level 3: LoopAgent with preserved max_iterations
        cloned_loop = cloned_parallel.sub_agents[0]
        assert isinstance(cloned_loop, LoopAgent)
        assert cloned_loop.max_iterations == 3

        # Verify Level 4: LlmAgent with override applied
        cloned_inner = cloned_loop.sub_agents[0]
        assert isinstance(cloned_inner, LlmAgent)
        assert cloned_inner.instruction == "Updated inner"

        # Verify sibling and finalizer overrides
        cloned_sibling = cloned_parallel.sub_agents[1]
        assert isinstance(cloned_sibling, LlmAgent)
        assert cloned_sibling.instruction == "Updated sibling"

        cloned_finalizer = result.sub_agents[1]
        assert isinstance(cloned_finalizer, LlmAgent)
        assert cloned_finalizer.instruction == "Updated finalizer"

    def test_clone_deeply_nested_workflow_5_levels(self) -> None:
        """Verify cloning workflow with 5 levels of nesting."""
        # Level 5: LlmAgents (leaves)
        leaf_a = LlmAgent(name="leaf_a", instruction="Leaf A")
        leaf_b = LlmAgent(name="leaf_b", instruction="Leaf B")

        # Level 4: ParallelAgent
        inner_parallel = ParallelAgent(name="inner_parallel", sub_agents=[leaf_a, leaf_b])

        # Level 3: LoopAgent
        loop = LoopAgent(name="loop", sub_agents=[inner_parallel], max_iterations=2)

        # Level 2: SequentialAgent
        after_loop = LlmAgent(name="after_loop", instruction="After loop")
        inner_seq = SequentialAgent(name="inner_seq", sub_agents=[loop, after_loop])

        # Level 1: SequentialAgent (root)
        workflow = SequentialAgent(name="root", sub_agents=[inner_seq])

        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        # Verify all levels are cloned correctly
        assert isinstance(result, SequentialAgent)
        assert isinstance(result.sub_agents[0], SequentialAgent)

        inner_seq_cloned = result.sub_agents[0]
        assert isinstance(inner_seq_cloned.sub_agents[0], LoopAgent)
        assert inner_seq_cloned.sub_agents[0].max_iterations == 2

        loop_cloned = inner_seq_cloned.sub_agents[0]
        assert isinstance(loop_cloned.sub_agents[0], ParallelAgent)

        inner_parallel_cloned = loop_cloned.sub_agents[0]
        assert len(inner_parallel_cloned.sub_agents) == 2
        assert isinstance(inner_parallel_cloned.sub_agents[0], LlmAgent)
        assert isinstance(inner_parallel_cloned.sub_agents[1], LlmAgent)

    def test_clone_nested_workflow_applies_overrides_at_all_levels(self) -> None:
        """Verify instruction overrides are applied to LlmAgents at all nesting levels."""
        # Create 3-level nested workflow with LlmAgents at different levels
        level3_agent = LlmAgent(name="level3", instruction="Original level 3")
        level2_loop = LoopAgent(name="loop", sub_agents=[level3_agent], max_iterations=2)
        level1_sequential = SequentialAgent(name="seq", sub_agents=[level2_loop])

        candidate = {"level3.instruction": "Updated level 3"}

        result = clone_workflow_with_overrides(level1_sequential, candidate)

        # Navigate to the level 3 agent and verify override
        cloned_level3 = result.sub_agents[0].sub_agents[0]
        assert isinstance(cloned_level3, LlmAgent)
        assert cloned_level3.instruction == "Updated level 3"

    def test_clone_nested_workflow_different_instances_at_all_levels(self) -> None:
        """Verify cloned workflow has different instances at all nesting levels."""
        inner = LlmAgent(name="inner", instruction="Inner")
        loop = LoopAgent(name="loop", sub_agents=[inner], max_iterations=3)
        workflow = SequentialAgent(name="root", sub_agents=[loop])

        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        # All instances should be different
        assert result is not workflow
        assert result.sub_agents[0] is not loop
        assert result.sub_agents[0].sub_agents[0] is not inner


class TestCloneWorkflowEdgeCases:
    """Edge case tests for clone_workflow_with_overrides() (Phase 6)."""

    def test_clone_loop_agent_with_max_iterations_zero(self) -> None:
        """T030: Verify LoopAgent with max_iterations=0 clones correctly."""
        inner = LlmAgent(name="inner", instruction="Task")
        # Edge case: max_iterations=0 means no iterations
        workflow = LoopAgent(name="loop", sub_agents=[inner], max_iterations=0)
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, LoopAgent)
        assert result.max_iterations == 0
        assert len(result.sub_agents) == 1

    def test_clone_loop_agent_with_max_iterations_one(self) -> None:
        """Verify LoopAgent with max_iterations=1 clones correctly."""
        inner = LlmAgent(name="inner", instruction="Task")
        workflow = LoopAgent(name="loop", sub_agents=[inner], max_iterations=1)
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, LoopAgent)
        assert result.max_iterations == 1

    def test_clone_parallel_agent_single_sub_agent(self) -> None:
        """T031: Verify ParallelAgent with single sub-agent clones correctly."""
        agent = LlmAgent(name="solo", instruction="Solo task")
        # Edge case: ParallelAgent with only one sub-agent
        workflow = ParallelAgent(name="parallel_solo", sub_agents=[agent])
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, ParallelAgent)
        assert len(result.sub_agents) == 1
        assert isinstance(result.sub_agents[0], LlmAgent)
        assert result.sub_agents[0].name == "solo"

    def test_clone_llm_agents_with_same_name(self) -> None:
        """T033: Verify LlmAgents with same name get same override applied.

        When multiple LlmAgents have the same name (e.g., in different
        branches), the override for that name should be applied to all.
        Note: ADK doesn't allow the exact same agent instance twice, so
        we test with separate agents that have the same name pattern.
        """
        # ADK validates that sub-agents must have unique names in the same parent,
        # so we test across different branches in a nested workflow
        branch1_agent = LlmAgent(name="worker", instruction="Original 1")
        branch2_agent = LlmAgent(name="worker", instruction="Original 2")

        # Put them in different parallel branches (ADK allows same name in different parents)
        parallel1 = ParallelAgent(name="branch1", sub_agents=[branch1_agent])
        parallel2 = ParallelAgent(name="branch2", sub_agents=[branch2_agent])

        workflow = SequentialAgent(name="root", sub_agents=[parallel1, parallel2])
        candidate = {"worker.instruction": "Updated worker"}

        result = clone_workflow_with_overrides(workflow, candidate)

        # Both agents named "worker" should have the updated instruction
        cloned1 = result.sub_agents[0].sub_agents[0]
        cloned2 = result.sub_agents[1].sub_agents[0]
        assert cloned1.instruction == "Updated worker"
        assert cloned2.instruction == "Updated worker"
        # They should be different instances
        assert cloned1 is not cloned2

    def test_clone_empty_sequential_agent(self) -> None:
        """Verify empty SequentialAgent clones correctly."""
        workflow = SequentialAgent(name="empty_seq", sub_agents=[])
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, SequentialAgent)
        assert len(result.sub_agents) == 0

    def test_clone_empty_parallel_agent(self) -> None:
        """Verify empty ParallelAgent clones correctly."""
        workflow = ParallelAgent(name="empty_parallel", sub_agents=[])
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(workflow, candidate)

        assert isinstance(result, ParallelAgent)
        assert len(result.sub_agents) == 0

    def test_clone_llm_agent_preserves_output_key(self) -> None:
        """Verify cloning LlmAgent preserves output_key."""
        agent = LlmAgent(
            name="agent",
            instruction="Task",
            output_key="my_output",
        )
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(agent, candidate)

        assert isinstance(result, LlmAgent)
        assert result.output_key == "my_output"

    def test_clone_llm_agent_preserves_model(self) -> None:
        """Verify cloning LlmAgent preserves model configuration."""
        agent = LlmAgent(
            name="agent",
            instruction="Task",
            model="gemini-1.5-flash",
        )
        candidate: dict[str, str] = {}

        result = clone_workflow_with_overrides(agent, candidate)

        assert isinstance(result, LlmAgent)
        assert result.model == "gemini-1.5-flash"
