"""Protocol and types for unified agent execution.

This module defines the AgentExecutorProtocol and supporting types for
executing any ADK agent type (generator, critic, reflection) with consistent
behavior, session management, and result handling.

Attributes:
    ExecutionStatus (enum): Status of agent execution (SUCCESS/FAILED/TIMEOUT).
    ExecutionResult (dataclass): Result of an agent execution.
    AgentExecutorProtocol (protocol): Protocol for unified agent execution.

Examples:
    Using an executor:

    ```python
    from gepa_adk.ports.agent_executor import (
        AgentExecutorProtocol,
        ExecutionResult,
        ExecutionStatus,
    )

    executor: AgentExecutorProtocol = AgentExecutor()
    result = await executor.execute_agent(
        agent=my_agent,
        input_text="Hello",
        timeout_seconds=60,
    )
    if result.status == ExecutionStatus.SUCCESS:
        print(result.extracted_value)
    ```

See Also:
    - [`gepa_adk.adapters.agent_executor`][gepa_adk.adapters.agent_executor]:
        AgentExecutor implementation.

Note:
    This module follows hexagonal architecture principles. The protocol
    is defined here in the ports layer, while implementations live in
    the adapters layer.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class ExecutionStatus(str, Enum):
    """Status of agent execution.

    This enum represents the outcome status of an agent execution,
    used by ExecutionResult to indicate how the execution completed.

    Attributes:
        SUCCESS: Agent completed execution normally with valid output.
        FAILED: Agent encountered an error during execution.
        TIMEOUT: Agent execution exceeded configured timeout.

    Examples:
        Checking execution status:

        ```python
        from gepa_adk.ports.agent_executor import ExecutionStatus

        if result.status == ExecutionStatus.SUCCESS:
            print(f"Output: {result.extracted_value}")
        elif result.status == ExecutionStatus.TIMEOUT:
            print(f"Timed out after {result.execution_time_seconds}s")
        elif result.status == ExecutionStatus.FAILED:
            print(f"Error: {result.error_message}")
        ```

    Note:
        Status is determined by execution outcome, not output quality.
        A successful execution may still produce low-quality output
        that fails scoring.
    """

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ExecutionResult:
    """Result of an agent execution.

    Provides consistent return type across all agent types (generator, critic,
    reflection) with status, output, timing, and debugging information.

    Attributes:
        status (ExecutionStatus): Outcome status of the execution.
        session_id (str): ADK session identifier used for this execution.
        extracted_value (str | None): Output text extracted from agent response. None if
            agent produced no output or execution failed.
        error_message (str | None): Error details if status is FAILED or TIMEOUT. None
            for successful executions.
        execution_time_seconds (float): Duration of execution in seconds.
        captured_events (list[Any] | None): ADK events captured during execution for debugging
            and trajectory analysis. None if event capture disabled.

    Examples:
        Successful execution:

        ```python
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id="sess_123",
            extracted_value="Hello, world!",
            execution_time_seconds=1.5,
        )
        ```

        Failed execution:

        ```python
        result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            session_id="sess_456",
            error_message="Model rate limit exceeded",
            execution_time_seconds=0.2,
        )
        ```

    Note:
        The captured_events field contains raw ADK Event objects for
        debugging and trajectory recording. Events are captured even
        on timeout or failure.
    """

    status: ExecutionStatus
    session_id: str
    extracted_value: str | None = None
    error_message: str | None = None
    execution_time_seconds: float = 0.0
    captured_events: list[Any] | None = field(default=None)


@runtime_checkable
class AgentExecutorProtocol(Protocol):
    """Protocol for unified agent execution.

    Defines the interface for executing any ADK agent type (LlmAgent,
    workflow agents) with consistent behavior, session management, and
    result handling.

    This protocol enables:
    - Feature parity across generator, critic, and reflection agents
    - Dependency injection for testing
    - Single point of change for new ADK features

    Examples:
        Using an executor:

        ```python
        executor: AgentExecutorProtocol = AgentExecutor()

        result = await executor.execute_agent(
            agent=my_agent,
            input_text="Hello",
            timeout_seconds=60,
        )

        if result.status == ExecutionStatus.SUCCESS:
            print(result.extracted_value)
        ```

        With instruction override (for evolution):

        ```python
        result = await executor.execute_agent(
            agent=my_agent,
            input_text="Hello",
            instruction_override="You are a helpful assistant.",
        )
        ```

    See Also:
        - [`ExecutionResult`][gepa_adk.ports.agent_executor.ExecutionResult]:
            Return type for execute_agent.
        - [`ExecutionStatus`][gepa_adk.ports.agent_executor.ExecutionStatus]:
            Status enum for execution outcomes.

    Note:
        Implementations should validate that the agent parameter is a
        valid ADK LlmAgent. The Any type is used here to avoid coupling
        the ports layer to ADK types.
    """

    async def execute_agent(
        self,
        agent: Any,
        input_text: str,
        *,
        instruction_override: str | None = None,
        output_schema_override: Any | None = None,
        session_state: dict[str, Any] | None = None,
        existing_session_id: str | None = None,
        timeout_seconds: int = 300,
    ) -> ExecutionResult:
        """Execute an agent and return structured result.

        Runs the specified agent with the given input, optionally applying
        instruction or schema overrides for evolution scenarios. Manages
        session lifecycle and captures execution events.

        Args:
            agent: ADK LlmAgent to execute. The agent's tools, output_key,
                and other ADK features are preserved during execution.
            input_text: User message to send to the agent.
            instruction_override: If provided, replaces the agent's instruction
                for this execution only. Original agent is not modified.
            output_schema_override: If provided, replaces the agent's output
                schema for this execution only (type[BaseModel]). Used for schema evolution.
            session_state: Initial state to inject into the session. Used for
                template variable substitution (e.g., {component_text}).
            existing_session_id: If provided, reuses an existing session instead
                of creating a new one. Useful for critic accessing generator state.
            timeout_seconds: Maximum execution time in seconds. Defaults to 300.
                Execution terminates with TIMEOUT status if exceeded.

        Returns:
            ExecutionResult with status, output, and debugging information.

        Raises:
            SessionNotFoundError: If existing_session_id is provided but session
                does not exist.

        Examples:
            Basic execution:

            ```python
            result = await executor.execute_agent(
                agent=greeter,
                input_text="Hello!",
            )
            print(result.extracted_value)  # "Hello! How can I help?"
            ```

            With session state for reflection:

            ```python
            result = await executor.execute_agent(
                agent=reflector,
                input_text="Improve the instruction",
                session_state={
                    "component_text": "Be helpful.",
                    "trials": '[{"score": 0.5}]',
                },
            )
            ```

            Session sharing between agents:

            ```python
            # Generator creates session
            gen_result = await executor.execute_agent(
                agent=generator,
                input_text="Write a story.",
            )

            # Critic reuses generator's session
            critic_result = await executor.execute_agent(
                agent=critic,
                input_text=f"Evaluate: {gen_result.extracted_value}",
                existing_session_id=gen_result.session_id,
            )
            ```

        Note:
            The agent parameter is typed as Any to avoid coupling to ADK types
            in the ports layer. Implementations should validate that the agent
            is a valid LlmAgent.
        """
        ...


__all__ = [
    "ExecutionStatus",
    "ExecutionResult",
    "AgentExecutorProtocol",
]
