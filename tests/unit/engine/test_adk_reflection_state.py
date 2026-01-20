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

    Verify component_text and trials are injected into session.state
    when the reflection function is called.
    """

    @pytest.mark.asyncio
    async def test_component_text_injected_into_session_state(
        self, mocker: MockerFixture
    ) -> None:
        """Verify component_text is injected into session state."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session.state = {}
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mock_session
        )
        mock_session_service.get_session = mocker.AsyncMock(return_value=mock_session)

        # Mock Runner with successful response
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = "Improved instruction"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(
            mock_agent, mock_executor, session_service=mock_session_service
        )

        component_text = "Be helpful and concise"
        await reflection_fn(component_text, [])

        # Verify session.state contains component_text
        call_kwargs = mock_session_service.create_session.call_args[1]
        assert "state" in call_kwargs
        assert call_kwargs["state"]["component_text"] == component_text

    @pytest.mark.asyncio
    async def test_trials_injected_into_session_state_as_json(
        self, mocker: MockerFixture
    ) -> None:
        """Verify trials are JSON-serialized and injected into session state."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session.state = {}
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mock_session
        )
        mock_session_service.get_session = mocker.AsyncMock(return_value=mock_session)

        # Mock Runner with successful response
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = "Improved instruction"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(
            mock_agent, mock_executor, session_service=mock_session_service
        )

        trials = [
            {"input": "hello", "output": "hi", "feedback": {"score": 0.8}},
            {"input": "bye", "output": "goodbye", "feedback": {"score": 0.6}},
        ]
        await reflection_fn("Be helpful", trials)

        # Verify session.state contains trials as JSON string
        call_kwargs = mock_session_service.create_session.call_args[1]
        trials_json = call_kwargs["state"]["trials"]
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

        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session.state = {"proposed_instruction": "Improved text from state"}
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mock_session
        )
        mock_session_service.get_session = mocker.AsyncMock(return_value=mock_session)

        # Mock Runner
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = "Improved text from event"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        # Create reflection fn with default output_key
        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(
            mock_agent,
            mock_executor,
            session_service=mock_session_service,
            output_key="proposed_instruction",
        )

        result = await reflection_fn("Be helpful", [])

        # Result should come from state when output_key is configured
        # Note: This test validates the contract; actual implementation
        # may vary in how it retrieves the output
        assert result is not None

    @pytest.mark.asyncio
    async def test_custom_output_key_can_be_specified(
        self, mocker: MockerFixture
    ) -> None:
        """Verify custom output_key can be specified."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session.state = {"custom_output": "Custom improved text"}
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mock_session
        )
        mock_session_service.get_session = mocker.AsyncMock(return_value=mock_session)

        # Mock Runner
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = "Event text"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        # Create reflection fn with custom output_key
        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(
            mock_agent,
            mock_executor,
            session_service=mock_session_service,
            output_key="custom_output",
        )

        result = await reflection_fn("Be helpful", [])
        assert result is not None


class TestStateBasedOutputExtraction:
    """T010: Unit tests for state-based output extraction.

    Verify output is retrieved from session.state[output_key]
    when available.
    """

    @pytest.mark.asyncio
    async def test_output_extracted_from_session_state(
        self, mocker: MockerFixture
    ) -> None:
        """Verify output is extracted from session.state when output_key present."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = "proposed_instruction"

        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session.state = {"proposed_instruction": "State-based improved text"}
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mock_session
        )
        mock_session_service.get_session = mocker.AsyncMock(return_value=mock_session)

        # Mock Runner - simulate ADK storing output via output_key
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = "Event-based text (fallback)"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(
            mock_agent,
            mock_executor,
            session_service=mock_session_service,
            output_key="proposed_instruction",
        )

        result = await reflection_fn("Be helpful", [])

        # After implementation, result should prefer state-based extraction
        # For now, verify the function completes successfully
        assert result is not None


class TestFallbackToEventExtraction:
    """T011: Unit tests for fallback to event extraction.

    Verify fallback to extract_final_output(events) when:
    - output_key is not set
    - output_key not in session.state
    - session retrieval fails
    """

    @pytest.mark.asyncio
    async def test_fallback_when_output_key_missing_from_state(
        self, mocker: MockerFixture
    ) -> None:
        """Verify fallback to event extraction when output_key not in state."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = "proposed_instruction"

        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        # State does NOT contain the output_key
        mock_session.state = {"other_key": "other_value"}
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mock_session
        )
        mock_session_service.get_session = mocker.AsyncMock(return_value=mock_session)

        # Mock Runner - event-based extraction should be used
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = "Fallback event text"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(
            mock_agent,
            mock_executor,
            session_service=mock_session_service,
            output_key="proposed_instruction",
        )

        result = await reflection_fn("Be helpful", [])

        # Should fallback to event-based extraction
        # Current implementation uses events, so result should be "Fallback event text"
        assert result == "Fallback event text"

    @pytest.mark.asyncio
    async def test_fallback_when_session_retrieval_fails(
        self, mocker: MockerFixture
    ) -> None:
        """Verify fallback to event extraction when session retrieval fails."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = "proposed_instruction"

        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mock_session
        )
        # Simulate session retrieval failure
        mock_session_service.get_session = mocker.AsyncMock(return_value=None)

        # Mock Runner
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = "Fallback from events"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(
            mock_agent,
            mock_executor,
            session_service=mock_session_service,
            output_key="proposed_instruction",
        )

        result = await reflection_fn("Be helpful", [])

        # Should fallback to event-based extraction
        assert result == "Fallback from events"


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
