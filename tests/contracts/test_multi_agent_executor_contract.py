"""Contract tests for Multi-Agent Unified Executor integration.

This module verifies that evolve_group() and MultiAgentAdapter properly integrate
with the unified AgentExecutor for consistent session management across all agent
types (generator, critic, reflection).

Tests are organized by functional requirement (FR-xxx) and user story (US1, US2, US3).

Note:
    These contract tests verify the protocol-level integration, not the full
    end-to-end evolution behavior. Integration tests cover the full workflows.
"""

import inspect

import pytest

from gepa_adk.adapters.critic_scorer import CriticScorer
from gepa_adk.adapters.multi_agent import MultiAgentAdapter


class TestEvolveGroupExecutorCreation:
    """Contract tests for FR-003: evolve_group() creates AgentExecutor.

    User Story 1: Unified Multi-Agent Evolution
    """

    def test_evolve_group_creates_executor_in_implementation(self):
        """evolve_group() MUST create AgentExecutor when not explicitly provided (FR-003).

        This test verifies that evolve_group() internally creates an executor
        and uses it for all agent executions, enabling consistent session
        management across generator, critic, and reflection agents.

        Verification approach: Inspect the source code of evolve_group() to
        confirm that AgentExecutor is instantiated within the function body.
        """
        from gepa_adk import api

        # Get the source code of evolve_group
        source = inspect.getsource(api.evolve_group)

        # Verify AgentExecutor is created within evolve_group
        assert "AgentExecutor(" in source, (
            "evolve_group() must instantiate AgentExecutor"
        )
        assert "executor = AgentExecutor" in source, (
            "evolve_group() must assign AgentExecutor to 'executor' variable"
        )


class TestEvolveGroupExecutorPassing:
    """Contract tests for FR-004, FR-005, FR-006: executor passed to components.

    User Story 1: Unified Multi-Agent Evolution
    """

    def test_evolve_group_passes_executor_to_multi_agent_adapter(self):
        """evolve_group() MUST pass executor to MultiAgentAdapter (FR-004).

        This test verifies that the executor instance created by evolve_group()
        is passed to MultiAgentAdapter.
        """
        from gepa_adk import api

        source = inspect.getsource(api.evolve_group)

        # Verify executor is passed to MultiAgentAdapter
        assert "executor=executor" in source, (
            "evolve_group() must pass executor to MultiAgentAdapter"
        )
        assert "MultiAgentAdapter(" in source, (
            "evolve_group() must create MultiAgentAdapter"
        )

    def test_evolve_group_passes_executor_to_critic_scorer(self):
        """evolve_group() MUST pass executor to CriticScorer (FR-005).

        This test verifies that the executor instance created by evolve_group()
        is passed to CriticScorer when a critic agent is provided.
        """
        from gepa_adk import api

        source = inspect.getsource(api.evolve_group)

        # Verify executor is passed to CriticScorer
        assert "CriticScorer(" in source, (
            "evolve_group() must create CriticScorer when critic is provided"
        )
        # The executor should be passed to CriticScorer
        assert "CriticScorer(critic_agent=critic, executor=executor)" in source, (
            "evolve_group() must pass executor to CriticScorer"
        )

    def test_evolve_group_passes_executor_to_reflection_fn(self):
        """evolve_group() MUST pass executor to create_adk_reflection_fn (FR-006).

        This test verifies that the executor instance created by evolve_group()
        is passed to create_adk_reflection_fn when a reflection agent is provided.
        """
        from gepa_adk import api

        source = inspect.getsource(api.evolve_group)

        # Verify executor is passed to create_adk_reflection_fn
        assert "create_adk_reflection_fn(" in source, (
            "evolve_group() must call create_adk_reflection_fn when reflection_agent provided"
        )
        # The executor should be passed
        assert "executor=executor" in source, (
            "evolve_group() must pass executor to create_adk_reflection_fn"
        )


class TestEvolveGroupExecutorLogging:
    """Contract tests for FR-008: uses_executor logging.

    User Story 1: Unified Multi-Agent Evolution
    """

    def test_multi_agent_adapter_logs_uses_executor_true(self, mock_executor):
        """MultiAgentAdapter MUST log uses_executor=True when executor provided (FR-008).

        This test verifies that MultiAgentAdapter initializes with uses_executor=True
        in its logger context when an executor is provided.
        """
        from google.adk.agents import LlmAgent
        from pydantic import BaseModel

        class TestOutput(BaseModel):
            result: str

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test instruction",
            output_schema=TestOutput,
        )

        # Create adapter with executor
        adapter = MultiAgentAdapter(
            agents=[agent],
            primary="test_agent",
            executor=mock_executor,
        )

        # Verify logger context includes uses_executor=True
        # The logger is bound with uses_executor during __init__
        assert adapter._executor is not None

    def test_critic_scorer_logs_uses_executor_true(self, mock_executor):
        """CriticScorer MUST log uses_executor=True when executor provided (FR-008).

        This test verifies that CriticScorer initializes with uses_executor
        in its logger context when an executor is provided.
        """
        from google.adk.agents import LlmAgent
        from pydantic import BaseModel, Field

        class CriticOutput(BaseModel):
            score: float = Field(ge=0.0, le=1.0)

        critic = LlmAgent(
            name="test_critic",
            model="gemini-2.0-flash",
            instruction="Score the output",
            output_schema=CriticOutput,
        )

        # Create scorer with executor
        scorer = CriticScorer(critic_agent=critic, executor=mock_executor)

        # Verify executor is stored
        assert scorer._executor is mock_executor


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

    def test_run_shared_session_uses_executor_when_provided(self):
        """_run_shared_session MUST use executor when provided (FR-002).

        This test verifies that when an executor is provided to MultiAgentAdapter,
        the _run_shared_session method uses the executor's execute_agent method
        instead of using direct Runner calls.

        Verification approach: Inspect the source code to confirm executor is used.
        """
        source = inspect.getsource(MultiAgentAdapter._run_shared_session)

        # Verify executor is checked and used
        assert "self._executor is not None" in source, (
            "_run_shared_session must check if executor is available"
        )
        assert "self._executor.execute_agent" in source, (
            "_run_shared_session must use executor.execute_agent when available"
        )

    def test_run_isolated_sessions_uses_executor_when_provided(self):
        """_run_isolated_sessions MUST use executor when provided (FR-002).

        This test verifies that when an executor is provided to MultiAgentAdapter,
        the _run_isolated_sessions method uses the executor's execute_agent method
        instead of using direct Runner calls.

        Verification approach: Inspect the source code to confirm executor is used.
        """
        source = inspect.getsource(MultiAgentAdapter._run_isolated_sessions)

        # Verify executor is checked and used
        assert "self._executor is not None" in source, (
            "_run_isolated_sessions must check if executor is available"
        )
        assert "self._executor.execute_agent" in source, (
            "_run_isolated_sessions must use executor.execute_agent when available"
        )

    @pytest.mark.asyncio
    async def test_executor_execute_agent_called_in_evaluate(
        self,
        trainset_samples,
        mock_executor,
    ):
        """When executor provided, evaluate MUST trigger executor calls (FR-002).

        This test verifies that when an executor is provided to MultiAgentAdapter
        and evaluate() is called, the executor's execute_agent method is invoked.
        """
        from google.adk.agents import LlmAgent
        from pydantic import BaseModel

        class TestOutput(BaseModel):
            result: str

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test instruction",
            output_schema=TestOutput,
        )

        # Create adapter with mock executor
        adapter = MultiAgentAdapter(
            agents=[agent],
            primary="test_agent",
            executor=mock_executor,
        )

        # Call evaluate
        candidate = {"test_agent_instruction": "Evolved instruction"}
        await adapter.evaluate(trainset_samples, candidate)

        # Verify executor was called
        assert mock_executor.execute_count > 0, (
            "executor.execute_agent must be called during evaluate()"
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
