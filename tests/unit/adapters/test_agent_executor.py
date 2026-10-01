"""Unit tests for AgentExecutor adapter.

This module tests the AgentExecutor implementation with mocked dependencies,
verifying session management, event capture, output extraction, and
error handling.

Override tests use real ``LlmAgent`` instances so they observe the copy
``_apply_overrides`` returns, including every user-set field it must keep.

Tests follow ADR-005 three-layer testing strategy at the unit layer.

See Also:
    [`gepa_adk.adapters.execution.agent_executor`][]: The adapter under test.

Examples:
    ```bash
    uv run pytest tests/unit/adapters/test_agent_executor.py -q
    ```
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent
from google.genai import types
from pydantic import BaseModel

from gepa_adk.adapters.execution.agent_executor import (
    AgentExecutor,
    SessionNotFoundError,
)
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus


def _create_mock_agent(
    name: str = "test_agent",
    instruction: str = "Be helpful",
    output_key: str | None = None,
) -> MagicMock:
    """Create a mock ADK LlmAgent.

    Args:
        name: Agent name.
        instruction: Agent instruction text.
        output_key: Optional session-state output key.

    Returns:
        A MagicMock shaped like an LlmAgent.
    """
    agent = MagicMock()
    agent.name = name
    agent.model = "test-model"
    agent.instruction = instruction
    agent.output_key = output_key
    agent.output_schema = None
    agent.tools = []
    agent.before_model_callback = None
    agent.after_model_callback = None
    return agent


def _create_llm_agent(instruction: str = "Be helpful") -> LlmAgent:
    """Create a real ADK LlmAgent for override tests.

    Args:
        instruction: Instruction text for the agent.

    Returns:
        An LlmAgent named ``test_agent`` on a placeholder model.
    """
    return LlmAgent(name="test_agent", model="test-model", instruction=instruction)


class _OverrideSchema(BaseModel):
    """Output schema used by the override tests.

    Examples:
        ```python
        _OverrideSchema(answer="42")
        ```
    """

    answer: str


def _create_mock_session(session_id: str = "test_session") -> MagicMock:
    """Create a mock ADK Session.

    Args:
        session_id: Session identifier.

    Returns:
        A MagicMock shaped like an ADK Session.
    """
    session = MagicMock()
    session.id = session_id
    session.user_id = "exec_user"
    session.state = {}
    return session


def _create_mock_event(
    is_final: bool = True,
    text: str = "Hello, world!",
) -> MagicMock:
    """Create a mock ADK Event.

    Args:
        is_final: Whether the event is a final response.
        text: Text carried by the event's single part.

    Returns:
        A MagicMock shaped like an ADK Event.
    """
    event = MagicMock()
    event.is_final_response.return_value = is_final

    # Set up content.parts for text extraction
    part = MagicMock()
    part.thought = False
    part.text = text
    event.content.parts = [part]

    # Also set up actions.response_content
    event.actions.response_content = [part]

    return event


@pytest.mark.unit
class TestAgentExecutorInit:
    """Tests for AgentExecutor initialization.

    Examples:
        ```bash
        uv run pytest tests/unit/adapters/test_agent_executor.py -k TestAgentExecutorInit
        ```
    """

    def test_init_with_defaults(self) -> None:
        """AgentExecutor initializes with default session service and app name."""
        executor = AgentExecutor()

        assert executor._app_name == "gepa_executor"
        assert executor._session_service is not None

    def test_init_with_custom_session_service(self) -> None:
        """AgentExecutor accepts custom session service."""
        mock_service = MagicMock()
        executor = AgentExecutor(session_service=mock_service)

        assert executor._session_service is mock_service

    def test_init_with_custom_app_name(self) -> None:
        """AgentExecutor accepts custom app name."""
        executor = AgentExecutor(app_name="custom_app")

        assert executor._app_name == "custom_app"


@pytest.mark.unit
class TestAgentExecutorExecution:
    """Tests for AgentExecutor.execute_agent() method.

    Examples:
        ```bash
        uv run pytest tests/unit/adapters/test_agent_executor.py -k TestAgentExecutorExecution
        ```
    """

    @pytest.mark.asyncio
    async def test_execute_creates_session_and_captures_events(self) -> None:
        """AgentExecutor creates session and captures events during execution."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()
        mock_event = _create_mock_event()

        with patch.object(
            executor, "_execute_runner", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = [mock_event]

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
            )

        # Assert
        assert result.status == ExecutionStatus.SUCCESS
        assert result.session_id == "test_session"
        assert result.captured_events == [mock_event]
        mock_service.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_extracts_output_from_events(self) -> None:
        """AgentExecutor extracts output text from ADK events."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()
        mock_event = _create_mock_event(text="Generated output")

        with patch.object(
            executor, "_execute_runner", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = [mock_event]

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
            )

        # Assert
        assert result.extracted_value == "Generated output"

    @pytest.mark.asyncio
    async def test_execute_extracts_output_from_state_when_output_key(self) -> None:
        """AgentExecutor extracts output from session state when output_key is set."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_session.state = {"my_output": "State-based output"}
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent(output_key="my_output")

        with patch.object(
            executor, "_execute_runner", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = []

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
            )

        # Assert
        assert result.extracted_value == "State-based output"

    @pytest.mark.asyncio
    async def test_execute_returns_consistent_execution_result(self) -> None:
        """AgentExecutor returns consistent ExecutionResult with all fields."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session("session_123")
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()
        mock_event = _create_mock_event(text="Output")

        with patch.object(
            executor, "_execute_runner", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = [mock_event]

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
            )

        # Assert
        assert isinstance(result, ExecutionResult)
        assert result.status == ExecutionStatus.SUCCESS
        assert result.session_id == "session_123"
        assert result.extracted_value == "Output"
        assert result.error_message is None
        assert result.execution_time_seconds > 0
        assert result.captured_events == [mock_event]

    @pytest.mark.asyncio
    async def test_execute_captures_events_during_execution(self) -> None:
        """AgentExecutor captures all events during execution loop."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()

        # Multiple events
        event1 = _create_mock_event(is_final=False, text="")
        event2 = _create_mock_event(is_final=True, text="Final response")

        with patch.object(
            executor, "_execute_runner", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = [event1, event2]

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
            )

        # Assert
        assert len(result.captured_events) == 2
        assert result.extracted_value == "Final response"


@pytest.mark.unit
class TestAgentExecutorSessionSharing:
    """Tests for session sharing functionality.

    Examples:
        ```bash
        uv run pytest tests/unit/adapters/test_agent_executor.py -k TestAgentExecutorSessionSharing
        ```
    """

    @pytest.mark.asyncio
    async def test_reuses_existing_session_when_provided(self) -> None:
        """AgentExecutor retrieves existing session when existing_session_id is provided."""
        # Arrange
        mock_service = AsyncMock()
        existing_session = _create_mock_session("existing_session")
        mock_service.get_session.return_value = existing_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()

        with patch.object(
            executor, "_execute_runner", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = []

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                existing_session_id="existing_session",
            )

        # Assert
        assert result.session_id == "existing_session"
        mock_service.create_session.assert_not_called()
        mock_service.get_session.assert_called()

    @pytest.mark.asyncio
    async def test_creates_session_when_not_found(self) -> None:
        """AgentExecutor creates session when existing_session_id doesn't exist.

        Uses "get or create" semantics: if session exists, use it;
        if not, create it with the specified ID.
        """
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_session.return_value = None  # Session doesn't exist
        created_session = _create_mock_session("new_session_123")
        mock_service.create_session.return_value = created_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()

        with patch.object(
            executor, "_execute_runner", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = []

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                existing_session_id="new_session_123",
            )

        # Assert - session should be created with the specified ID
        assert result.session_id == "new_session_123"
        mock_service.create_session.assert_called_once()
        create_call = mock_service.create_session.call_args
        assert create_call.kwargs["session_id"] == "new_session_123"

    @pytest.mark.asyncio
    async def test_get_session_raises_for_invalid_session(self) -> None:
        """AgentExecutor._get_session raises SessionNotFoundError for invalid ID.

        The _get_session method still provides strict existence checking
        for cases where that behavior is needed.
        """
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_session.return_value = None

        executor = AgentExecutor(session_service=mock_service)

        # Act & Assert
        with pytest.raises(SessionNotFoundError) as exc_info:
            await executor._get_session("invalid_session", "user_id")

        assert exc_info.value.session_id == "invalid_session"

    @pytest.mark.asyncio
    async def test_get_or_create_session_returns_existing(self) -> None:
        """AgentExecutor._get_or_create_session returns existing session when found."""
        # Arrange
        mock_service = AsyncMock()
        existing_session = _create_mock_session("existing_session")
        mock_service.get_session.return_value = existing_session

        executor = AgentExecutor(session_service=mock_service)

        # Act
        session = await executor._get_or_create_session("existing_session", "user_id")

        # Assert
        assert session is existing_session
        mock_service.get_session.assert_called_once()
        mock_service.create_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_session_creates_when_not_found(self) -> None:
        """AgentExecutor._get_or_create_session creates new session when not found."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_session.return_value = None
        created_session = _create_mock_session("new_session")
        mock_service.create_session.return_value = created_session

        executor = AgentExecutor(session_service=mock_service)

        # Act
        session = await executor._get_or_create_session("new_session", "user_id")

        # Assert
        assert session is created_session
        mock_service.get_session.assert_called_once()
        mock_service.create_session.assert_called_once()
        create_call = mock_service.create_session.call_args
        assert create_call.kwargs["session_id"] == "new_session"

    @pytest.mark.asyncio
    async def test_get_or_create_session_passes_state_when_creating(self) -> None:
        """AgentExecutor._get_or_create_session passes state only when creating."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_session.return_value = None
        created_session = _create_mock_session("new_session")
        mock_service.create_session.return_value = created_session

        executor = AgentExecutor(session_service=mock_service)
        initial_state = {"key": "value"}

        # Act
        await executor._get_or_create_session(
            "new_session", "user_id", session_state=initial_state
        )

        # Assert
        create_call = mock_service.create_session.call_args
        assert create_call.kwargs["state"] == initial_state

    @pytest.mark.asyncio
    async def test_get_or_create_session_ignores_state_when_existing(self) -> None:
        """AgentExecutor._get_or_create_session ignores state when session exists."""
        # Arrange
        mock_service = AsyncMock()
        existing_session = _create_mock_session("existing_session")
        existing_session.state = {"original": "state"}
        mock_service.get_session.return_value = existing_session

        executor = AgentExecutor(session_service=mock_service)
        new_state = {"new": "state"}

        # Act
        session = await executor._get_or_create_session(
            "existing_session", "user_id", session_state=new_state
        )

        # Assert - should return existing session without modification
        assert session.state == {"original": "state"}
        mock_service.create_session.assert_not_called()


@pytest.mark.unit
class TestAgentExecutorOverrides:
    """Tests for runtime overrides applied by copying the LlmAgent.

    Examples:
        ```bash
        uv run pytest tests/unit/adapters/test_agent_executor.py -k TestAgentExecutorOverrides
        ```
    """

    @pytest.mark.asyncio
    async def test_instruction_override_replaces_agent_instruction(self) -> None:
        """instruction_override reaches the Runner on a copied real LlmAgent."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_llm_agent(instruction="Original instruction")

        with (
            patch(
                "gepa_adk.adapters.execution.agent_executor.Runner"
            ) as mock_runner_class,
            patch.object(
                executor, "_execute_with_timeout", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_execute.return_value = ([], False)

            # Act
            await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                instruction_override="New instruction",
            )

        # Assert - Runner should be created with modified agent
        runner_call = mock_runner_class.call_args
        modified_agent = runner_call.kwargs["agent"]
        assert modified_agent.instruction == "New instruction"

    @pytest.mark.asyncio
    async def test_original_agent_unchanged_after_override(self) -> None:
        """Original real LlmAgent keeps its instruction after an override."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_llm_agent(instruction="Original instruction")
        original_instruction = agent.instruction

        with (
            patch("gepa_adk.adapters.execution.agent_executor.Runner"),
            patch.object(
                executor, "_execute_with_timeout", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_execute.return_value = ([], False)

            # Act
            await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                instruction_override="New instruction",
            )

        # Assert
        assert agent.instruction == original_instruction

    @pytest.mark.asyncio
    async def test_output_schema_override_replaces_agent_schema(self) -> None:
        """The agent handed to the Runner carries output_schema_override."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = LlmAgent(name="schema_agent", model="test-model", instruction="Hi")

        with (
            patch(
                "gepa_adk.adapters.execution.agent_executor.Runner"
            ) as mock_runner_class,
            patch.object(
                executor, "_execute_with_timeout", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_execute.return_value = ([], False)

            # Act
            await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                output_schema_override=_OverrideSchema,
            )

        # Assert - the agent handed to the Runner carries the new schema
        modified_agent = mock_runner_class.call_args.kwargs["agent"]
        assert modified_agent is not agent
        assert modified_agent.output_schema is _OverrideSchema
        assert modified_agent.instruction == "Hi"
        assert agent.output_schema is None

    def test_apply_overrides_preserves_user_fields(self) -> None:
        """An instruction override keeps every other user-set LlmAgent field."""

        # Arrange
        def before_agent(callback_context: Any) -> None:
            """Do nothing; identity is what the test checks.

            Args:
                callback_context: ADK callback context, unused.
            """
            return None

        config = types.GenerateContentConfig(temperature=0.2)
        agent = LlmAgent(
            name="rich_agent",
            model="test-model",
            instruction="Original instruction",
            description="A described agent",
            generate_content_config=config,
            include_contents="none",
            before_agent_callback=before_agent,
        )
        executor = AgentExecutor(session_service=AsyncMock())

        # Act
        result = executor._apply_overrides(
            agent,
            instruction_override="New instruction",
            output_schema_override=None,
        )

        # Assert
        assert result is not agent
        assert result.instruction == "New instruction"
        assert result.description == "A described agent"
        assert result.generate_content_config == config
        assert result.include_contents == "none"
        assert result.before_agent_callback is before_agent
        assert agent.instruction == "Original instruction"
        assert agent.description == "A described agent"

    def test_apply_overrides_without_overrides_returns_same_agent(self) -> None:
        """No overrides returns the original agent object unchanged."""
        agent = LlmAgent(name="plain_agent", model="test-model", instruction="Hi")
        executor = AgentExecutor(session_service=AsyncMock())

        result = executor._apply_overrides(
            agent, instruction_override=None, output_schema_override=None
        )

        assert result is agent


@pytest.mark.unit
class TestAgentExecutorTimeout:
    """Tests for timeout and error handling.

    Examples:
        ```bash
        uv run pytest tests/unit/adapters/test_agent_executor.py -k TestAgentExecutorTimeout
        ```
    """

    @pytest.mark.asyncio
    async def test_returns_timeout_status_when_exceeded(self) -> None:
        """Execution returns TIMEOUT status when timeout exceeded."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()

        with patch.object(
            executor, "_execute_with_timeout", new_callable=AsyncMock
        ) as mock_execute:
            # Simulate timeout
            mock_execute.return_value = ([], True)

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                timeout_seconds=1,
            )

        # Assert
        assert result.status == ExecutionStatus.TIMEOUT
        assert result.error_message is not None
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_partial_events_captured_on_timeout(self) -> None:
        """Partial events are captured even on timeout."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()
        partial_event = _create_mock_event(text="Partial")

        with patch.object(
            executor, "_execute_with_timeout", new_callable=AsyncMock
        ) as mock_execute:
            # Simulate timeout with partial events
            mock_execute.return_value = ([partial_event], True)

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                timeout_seconds=1,
            )

        # Assert
        assert result.status == ExecutionStatus.TIMEOUT
        assert len(result.captured_events) == 1
        # Should still try to extract partial output
        assert result.extracted_value == "Partial"

    @pytest.mark.asyncio
    async def test_returns_failed_status_on_exception(self) -> None:
        """Execution returns FAILED status with error_message on exception."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()

        with patch.object(
            executor, "_execute_with_timeout", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = RuntimeError("Model API failed")

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
            )

        # Assert
        assert result.status == ExecutionStatus.FAILED
        assert result.error_message is not None
        assert "Model API failed" in result.error_message
        assert result.extracted_value is None

    @pytest.mark.asyncio
    async def test_events_captured_on_failure(self) -> None:
        """Events captured before failure are preserved."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()

        with patch.object(
            executor, "_execute_with_timeout", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = RuntimeError("Failed")

            # Act
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
            )

        # Assert
        assert result.status == ExecutionStatus.FAILED
        assert result.captured_events == []  # No events captured before error


@pytest.mark.unit
class TestAgentExecutorSessionState:
    """Tests for session state injection.

    Examples:
        ```bash
        uv run pytest tests/unit/adapters/test_agent_executor.py -k TestAgentExecutorSessionState
        ```
    """

    @pytest.mark.asyncio
    async def test_session_state_injected_on_creation(self) -> None:
        """session_state is passed to create_session for template substitution."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()
        session_state = {
            "component_text": "Be helpful",
            "trials": '[{"score": 0.5}]',
        }

        with patch.object(
            executor, "_execute_runner", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = []

            # Act
            await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                session_state=session_state,
            )

        # Assert
        create_call = mock_service.create_session.call_args
        assert create_call.kwargs["state"] == session_state
