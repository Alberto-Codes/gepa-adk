"""Unit tests for propose() method's ADK/LiteLLM branching logic (US3).

NOTE: Nothing Escapes Virtue; Excellence Requires Thoughtful, Honest Engineering
"""

from typing import Any

import pytest
from pytest_mock import MockerFixture

from gepa_adk.domain.exceptions import EvolutionError
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_propose_uses_litellm_when_adk_fn_is_none(
    mocker: MockerFixture,
) -> None:
    """Test that propose() calls LiteLLM when adk_reflection_fn is None."""
    # Arrange
    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = "improved code"
    mock_acompletion = mocker.patch(
        "gepa_adk.engine.proposer.acompletion", return_value=mock_response
    )

    proposer = AsyncReflectiveMutationProposer(
        model="gpt-4",
        adk_reflection_fn=None,  # Explicit None
    )

    candidate: dict[str, str] = {"code": "def foo(): pass"}
    reflective_dataset: dict[str, list[dict[str, Any]]] = {
        "code": [{"issue": "missing docstring"}]
    }
    components_to_update = ["code"]

    # Act
    result = await proposer.propose(candidate, reflective_dataset, components_to_update)

    # Assert: LiteLLM called
    mock_acompletion.assert_called_once()
    assert result == {"code": "improved code"}


@pytest.mark.asyncio
async def test_propose_uses_adk_fn_when_provided(mocker: MockerFixture) -> None:
    """Test that propose() calls ADK reflection function when provided."""
    # Arrange
    mock_adk_fn = mocker.AsyncMock(return_value="adk improved code")

    proposer = AsyncReflectiveMutationProposer(
        model="gpt-4",
        adk_reflection_fn=mock_adk_fn,
    )

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
async def test_propose_does_not_call_litellm_when_adk_fn_provided(
    mocker: MockerFixture,
) -> None:
    """Test that LiteLLM is NOT called when adk_reflection_fn is provided."""
    # Arrange
    mock_adk_fn = mocker.AsyncMock(return_value="result")
    mock_acompletion = mocker.patch("gepa_adk.engine.proposer.acompletion")

    proposer = AsyncReflectiveMutationProposer(
        model="gpt-4",
        adk_reflection_fn=mock_adk_fn,
    )

    candidate = {"code": "x = 1"}
    reflective_dataset = {"code": [{"issue": "test"}]}
    components_to_update = ["code"]

    # Act
    await proposer.propose(candidate, reflective_dataset, components_to_update)

    # Assert: LiteLLM NOT called
    mock_acompletion.assert_not_called()


@pytest.mark.asyncio
async def test_propose_adk_exception_propagates(mocker: MockerFixture) -> None:
    """Test that ADK reflection function exceptions are wrapped as EvolutionError."""
    # Arrange
    mock_adk_fn = mocker.AsyncMock(side_effect=RuntimeError("ADK error"))

    proposer = AsyncReflectiveMutationProposer(
        model="gpt-4",
        adk_reflection_fn=mock_adk_fn,
    )

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

    proposer = AsyncReflectiveMutationProposer(
        model="gpt-4",
        adk_reflection_fn=mock_adk_fn,
    )

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

    proposer = AsyncReflectiveMutationProposer(
        model="gpt-4",
        adk_reflection_fn=mock_adk_fn,
    )

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

    proposer = AsyncReflectiveMutationProposer(
        model="gpt-4",
        adk_reflection_fn=mock_adk_fn,
    )

    candidate = {"code": "fallback text"}
    reflective_dataset = {"code": [{"issue": "test"}]}
    components_to_update = ["code"]

    # Act & Assert
    with pytest.raises(EvolutionError, match="non-string type"):
        await proposer.propose(candidate, reflective_dataset, components_to_update)
