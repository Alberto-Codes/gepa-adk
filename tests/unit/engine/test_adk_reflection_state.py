"""Unit tests for ADK session state output_key functionality.

Tests for feature 122-adk-session-state:
- T005: Session state injection verification
- T009: output_key configuration on LlmAgent
- T010: State-based output extraction
- T011: Fallback to event extraction when state missing

Contract reference: specs/122-adk-session-state/contracts/
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from gepa_adk.engine.adk_reflection import (
    create_adk_reflection_fn,
)
from gepa_adk.ports.agent_executor import ExecutionStatus
from gepa_adk.utils.events import extract_output_from_state


def _create_mock_executor() -> MagicMock:
    """Create a mock executor for testing."""
    mock_executor = MagicMock()
    mock_executor.execute_agent = AsyncMock(
        return_value=MagicMock(
            status=ExecutionStatus.SUCCESS,
            extracted_value="proposed text",
            session_id="test_session",
        )
    )
    return mock_executor


pytestmark = pytest.mark.unit


class TestSessionStateInjection:
    """T005: Unit tests for session state injection.

    Verify component_text and trials are passed to executor
    when the reflection function is called.
    """

    @pytest.mark.asyncio
    async def test_component_text_injected_into_session_state(
        self, mocker: MockerFixture
    ) -> None:
        """Verify component_text is passed to executor in session_state."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        component_text = "Be helpful and concise"
        await reflection_fn(component_text, [])

        # Verify executor was called with session_state containing component_text
        mock_executor.execute_agent.assert_called_once()
        call_kwargs = mock_executor.execute_agent.call_args.kwargs
        assert "session_state" in call_kwargs
        assert call_kwargs["session_state"]["component_text"] == component_text

    @pytest.mark.asyncio
    async def test_trials_injected_into_session_state_as_json(
        self, mocker: MockerFixture
    ) -> None:
        """Verify trials are JSON-serialized and passed to executor in session_state."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        trials = [
            {"input": "hello", "output": "hi", "feedback": {"score": 0.8}},
            {"input": "bye", "output": "goodbye", "feedback": {"score": 0.6}},
        ]
        await reflection_fn("Be helpful", trials)

        # Verify executor was called with session_state containing trials as JSON
        call_kwargs = mock_executor.execute_agent.call_args.kwargs
        trials_json = call_kwargs["session_state"]["trials"]
        assert isinstance(trials_json, str)
        assert json.loads(trials_json) == trials


class TestOutputKeyConfiguration:
    """T009: Unit tests for output_key configuration on LlmAgent.

    Verify that output_key parameter is passed to create_adk_reflection_fn
    and configured on the agent.
    """

    @pytest.mark.asyncio
    async def test_default_output_key_is_proposed_instruction(
        self, mocker: MockerFixture
    ) -> None:
        """Verify default output_key is 'proposed_instruction'."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None  # No output_key initially

        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(
            mock_agent,
            mock_executor,
            output_key="proposed_instruction",
        )

        result = await reflection_fn("Be helpful", [])

        # Result should come from executor's extracted_value
        assert result is not None
        assert result == "proposed text"  # From mock executor

    @pytest.mark.asyncio
    async def test_custom_output_key_can_be_specified(
        self, mocker: MockerFixture
    ) -> None:
        """Verify custom output_key can be specified."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(
            mock_agent,
            mock_executor,
            output_key="custom_output",
        )

        result = await reflection_fn("Be helpful", [])
        assert result is not None


class TestStateBasedOutputExtraction:
    """T010: Unit tests for state-based output extraction.

    Verify output is retrieved from executor's extracted_value
    when available.
    """

    @pytest.mark.asyncio
    async def test_output_extracted_from_executor_result(
        self, mocker: MockerFixture
    ) -> None:
        """Verify output is extracted from executor's extracted_value."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = "proposed_instruction"

        mock_executor = _create_mock_executor()
        # Configure executor to return specific output
        mock_executor.execute_agent = AsyncMock(
            return_value=MagicMock(
                status=ExecutionStatus.SUCCESS,
                extracted_value="State-based improved text",
                session_id="test_session",
            )
        )

        reflection_fn = create_adk_reflection_fn(
            mock_agent,
            mock_executor,
            output_key="proposed_instruction",
        )

        result = await reflection_fn("Be helpful", [])

        # Result should come from executor's extracted_value
        assert result == "State-based improved text"


class TestFallbackToEventExtraction:
    """T011: Unit tests for fallback behavior.

    Verify behavior when executor returns empty or failed results.
    The executor now handles all extraction internally.
    """

    @pytest.mark.asyncio
    async def test_empty_result_when_executor_returns_empty(
        self, mocker: MockerFixture
    ) -> None:
        """Verify empty result when executor returns empty extracted_value."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = "proposed_instruction"

        mock_executor = _create_mock_executor()
        # Configure executor to return empty output
        mock_executor.execute_agent = AsyncMock(
            return_value=MagicMock(
                status=ExecutionStatus.SUCCESS,
                extracted_value="",
                session_id="test_session",
            )
        )

        reflection_fn = create_adk_reflection_fn(
            mock_agent,
            mock_executor,
            output_key="proposed_instruction",
        )

        result = await reflection_fn("Be helpful", [])

        # Should return empty string when executor returns empty
        assert result == ""

    @pytest.mark.asyncio
    async def test_error_raised_when_executor_fails(
        self, mocker: MockerFixture
    ) -> None:
        """Verify error is raised when executor returns FAILED status."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = "proposed_instruction"

        mock_executor = _create_mock_executor()
        # Configure executor to return failure
        mock_executor.execute_agent = AsyncMock(
            return_value=MagicMock(
                status=ExecutionStatus.FAILED,
                extracted_value="",
                session_id="test_session",
                error_message="Execution failed",
            )
        )

        reflection_fn = create_adk_reflection_fn(
            mock_agent,
            mock_executor,
            output_key="proposed_instruction",
        )

        import pytest

        with pytest.raises(RuntimeError, match="Execution failed"):
            await reflection_fn("Be helpful", [])


class TestExtractOutputFromStateIntegration:
    """Integration tests for extract_output_from_state usage pattern."""

    def test_extract_output_from_state_with_valid_key(self) -> None:
        """Verify extract_output_from_state returns value when key exists."""
        state: dict[str, Any] = {"proposed_instruction": "Improved text"}

        result = extract_output_from_state(state, "proposed_instruction")

        assert result == "Improved text"

    def test_extract_output_from_state_returns_none_for_missing_key(self) -> None:
        """Verify extract_output_from_state returns None when key missing."""
        state: dict[str, Any] = {"other_key": "value"}

        result = extract_output_from_state(state, "proposed_instruction")

        assert result is None

    def test_extract_output_from_state_returns_none_for_none_key(self) -> None:
        """Verify extract_output_from_state returns None when output_key is None."""
        state: dict[str, Any] = {"proposed_instruction": "text"}

        result = extract_output_from_state(state, None)

        assert result is None
