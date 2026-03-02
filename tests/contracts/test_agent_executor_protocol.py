"""Contract tests for AgentExecutorProtocol.

This module verifies that AgentExecutor correctly implements the
AgentExecutorProtocol as defined in the ports layer.

Tests follow ADR-005 three-layer testing strategy at the contract layer.
"""

import pytest

from gepa_adk.ports.agent_executor import (
    AgentExecutorProtocol,
    ExecutionResult,
    ExecutionStatus,
)


@pytest.mark.contract
class TestAgentExecutorProtocolCompliance:
    """Contract tests verifying AgentExecutor implements AgentExecutorProtocol."""

    def test_agent_executor_implements_protocol(self) -> None:
        """Verify AgentExecutor is a valid AgentExecutorProtocol implementation.

        This test imports AgentExecutor and verifies it satisfies the
        @runtime_checkable protocol using isinstance().
        """
        from gepa_adk.adapters.execution.agent_executor import AgentExecutor

        executor = AgentExecutor()
        assert isinstance(executor, AgentExecutorProtocol)

    def test_execute_agent_method_exists(self) -> None:
        """Verify execute_agent method exists with correct signature."""
        from gepa_adk.adapters.execution.agent_executor import AgentExecutor

        executor = AgentExecutor()
        assert hasattr(executor, "execute_agent")
        assert callable(executor.execute_agent)

    def test_execute_agent_is_async(self) -> None:
        """Verify execute_agent is an async method."""
        import asyncio

        from gepa_adk.adapters.execution.agent_executor import AgentExecutor

        executor = AgentExecutor()
        assert asyncio.iscoroutinefunction(executor.execute_agent)


@pytest.mark.contract
class TestExecutionStatusContract:
    """Contract tests for ExecutionStatus enum."""

    def test_execution_status_values_exist(self) -> None:
        """Verify all expected status values exist."""
        assert hasattr(ExecutionStatus, "SUCCESS")
        assert hasattr(ExecutionStatus, "FAILED")
        assert hasattr(ExecutionStatus, "TIMEOUT")

    def test_execution_status_string_values(self) -> None:
        """Verify status values are lowercase strings for serialization."""
        assert ExecutionStatus.SUCCESS.value == "success"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.TIMEOUT.value == "timeout"

    def test_execution_status_is_str_enum(self) -> None:
        """Verify ExecutionStatus inherits from str for easy serialization."""
        assert isinstance(ExecutionStatus.SUCCESS, str)
        assert ExecutionStatus.SUCCESS == "success"


@pytest.mark.contract
class TestExecutionResultContract:
    """Contract tests for ExecutionResult dataclass."""

    def test_execution_result_required_fields(self) -> None:
        """Verify required fields are enforced."""
        # Should work with required fields
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id="test_session",
        )
        assert result.status == ExecutionStatus.SUCCESS
        assert result.session_id == "test_session"

    def test_execution_result_optional_fields_defaults(self) -> None:
        """Verify optional fields have correct defaults."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id="test_session",
        )
        assert result.extracted_value is None
        assert result.error_message is None
        assert result.execution_time_seconds == 0.0
        assert result.captured_events is None

    def test_execution_result_all_fields(self) -> None:
        """Verify all fields can be set."""
        events = [{"type": "test"}]
        result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            session_id="test_session",
            extracted_value="output",
            error_message="Something went wrong",
            execution_time_seconds=1.5,
            captured_events=events,
        )
        assert result.status == ExecutionStatus.FAILED
        assert result.session_id == "test_session"
        assert result.extracted_value == "output"
        assert result.error_message == "Something went wrong"
        assert result.execution_time_seconds == 1.5
        assert result.captured_events == events

    def test_execution_result_is_dataclass(self) -> None:
        """Verify ExecutionResult is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(ExecutionResult)
