"""Unit tests for session state context passing (US2).

NOTE: Nothing Escapes Virtue; Excellence Requires Thoughtful, Honest Engineering
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gepa_adk.engine.proposer import create_adk_reflection_fn


@pytest.mark.asyncio
@patch("google.adk.Runner")
@patch("google.adk.sessions.InMemorySessionService")
async def test_current_instruction_in_session_state(
    mock_session_service_cls: MagicMock,
    mock_runner_cls: MagicMock,
) -> None:
    """Test that current_instruction is passed in session state."""
    # Arrange: Mock agent and session
    mock_agent = MagicMock()
    mock_session = MagicMock()
    mock_session.state = {}
    mock_session_instance = MagicMock()
    mock_session_instance.create_session = AsyncMock(return_value=mock_session)
    mock_session_service_cls.return_value = mock_session_instance

    # Mock Runner.run_async
    mock_runner = AsyncMock()
    mock_runner.run_async.return_value = []
    mock_runner_cls.return_value = mock_runner

    # Create reflection function
    reflection_fn = create_adk_reflection_fn(mock_agent)

    # Act
    current_text = "function foo() { return 1; }"
    feedback = [{"component": "code", "issue": "test"}]
    await reflection_fn(current_text, feedback)

    # Assert: Session created with current_instruction in state
    mock_session_instance.create_session.assert_called_once()
    call_kwargs = mock_session_instance.create_session.call_args.kwargs
    assert "state" in call_kwargs
    assert "current_instruction" in call_kwargs["state"]
    assert call_kwargs["state"]["current_instruction"] == current_text


@pytest.mark.asyncio
@patch("google.adk.Runner")
@patch("google.adk.sessions.InMemorySessionService")
async def test_execution_feedback_in_session_state(
    mock_session_service_cls: MagicMock,
    mock_runner_cls: MagicMock,
) -> None:
    """Test that execution_feedback is serialized as JSON in session state."""
    # Arrange
    mock_agent = MagicMock()
    mock_session = MagicMock()
    mock_session.state = {}
    mock_session_instance = MagicMock()
    mock_session_instance.create_session = AsyncMock(return_value=mock_session)
    mock_session_service_cls.return_value = mock_session_instance

    mock_runner = AsyncMock()
    mock_runner.run_async.return_value = []
    mock_runner_cls.return_value = mock_runner

    reflection_fn = create_adk_reflection_fn(mock_agent)

    # Act
    feedback = [
        {"component": "code", "issue": "missing return"},
        {"component": "docs", "issue": "typo"},
    ]
    await reflection_fn("", feedback)

    # Assert: execution_feedback is JSON string
    call_kwargs = mock_session_instance.create_session.call_args.kwargs
    assert "execution_feedback" in call_kwargs["state"]
    feedback_json = call_kwargs["state"]["execution_feedback"]
    assert isinstance(feedback_json, str)
    parsed = json.loads(feedback_json)
    assert parsed == feedback


@pytest.mark.asyncio
@patch("google.adk.Runner")
@patch("google.adk.sessions.InMemorySessionService")
async def test_empty_feedback_creates_empty_json_array(
    mock_session_service_cls: MagicMock,
    mock_runner_cls: MagicMock,
) -> None:
    """Test that empty feedback list creates '[]' in session state."""
    # Arrange
    mock_agent = MagicMock()
    mock_session = MagicMock()
    mock_session.state = {}
    mock_session_instance = MagicMock()
    mock_session_instance.create_session = AsyncMock(return_value=mock_session)
    mock_session_service_cls.return_value = mock_session_instance

    mock_runner = AsyncMock()
    mock_runner.run_async.return_value = []
    mock_runner_cls.return_value = mock_runner

    reflection_fn = create_adk_reflection_fn(mock_agent)

    # Act
    await reflection_fn("text", [])

    # Assert
    call_kwargs = mock_session_instance.create_session.call_args.kwargs
    feedback_json = call_kwargs["state"]["execution_feedback"]
    assert feedback_json == "[]"


@pytest.mark.asyncio
@patch("google.adk.Runner")
@patch("google.adk.sessions.InMemorySessionService")
async def test_session_state_keys_used(
    mock_session_service_cls: MagicMock,
    mock_runner_cls: MagicMock,
) -> None:
    """Test that SESSION_STATE_KEYS constants are used for state dict keys."""
    # Arrange
    mock_agent = MagicMock()
    mock_session = MagicMock()
    mock_session.state = {}
    mock_session_instance = MagicMock()
    mock_session_instance.create_session = AsyncMock(return_value=mock_session)
    mock_session_service_cls.return_value = mock_session_instance

    mock_runner = AsyncMock()
    mock_runner.run_async.return_value = []
    mock_runner_cls.return_value = mock_runner

    reflection_fn = create_adk_reflection_fn(mock_agent)

    # Act
    await reflection_fn("code", [{"issue": "test"}])

    # Assert: Both keys from SESSION_STATE_KEYS present
    call_kwargs = mock_session_instance.create_session.call_args.kwargs
    state = call_kwargs["state"]
    assert "current_instruction" in state
    assert "execution_feedback" in state
