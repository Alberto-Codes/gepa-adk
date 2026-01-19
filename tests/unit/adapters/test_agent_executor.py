"""Unit tests for AgentExecutor adapter.

This module tests the AgentExecutor implementation with mocked dependencies,
verifying session management, event capture, output extraction, and
error handling.

Tests follow ADR-005 three-layer testing strategy at the unit layer.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gepa_adk.adapters.agent_executor import AgentExecutor, SessionNotFoundError
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus


def _create_mock_agent(
    name: str = "test_agent",
    instruction: str = "Be helpful",
    output_key: str | None = None,
) -> MagicMock:
    """Create a mock ADK LlmAgent."""
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


def _create_mock_session(session_id: str = "test_session") -> MagicMock:
    """Create a mock ADK Session."""
    session = MagicMock()
    session.id = session_id
    session.user_id = "exec_user"
    session.state = {}
    return session


def _create_mock_event(
    is_final: bool = True,
    text: str = "Hello, world!",
) -> MagicMock:
    """Create a mock ADK Event."""
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
    """Tests for AgentExecutor initialization."""

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
    """Tests for AgentExecutor.execute_agent() method."""

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
    """Tests for session sharing functionality."""

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
    async def test_raises_session_not_found_for_invalid_session(self) -> None:
        """AgentExecutor raises SessionNotFoundError for invalid session ID."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_session.return_value = None

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()

        # Act & Assert
        with pytest.raises(SessionNotFoundError) as exc_info:
            await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                existing_session_id="invalid_session",
            )

        assert exc_info.value.session_id == "invalid_session"


@pytest.mark.unit
class TestAgentExecutorOverrides:
    """Tests for runtime configuration overrides."""

    @pytest.mark.asyncio
    async def test_instruction_override_replaces_agent_instruction(self) -> None:
        """instruction_override replaces agent instruction for single execution."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent(instruction="Original instruction")

        with (
            patch("gepa_adk.adapters.agent_executor.Runner") as mock_runner_class,
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
        """Original agent is not modified after override execution."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent(instruction="Original instruction")
        original_instruction = agent.instruction

        with (
            patch("gepa_adk.adapters.agent_executor.Runner"),
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
        """output_schema_override replaces agent schema for single execution."""
        # Arrange
        mock_service = AsyncMock()
        mock_session = _create_mock_session()
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        executor = AgentExecutor(session_service=mock_service)
        agent = _create_mock_agent()

        # Create a mock schema that looks like a Pydantic BaseModel class
        new_schema = MagicMock()

        with (
            patch("gepa_adk.adapters.agent_executor.Runner"),
            patch("google.adk.agents.LlmAgent") as mock_llm_agent_class,
            patch.object(
                executor, "_execute_with_timeout", new_callable=AsyncMock
            ) as mock_execute,
        ):
            # Set up mock LlmAgent to track instantiation args
            mock_modified_agent = MagicMock()
            mock_llm_agent_class.return_value = mock_modified_agent
            mock_execute.return_value = ([], False)

            # Act
            await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                output_schema_override=new_schema,
            )

        # Assert - LlmAgent should be created with the new schema
        llm_agent_call = mock_llm_agent_class.call_args
        assert llm_agent_call.kwargs["output_schema"] == new_schema


@pytest.mark.unit
class TestAgentExecutorTimeout:
    """Tests for timeout and error handling."""

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
    """Tests for session state injection."""

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
