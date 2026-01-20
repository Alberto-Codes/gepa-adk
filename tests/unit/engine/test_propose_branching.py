"""Unit tests for propose() method's ADK reflection behavior.

NOTE: Nothing Escapes Virtue; Excellence Requires Thoughtful, Honest Engineering
"""

import pytest
from pytest_mock import MockerFixture

from gepa_adk.domain.exceptions import EvolutionError
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_propose_requires_adk_reflection_fn() -> None:
    """Test that AsyncReflectiveMutationProposer raises ValueError if adk_reflection_fn is None."""
    # Act & Assert
    with pytest.raises(ValueError, match="adk_reflection_fn is required"):
        AsyncReflectiveMutationProposer(adk_reflection_fn=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_propose_uses_adk_fn_when_provided(mocker: MockerFixture) -> None:
    """Test that propose() calls ADK reflection function when provided."""
    # Arrange
    mock_adk_fn = mocker.AsyncMock(return_value="adk improved code")

    proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_adk_fn)

    candidate = {"code": "def bar(): pass"}
    reflective_dataset = {"code": [{"issue": "no return statement"}]}
    components_to_update = ["code"]

    # Act
    result = await proposer.propose(candidate, reflective_dataset, components_to_update)

    # Assert: ADK function called with current text and feedback
    mock_adk_fn.assert_called_once()
    call_args = mock_adk_fn.call_args
    assert call_args[0][0] == "def bar(): pass"  # current_text
    assert call_args[0][1] == [{"issue": "no return statement"}]  # feedback
    assert result == {"code": "adk improved code"}


@pytest.mark.asyncio
async def test_propose_adk_exception_propagates(mocker: MockerFixture) -> None:
    """Test that ADK reflection function exceptions are wrapped as EvolutionError."""
    # Arrange
    mock_adk_fn = mocker.AsyncMock(side_effect=RuntimeError("ADK error"))

    proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_adk_fn)

    candidate = {"code": "def test(): pass"}
    reflective_dataset = {"code": [{"issue": "test"}]}
    components_to_update = ["code"]

    # Act & Assert: Exception should be wrapped
    with pytest.raises(EvolutionError, match="Reflection agent raised exception"):
        await proposer.propose(candidate, reflective_dataset, components_to_update)


@pytest.mark.asyncio
async def test_propose_empty_feedback_skips_component(mocker: MockerFixture) -> None:
    """Test that empty feedback list still skips component (no change)."""
    # Arrange
    mock_adk_fn = mocker.AsyncMock(return_value="should not be called")

    proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_adk_fn)

    candidate = {"code": "original"}
    reflective_dataset = {"code": []}  # Empty feedback
    components_to_update = ["code"]

    # Act
    result = await proposer.propose(candidate, reflective_dataset, components_to_update)

    # Assert: No call to ADK function, no proposal made
    mock_adk_fn.assert_not_called()
    assert result is None  # Empty dataset returns None


@pytest.mark.asyncio
async def test_propose_adk_empty_response_fallback(mocker: MockerFixture) -> None:
    """Test that empty ADK response raises EvolutionError."""
    # Arrange
    mock_adk_fn = mocker.AsyncMock(return_value="")  # Empty response

    proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_adk_fn)

    candidate = {"code": "original code"}
    reflective_dataset = {"code": [{"issue": "test"}]}
    components_to_update = ["code"]

    # Act & Assert
    with pytest.raises(EvolutionError, match="empty string"):
        await proposer.propose(candidate, reflective_dataset, components_to_update)


@pytest.mark.asyncio
async def test_propose_adk_none_response_fallback(mocker: MockerFixture) -> None:
    """Test that None ADK response raises EvolutionError."""
    # Arrange
    mock_adk_fn = mocker.AsyncMock(return_value=None)

    proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_adk_fn)

    candidate = {"code": "fallback text"}
    reflective_dataset = {"code": [{"issue": "test"}]}
    components_to_update = ["code"]

    # Act & Assert
    with pytest.raises(EvolutionError, match="must return a string"):
        await proposer.propose(candidate, reflective_dataset, components_to_update)
