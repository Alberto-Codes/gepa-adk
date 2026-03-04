"""Unit tests for ADK reflection function factory.

Tests for the simplified create_adk_reflection_fn that requires a
pre-selected reflection_agent and session_service (no auto-selection).
"""

import pytest
from pytest_mock import MockerFixture

from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.ports.agent_executor import ExecutionStatus


def _create_mock_executor(
    mocker: MockerFixture, extracted_value: str = "proposed text"
):
    """Create a mock executor for testing."""
    mock_executor = mocker.MagicMock()
    result_mock = mocker.MagicMock()
    result_mock.status = ExecutionStatus.SUCCESS
    result_mock.extracted_value = extracted_value
    result_mock.session_id = "test_session"
    mock_executor.execute_agent = mocker.AsyncMock(return_value=result_mock)
    return mock_executor


pytestmark = pytest.mark.unit


class TestCreateAdkReflectionFn:
    """Tests for create_adk_reflection_fn factory."""

    @pytest.mark.asyncio
    async def test_creates_callable_reflection_fn(self, mocker: MockerFixture) -> None:
        """Verify factory returns a callable reflection function."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None
        mock_session_service = mocker.MagicMock()
        mock_executor = _create_mock_executor(mocker)

        reflection_fn = create_adk_reflection_fn(
            reflection_agent=mock_agent,
            executor=mock_executor,
            session_service=mock_session_service,
        )

        assert callable(reflection_fn)
        result = await reflection_fn("Be helpful", [])
        assert result == "proposed text"

    @pytest.mark.asyncio
    async def test_passes_component_text_and_trials(
        self, mocker: MockerFixture
    ) -> None:
        """Verify reflection function passes data to executor via session state."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = "proposed_component_text"
        mock_session_service = mocker.MagicMock()
        mock_executor = _create_mock_executor(mocker)

        reflection_fn = create_adk_reflection_fn(
            reflection_agent=mock_agent,
            executor=mock_executor,
            session_service=mock_session_service,
        )

        trials = [{"input": "Hi", "output": "Hello", "feedback": {"score": 0.8}}]
        await reflection_fn("Be helpful", trials)

        # Verify executor was called with the agent and session state
        call_kwargs = mock_executor.execute_agent.call_args
        assert call_kwargs.kwargs["agent"] is mock_agent
        assert "component_text" in call_kwargs.kwargs["session_state"]
        assert "trials" in call_kwargs.kwargs["session_state"]

    @pytest.mark.asyncio
    async def test_configures_output_key_on_agent(self, mocker: MockerFixture) -> None:
        """Verify output_key is set on agent when not already configured."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None
        mock_session_service = mocker.MagicMock()
        mock_executor = _create_mock_executor(mocker)

        create_adk_reflection_fn(
            reflection_agent=mock_agent,
            executor=mock_executor,
            session_service=mock_session_service,
            output_key="my_output_key",
        )

        assert mock_agent.output_key == "my_output_key"

    @pytest.mark.asyncio
    async def test_does_not_overwrite_existing_output_key(
        self, mocker: MockerFixture
    ) -> None:
        """Verify existing output_key on agent is preserved."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = "existing_key"
        mock_session_service = mocker.MagicMock()
        mock_executor = _create_mock_executor(mocker)

        create_adk_reflection_fn(
            reflection_agent=mock_agent,
            executor=mock_executor,
            session_service=mock_session_service,
        )

        assert mock_agent.output_key == "existing_key"

    @pytest.mark.asyncio
    async def test_returns_empty_string_on_empty_response(
        self, mocker: MockerFixture
    ) -> None:
        """Verify empty string returned when agent produces no output."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = "proposed_component_text"
        mock_session_service = mocker.MagicMock()
        mock_executor = _create_mock_executor(mocker, extracted_value="")

        reflection_fn = create_adk_reflection_fn(
            reflection_agent=mock_agent,
            executor=mock_executor,
            session_service=mock_session_service,
        )

        result = await reflection_fn("Be helpful", [])
        assert result == ""

    @pytest.mark.asyncio
    async def test_raises_on_executor_failure(self, mocker: MockerFixture) -> None:
        """Verify RuntimeError raised when executor returns FAILED status."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = "proposed_component_text"
        mock_session_service = mocker.MagicMock()

        mock_executor = mocker.MagicMock()
        result_mock = mocker.MagicMock()
        result_mock.status = ExecutionStatus.FAILED
        result_mock.error_message = "Agent execution failed"
        result_mock.session_id = "test_session"
        mock_executor.execute_agent = mocker.AsyncMock(return_value=result_mock)

        reflection_fn = create_adk_reflection_fn(
            reflection_agent=mock_agent,
            executor=mock_executor,
            session_service=mock_session_service,
        )

        with pytest.raises(RuntimeError, match="Agent execution failed"):
            await reflection_fn("Be helpful", [])
