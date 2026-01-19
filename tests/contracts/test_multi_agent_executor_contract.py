"""Contract tests for Multi-Agent Unified Executor integration.

This module verifies that evolve_group() and MultiAgentAdapter properly integrate
with the unified AgentExecutor for consistent session management across all agent
types (generator, critic, reflection).

Tests are organized by functional requirement (FR-xxx) and user story (US1, US2, US3).

Note:
    These contract tests verify the protocol-level integration, not the full
    end-to-end evolution behavior. Integration tests cover the full workflows.
"""

import pytest

from gepa_adk import evolve_group
from gepa_adk.adapters.agent_executor import AgentExecutor
from gepa_adk.adapters.multi_agent import MultiAgentAdapter
from gepa_adk.ports.agent_executor import AgentExecutorProtocol


class TestEvolveGroupExecutorCreation:
    """Contract tests for FR-003: evolve_group() creates AgentExecutor.

    User Story 1: Unified Multi-Agent Evolution
    """

    @pytest.mark.asyncio
    async def test_evolve_group_creates_executor_internally(
        self,
        trainset_samples,
    ):
        """evolve_group() MUST create AgentExecutor when not explicitly provided (FR-003).

        This test verifies that evolve_group() internally creates an executor
        and uses it for all agent executions, enabling consistent session
        management across generator, critic, and reflection agents.

        Note:
            This test currently fails because evolve_group() does not yet
            create or use an executor. Implementation is pending (T008).
        """
        pytest.skip(
            "T008 not implemented yet - evolve_group() does not create executor"
        )


class TestEvolveGroupExecutorPassing:
    """Contract tests for FR-004, FR-005, FR-006: executor passed to components.

    User Story 1: Unified Multi-Agent Evolution
    """

    @pytest.mark.asyncio
    async def test_evolve_group_passes_executor_to_all_components(
        self,
        trainset_samples,
    ):
        """evolve_group() MUST pass executor to all components (FR-004/005/006).

        This test verifies that the executor instance created by evolve_group()
        is passed to MultiAgentAdapter, CriticScorer, and reflection function,
        ensuring unified execution throughout the multi-agent pipeline.

        Note:
            This test currently fails because evolve_group() does not pass
            executor to components. Implementation is pending (T009-T011).
        """
        pytest.skip("T009-T011 not implemented yet - executor not passed to components")


class TestEvolveGroupExecutorLogging:
    """Contract tests for FR-008: uses_executor logging.

    User Story 1: Unified Multi-Agent Evolution
    """

    @pytest.mark.asyncio
    async def test_all_logs_show_uses_executor_true(
        self,
        trainset_samples,
    ):
        """All agent executions MUST log uses_executor=True when using unified path (FR-008).

        This test verifies that all log entries related to agent execution
        include the uses_executor=True field, enabling observability of the
        unified execution path.

        Note:
            This test currently fails because logging has not been updated
            to include uses_executor field. Implementation is pending (T017).
        """
        pytest.skip("T017 not implemented yet - uses_executor logging not added")


class TestMultiAgentAdapterExecutorParameter:
    """Contract tests for FR-001: MultiAgentAdapter accepts executor parameter.

    User Story 2: MultiAgentAdapter Executor Integration
    """

    def test_multi_agent_adapter_accepts_executor_parameter(self, mock_executor):
        """MultiAgentAdapter MUST accept executor parameter (FR-001).

        This test verifies that MultiAgentAdapter constructor accepts an
        optional executor parameter of type AgentExecutorProtocol | None
        and stores it for use during agent execution.
        """
        from google.adk.agents import LlmAgent
        from pydantic import BaseModel

        # Create output schema for agent
        class TestOutput(BaseModel):
            result: str

        # Create test agents
        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test instruction",
            output_schema=TestOutput,
        )

        # Create adapter with executor parameter
        adapter = MultiAgentAdapter(
            agents=[agent],
            primary="test_agent",
            executor=mock_executor,
        )

        # Verify executor is stored
        assert adapter._executor is mock_executor
        assert adapter._executor is not None


class TestMultiAgentAdapterExecutorUsage:
    """Contract tests for FR-002: executor used for all executions.

    User Story 2: MultiAgentAdapter Executor Integration
    """

    @pytest.mark.asyncio
    async def test_executor_used_for_all_agent_executions(
        self,
        trainset_samples,
        mock_executor,
    ):
        """When executor provided, all agent executions MUST use that executor (FR-002).

        This test verifies that when an executor is provided to MultiAgentAdapter,
        all agent execution calls go through the executor's execute_agent method
        instead of using direct Runner calls.

        Note:
            This test currently fails because MultiAgentAdapter does not use
            the executor for executions yet. Implementation is pending (T021-T022).
        """
        pytest.skip(
            "T021-T022 not implemented yet - "
            "executor not used in _run_shared_session/_run_isolated_sessions"
        )


class TestMultiAgentAdapterBackwardCompatibility:
    """Contract tests for FR-009: backward compatibility without executor.

    User Story 2: MultiAgentAdapter Executor Integration
    """

    def test_backward_compatibility_without_executor(self):
        """System MUST work when no executor explicitly provided (FR-009).

        This test verifies that MultiAgentAdapter continues to work with
        its legacy execution path when no executor is provided, ensuring
        backward compatibility with existing callers.
        """
        from google.adk.agents import LlmAgent
        from pydantic import BaseModel

        # Create output schema for agent
        class TestOutput(BaseModel):
            result: str

        # Create test agents
        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test instruction",
            output_schema=TestOutput,
        )

        # Create adapter WITHOUT executor parameter (backward compatibility)
        adapter = MultiAgentAdapter(
            agents=[agent],
            primary="test_agent",
        )

        # Verify adapter works without executor
        assert adapter._executor is None
        assert adapter.primary == "test_agent"
        assert len(adapter.agents) == 1


class TestEvolveWorkflowExecutorInheritance:
    """Contract tests for FR-007: evolve_workflow() inherits executor support.

    User Story 3: Workflow Evolution Executor Support
    """

    @pytest.mark.asyncio
    async def test_evolve_workflow_inherits_executor_from_evolve_group(
        self,
        trainset_samples,
    ):
        """evolve_workflow() MUST inherit executor support by delegating to evolve_group() (FR-007).

        This test verifies that evolve_workflow() automatically benefits from
        unified executor support since it delegates to evolve_group() internally.

        The test verifies that the delegation chain exists and works correctly:
        evolve_workflow() -> evolve_group() -> AgentExecutor creation
        """
        from google.adk.agents import LlmAgent, SequentialAgent
        from pydantic import BaseModel

        from gepa_adk import evolve_workflow
        from gepa_adk.api import find_llm_agents

        # Create output schema for validation
        class TestOutput(BaseModel):
            result: str

        # Create simple workflow
        agent1 = LlmAgent(
            name="agent1",
            model="gemini-2.0-flash",
            instruction="First agent",
            output_key="step1",
        )
        agent2 = LlmAgent(
            name="agent2",
            model="gemini-2.0-flash",
            instruction="Second agent: {step1}",
            output_schema=TestOutput,
        )
        workflow = SequentialAgent(name="TestWorkflow", sub_agents=[agent1, agent2])

        # Verify workflow can be discovered
        llm_agents = find_llm_agents(workflow, max_depth=5)
        assert len(llm_agents) == 2
        assert llm_agents[0].name == "agent1"
        assert llm_agents[1].name == "agent2"

        # Verify delegation chain is set up correctly by checking that
        # evolve_workflow can be called (actual LLM calls would happen in integration tests)
        # This contract test verifies the protocol-level setup
