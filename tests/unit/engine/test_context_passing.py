"""Unit tests for session state context passing (US2).

Terminology:
    - component_text: The text content of a component being evolved
    - trials: Collection of trial records for reflection

NOTE: Nothing Escapes Virtue; Excellence Requires Thoughtful, Honest Engineering
"""

import json

import pytest
from pytest_mock import MockerFixture

from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_component_text_in_session_state(
    mocker: MockerFixture,
) -> None:
    """Test that component_text is passed in session state."""
    # Arrange: Mock agent and session
    mock_agent = mocker.MagicMock()
    mock_agent.output_key = None
    mock_session = mocker.MagicMock()
    mock_session.state = {}
    mock_session_instance = mocker.MagicMock()
    mock_session_instance.create_session = mocker.AsyncMock(return_value=mock_session)
    mock_session_instance.get_session = mocker.AsyncMock(return_value=mock_session)

    # Mock InMemorySessionService
    mocker.patch(
        "google.adk.sessions.InMemorySessionService", return_value=mock_session_instance
    )

    # Mock Runner.run_async to return async iterator
    async def mock_run_async(*args, **kwargs):
        mock_event = mocker.MagicMock()
        mock_event.content = None
        yield mock_event

    mock_runner = mocker.MagicMock()
    mock_runner.run_async = mock_run_async
    mocker.patch("google.adk.Runner", return_value=mock_runner)

    # Create reflection function
    reflection_fn = create_adk_reflection_fn(mock_agent)

    # Act
    component_text = "function foo() { return 1; }"
    trials = [{"input": "test", "output": "result", "feedback": {"score": 0.5}}]
    await reflection_fn(component_text, trials)

    # Assert: Session created with component_text in state
    mock_session_instance.create_session.assert_called_once()
    call_kwargs = mock_session_instance.create_session.call_args.kwargs
    assert "state" in call_kwargs
    assert "component_text" in call_kwargs["state"]
    assert call_kwargs["state"]["component_text"] == component_text


@pytest.mark.asyncio
async def test_trials_in_session_state(
    mocker: MockerFixture,
) -> None:
    """Test that trials is serialized as JSON in session state."""
    # Arrange
    mock_agent = mocker.MagicMock()
    mock_agent.output_key = None
    mock_session = mocker.MagicMock()
    mock_session.state = {}
    mock_session_instance = mocker.MagicMock()
    mock_session_instance.create_session = mocker.AsyncMock(return_value=mock_session)
    mock_session_instance.get_session = mocker.AsyncMock(return_value=mock_session)
    mocker.patch(
        "google.adk.sessions.InMemorySessionService", return_value=mock_session_instance
    )

    async def mock_run_async(*args, **kwargs):
        mock_event = mocker.MagicMock()
        mock_event.content = None
        yield mock_event

    mock_runner = mocker.MagicMock()
    mock_runner.run_async = mock_run_async
    mocker.patch("google.adk.Runner", return_value=mock_runner)

    reflection_fn = create_adk_reflection_fn(mock_agent)

    # Act
    trials = [
        {"input": "Hello", "output": "Hi!", "feedback": {"score": 0.8}},
        {"input": "Goodbye", "output": "Bye", "feedback": {"score": 0.6}},
    ]
    await reflection_fn("", trials)

    # Assert: trials is JSON string
    call_kwargs = mock_session_instance.create_session.call_args.kwargs
    assert "trials" in call_kwargs["state"]
    trials_json = call_kwargs["state"]["trials"]
    assert isinstance(trials_json, str)
    parsed = json.loads(trials_json)
    assert parsed == trials


@pytest.mark.asyncio
async def test_empty_trials_creates_empty_json_array(
    mocker: MockerFixture,
) -> None:
    """Test that empty trials list creates '[]' in session state."""
    # Arrange
    mock_agent = mocker.MagicMock()
    mock_agent.output_key = None
    mock_session = mocker.MagicMock()
    mock_session.state = {}
    mock_session_instance = mocker.MagicMock()
    mock_session_instance.create_session = mocker.AsyncMock(return_value=mock_session)
    mock_session_instance.get_session = mocker.AsyncMock(return_value=mock_session)
    mocker.patch(
        "google.adk.sessions.InMemorySessionService", return_value=mock_session_instance
    )

    async def mock_run_async(*args, **kwargs):
        mock_event = mocker.MagicMock()
        mock_event.content = None
        yield mock_event

    mock_runner = mocker.MagicMock()
    mock_runner.run_async = mock_run_async
    mocker.patch("google.adk.Runner", return_value=mock_runner)

    reflection_fn = create_adk_reflection_fn(mock_agent)

    # Act
    await reflection_fn("text", [])

    # Assert
    call_kwargs = mock_session_instance.create_session.call_args.kwargs
    trials_json = call_kwargs["state"]["trials"]
    assert trials_json == "[]"


@pytest.mark.asyncio
async def test_session_state_keys_used(
    mocker: MockerFixture,
) -> None:
    """Test that SESSION_STATE_KEYS constants are used for state dict keys."""
    # Arrange
    mock_agent = mocker.MagicMock()
    mock_agent.output_key = None
    mock_session = mocker.MagicMock()
    mock_session.state = {}
    mock_session_instance = mocker.MagicMock()
    mock_session_instance.create_session = mocker.AsyncMock(return_value=mock_session)
    mock_session_instance.get_session = mocker.AsyncMock(return_value=mock_session)
    mocker.patch(
        "google.adk.sessions.InMemorySessionService", return_value=mock_session_instance
    )

    async def mock_run_async(*args, **kwargs):
        mock_event = mocker.MagicMock()
        mock_event.content = None
        yield mock_event

    mock_runner = mocker.MagicMock()
    mock_runner.run_async = mock_run_async
    mocker.patch("google.adk.Runner", return_value=mock_runner)

    reflection_fn = create_adk_reflection_fn(mock_agent)

    # Act
    await reflection_fn("code", [{"input": "test", "feedback": {"score": 0.5}}])

    # Assert: Both keys from SESSION_STATE_KEYS present
    call_kwargs = mock_session_instance.create_session.call_args.kwargs
    state = call_kwargs["state"]
    assert "component_text" in state
    assert "trials" in state
