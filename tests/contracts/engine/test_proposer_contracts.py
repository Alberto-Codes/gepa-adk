"""Contract tests for AsyncReflectiveMutationProposer.

This module tests the behavioral guarantees and contracts of the mutation
proposer, ensuring it meets its API specification requirements. These tests
focus on the proposer's promises to callers rather than implementation details.

Note:
    These contract tests verify behavior using mock ADK reflection functions
    to isolate the proposer's logic from external dependencies.
"""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from pytest_mock import MockerFixture

from gepa_adk.domain.exceptions import EvolutionError
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

pytestmark = pytest.mark.contract


# Type alias for reflection function
ReflectionFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]


@pytest.fixture
def mock_reflection_fn(mocker: MockerFixture) -> ReflectionFn:
    """Create a mock ADK reflection function."""
    return mocker.AsyncMock(return_value="Improved instruction text")


class TestProposerInitialization:
    """Test proposer initialization and validation."""

    def test_requires_adk_reflection_fn(self) -> None:
        """Verify proposer requires adk_reflection_fn parameter."""
        with pytest.raises(ValueError, match="adk_reflection_fn is required"):
            AsyncReflectiveMutationProposer(adk_reflection_fn=None)  # type: ignore

    def test_accepts_valid_reflection_fn(
        self, mock_reflection_fn: ReflectionFn
    ) -> None:
        """Verify proposer accepts a valid reflection function."""
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)
        assert proposer.adk_reflection_fn is mock_reflection_fn


class TestUserStory1ProposeReturnsDict:
    """Test US1: Proposer returns dict with mutated text given valid input."""

    @pytest.mark.asyncio
    async def test_propose_returns_dict_with_mutated_text(
        self, mock_reflection_fn: ReflectionFn
    ) -> None:
        """Verify propose returns dict with mutated instruction."""
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [{"input": "What is 2+2?", "feedback": "Add explanations"}]
        }

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        assert result is not None
        assert isinstance(result, dict)
        assert "instruction" in result
        assert result["instruction"] == "Improved instruction text"


class TestUserStory3EmptyDataset:
    """Test US3: Proposer returns None for empty reflective dataset."""

    @pytest.mark.asyncio
    async def test_propose_returns_none_for_empty_dict(
        self, mock_reflection_fn: ReflectionFn
    ) -> None:
        """Verify propose returns None when reflective_dataset is empty dict."""
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {}  # Empty

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        assert result is None
        # Verify no reflection calls were made (cost optimization)
        mock_reflection_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_propose_returns_none_for_empty_feedback_list(
        self, mock_reflection_fn: ReflectionFn
    ) -> None:
        """Verify propose returns None when component has empty feedback list."""
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": []}  # Empty list

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        assert result is None
        mock_reflection_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_reflection_calls_when_returning_none(
        self, mock_reflection_fn: ReflectionFn
    ) -> None:
        """Verify no reflection calls made when returning None (cost optimization)."""
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {}

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        assert result is None
        mock_reflection_fn.assert_not_called()


class TestEdgeCaseEmptyReflectionResponse:
    """Test edge case: Empty reflection response raises EvolutionError."""

    @pytest.mark.asyncio
    async def test_empty_reflection_response_raises_error(
        self, mocker: MockerFixture
    ) -> None:
        """Verify empty reflection response raises EvolutionError."""
        mock_fn = mocker.AsyncMock(return_value="")
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": [{"input": "test", "feedback": "good"}]}

        with pytest.raises(EvolutionError, match="returned empty string"):
            await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )


class TestEdgeCaseInvalidReflectionResponse:
    """Test edge case: Invalid reflection response type raises EvolutionError."""

    @pytest.mark.asyncio
    async def test_non_string_reflection_response_raises_error(
        self, mocker: MockerFixture
    ) -> None:
        """Verify non-string reflection response raises EvolutionError."""
        mock_fn = mocker.AsyncMock(return_value=123)  # Returns int instead of str
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": [{"input": "test", "feedback": "good"}]}

        with pytest.raises(EvolutionError, match="must return a string"):
            await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )


class TestEdgeCaseComponentNotInCandidate:
    """Test edge case: Component not in candidate is skipped silently."""

    @pytest.mark.asyncio
    async def test_component_not_in_candidate_is_skipped(
        self, mock_reflection_fn: ReflectionFn
    ) -> None:
        """Verify component not in candidate dict is skipped without error."""
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [{"input": "test", "feedback": "good"}],
            "context": [{"input": "test2", "feedback": "ok"}],  # Not in candidate
        }

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction", "context"],
        )

        # Should only have instruction, context skipped
        assert result is not None
        assert "instruction" in result
        assert "context" not in result


class TestEdgeCaseReflectionFnException:
    """Test edge case: Reflection function exceptions are wrapped in EvolutionError."""

    @pytest.mark.asyncio
    async def test_reflection_exception_wrapped_in_evolution_error(
        self, mocker: MockerFixture
    ) -> None:
        """Verify reflection function exceptions are wrapped in EvolutionError."""
        mock_fn = mocker.AsyncMock(side_effect=RuntimeError("Connection failed"))
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": [{"input": "test", "feedback": "good"}]}

        with pytest.raises(EvolutionError, match="Connection failed"):
            await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )
