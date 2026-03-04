"""Unit tests for session state context passing (US2).

Terminology:
    - component_text: The text content of a component being evolved
    - trials: Collection of trial records for reflection

NOTE: Nothing Escapes Virtue; Excellence Requires Thoughtful, Honest Engineering
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.ports.agent_executor import ExecutionStatus

pytestmark = pytest.mark.unit


def create_mock_executor() -> MagicMock:
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


@pytest.mark.asyncio
async def test_component_text_in_session_state() -> None:
    """Test that component_text is passed in session state."""
    # Arrange: Mock agent and executor
    mock_agent = MagicMock()
    mock_agent.output_key = None

    # Create mock executor
    mock_executor = create_mock_executor()
    reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

    # Act
    component_text = "function foo() { return 1; }"
    trials = [{"input": "test", "output": "result", "feedback": {"score": 0.5}}]
    await reflection_fn(component_text, trials, "instruction")

    # Assert: executor.execute_agent called with component_text in session_state
    mock_executor.execute_agent.assert_called_once()
    call_kwargs = mock_executor.execute_agent.call_args.kwargs
    assert "session_state" in call_kwargs
    assert "component_text" in call_kwargs["session_state"]
    assert call_kwargs["session_state"]["component_text"] == component_text


@pytest.mark.asyncio
async def test_trials_in_session_state() -> None:
    """Test that trials is serialized as JSON in session state."""
    # Arrange
    mock_agent = MagicMock()
    mock_agent.output_key = None

    mock_executor = create_mock_executor()
    reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

    # Act
    trials = [
        {"input": "Hello", "output": "Hi!", "feedback": {"score": 0.8}},
        {"input": "Goodbye", "output": "Bye", "feedback": {"score": 0.6}},
    ]
    await reflection_fn("", trials, "instruction")

    # Assert: trials is JSON string in session_state
    call_kwargs = mock_executor.execute_agent.call_args.kwargs
    assert "trials" in call_kwargs["session_state"]
    trials_json = call_kwargs["session_state"]["trials"]
    assert isinstance(trials_json, str)
    parsed = json.loads(trials_json)
    assert parsed == trials


@pytest.mark.asyncio
async def test_empty_trials_creates_empty_json_array() -> None:
    """Test that empty trials list creates '[]' in session state."""
    # Arrange
    mock_agent = MagicMock()
    mock_agent.output_key = None

    mock_executor = create_mock_executor()
    reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

    # Act
    await reflection_fn("text", [], "instruction")

    # Assert
    call_kwargs = mock_executor.execute_agent.call_args.kwargs
    trials_json = call_kwargs["session_state"]["trials"]
    assert trials_json == "[]"


@pytest.mark.asyncio
async def test_session_state_keys_used() -> None:
    """Test that SESSION_STATE_KEYS constants are used for state dict keys."""
    # Arrange
    mock_agent = MagicMock()
    mock_agent.output_key = None

    mock_executor = create_mock_executor()
    reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

    # Act
    await reflection_fn(
        "code", [{"input": "test", "feedback": {"score": 0.5}}], "instruction"
    )

    # Assert: Both keys from SESSION_STATE_KEYS present
    call_kwargs = mock_executor.execute_agent.call_args.kwargs
    state = call_kwargs["session_state"]
    assert "component_text" in state
    assert "trials" in state
