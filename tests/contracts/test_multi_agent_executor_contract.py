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

    def test_multi_agent_adapter_accepts_executor_parameter(self):
        """MultiAgentAdapter MUST accept executor parameter (FR-001).

        This test verifies that MultiAgentAdapter constructor accepts an
        optional executor parameter of type AgentExecutorProtocol | None
        and stores it for use during agent execution.

        Note:
            This test currently fails because MultiAgentAdapter does not
            have an executor parameter yet. Implementation is pending (T019).
        """
        pytest.skip(
            "T019 not implemented yet - executor parameter not added to MultiAgentAdapter"
        )


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

        Note:
            This test currently fails because the executor parameter and
            fallback logic do not exist yet. Implementation is pending (T019).
        """
        pytest.skip(
            "T019 not implemented yet - backward compatibility logic not implemented"
        )


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

        Note:
            This test currently fails because evolve_group() does not create
            an executor yet. Once T008 is complete, this should pass automatically.
            Implementation is pending (T028).
        """
        pytest.skip(
            "T028 not implemented yet - "
            "evolve_workflow verification pending evolve_group executor creation"
        )
