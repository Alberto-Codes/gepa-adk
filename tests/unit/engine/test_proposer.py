"""Unit tests for AsyncReflectiveMutationProposer.

This module tests the AsyncReflectiveMutationProposer class which generates
text mutations via ADK reflection. Tests use mocked ADK reflection functions
to isolate the proposer's logic from external dependencies.

Note:
    These unit tests use fakes and mocks to isolate the proposer's internal
    logic from external dependencies like ADK agents.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from gepa_adk.domain.exceptions import EvolutionError
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from gepa_adk.ports.agent_executor import ExecutionStatus

pytestmark = pytest.mark.unit


def _create_mock_reflection_fn(return_value: str = "proposed text") -> AsyncMock:
    """Create a mock ADK reflection function for testing."""
    return AsyncMock(return_value=return_value)


class TestProposerInitialization:
    """Test AsyncReflectiveMutationProposer initialization."""

    def test_init_requires_adk_reflection_fn(self):
        """Verify __init__ raises ValueError when adk_reflection_fn is None."""
        with pytest.raises(ValueError, match="adk_reflection_fn is required"):
            AsyncReflectiveMutationProposer(adk_reflection_fn=None)

    def test_init_accepts_valid_reflection_fn(self):
        """Verify __init__ accepts a valid reflection function."""
        mock_fn = _create_mock_reflection_fn()
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        assert proposer.adk_reflection_fn is mock_fn


class TestProposeAsyncBehavior:
    """Test propose method async behavior (non-blocking)."""

    @pytest.mark.asyncio
    async def test_concurrent_propose_calls_execute_without_blocking(self) -> None:
        """Verify concurrent propose calls don't block each other."""
        mock_fn = _create_mock_reflection_fn("Improved instruction")
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": [{"input": "test", "feedback": "good"}]}

        # Launch multiple concurrent calls
        tasks = [
            proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )
            for _ in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        assert all(r is not None for r in results)
        assert all(r["instruction"] == "Improved instruction" for r in results)

    @pytest.mark.asyncio
    async def test_propose_calls_reflection_fn_with_correct_args(self) -> None:
        """Verify propose calls reflection_fn with component_text and trials."""
        mock_fn = _create_mock_reflection_fn("Better instruction")
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        trials = [{"input": "test", "output": "response", "feedback": "good"}]
        reflective_dataset = {"instruction": trials}

        await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        mock_fn.assert_called_once_with("Be helpful", trials, "instruction")


class TestProposePerformance:
    """Test propose method performance characteristics."""

    @pytest.mark.asyncio
    async def test_performance_none_returned_within_10ms_for_empty_dataset(self):
        """Verify None returned within 10ms for empty dataset (no reflection call)."""
        import time

        mock_fn = _create_mock_reflection_fn()
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {}  # Empty

        start = time.perf_counter()
        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result is None
        assert elapsed_ms < 10, (
            f"Empty dataset check took {elapsed_ms:.2f}ms, expected <10ms"
        )
        # Verify reflection function was not called
        mock_fn.assert_not_called()


class TestProposeEdgeCases:
    """Test propose method edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_propose_returns_none_for_missing_component(self) -> None:
        """Verify propose returns None when component not in reflective_dataset."""
        mock_fn = _create_mock_reflection_fn()
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"other_component": [{"input": "test"}]}

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        assert result is None
        mock_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_propose_returns_none_for_empty_trials(self) -> None:
        """Verify propose returns None when trials list is empty."""
        mock_fn = _create_mock_reflection_fn()
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": []}  # Empty trials

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        assert result is None
        mock_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_propose_raises_on_empty_response(self) -> None:
        """Verify propose raises EvolutionError for empty reflection response."""
        mock_fn = _create_mock_reflection_fn("")
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": [{"input": "test"}]}

        with pytest.raises(EvolutionError, match="empty string"):
            await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )

    @pytest.mark.asyncio
    async def test_propose_raises_on_non_string_response(self) -> None:
        """Verify propose raises EvolutionError for non-string response."""
        mock_fn = AsyncMock(return_value=123)  # Return int instead of str
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": [{"input": "test"}]}

        with pytest.raises(EvolutionError, match="must return a string"):
            await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )

    @pytest.mark.asyncio
    async def test_propose_wraps_reflection_exception(self) -> None:
        """Verify propose wraps reflection function exceptions in EvolutionError."""
        mock_fn = AsyncMock(side_effect=RuntimeError("Connection failed"))
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=mock_fn)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": [{"input": "test"}]}

        with pytest.raises(EvolutionError, match="RuntimeError: Connection failed"):
            await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )


def _create_mock_executor(extracted_value: str = "proposed text") -> MagicMock:
    """Create a mock executor for testing create_adk_reflection_fn."""
    mock_executor = MagicMock()
    mock_executor.execute_agent = AsyncMock(
        return_value=MagicMock(
            status=ExecutionStatus.SUCCESS,
            extracted_value=extracted_value,
            session_id="test_session",
        )
    )
    return mock_executor


class TestCreateAdkReflectionFn:
    """Unit tests for create_adk_reflection_fn factory function."""

    @pytest.mark.asyncio
    async def test_create_adk_reflection_fn_returns_callable(
        self, mocker: MockerFixture
    ) -> None:
        """Verify create_adk_reflection_fn returns async callable."""
        # Mock LlmAgent
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"

        # Create the reflection function
        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        # Verify it's callable
        assert callable(reflection_fn), "create_adk_reflection_fn must return callable"

    @pytest.mark.asyncio
    async def test_create_adk_reflection_fn_with_mocked_adk(
        self, mocker: MockerFixture
    ) -> None:
        """Verify reflection function calls executor.execute_agent with session_state."""
        # Mock ADK components
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        # Create mock executor
        mock_executor = _create_mock_executor("Improved instruction")

        # Create reflection function
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        # Call the reflection function
        result = await reflection_fn(
            "Be helpful",
            [{"score": 0.5, "output": "test"}],
            "instruction",
        )

        # Verify executor was called with session_state
        mock_executor.execute_agent.assert_called_once()
        call_kwargs = mock_executor.execute_agent.call_args.kwargs
        assert "session_state" in call_kwargs
        assert "component_text" in call_kwargs["session_state"]
        assert call_kwargs["session_state"]["component_text"] == "Be helpful"

        # Verify result is string
        assert isinstance(result, str)
        assert result == "Improved instruction"

    @pytest.mark.asyncio
    async def test_create_adk_reflection_fn_delegates_to_executor(
        self, mocker: MockerFixture
    ) -> None:
        """Verify create_adk_reflection_fn delegates to executor without session_service."""
        # Mock ADK components
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        # Create reflection function (executor handles sessions)
        mock_executor = _create_mock_executor()
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        # Call it
        await reflection_fn("test", [], "instruction")

        # Verify executor was called (it handles sessions internally)
        mock_executor.execute_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_reflection_fn_handles_empty_adk_response(
        self, mocker: MockerFixture
    ) -> None:
        """Verify reflection function handles empty ADK response."""
        mock_agent = mocker.MagicMock()
        mock_agent.output_key = None
        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session.state = {}
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mock_session
        )
        mock_session_service.get_session = mocker.AsyncMock(return_value=mock_session)

        # Mock Runner with empty response
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.actions.response_content = []  # Empty response

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        # Create and call reflection function
        mock_executor = _create_mock_executor("")
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)
        result = await reflection_fn("test", [], "instruction")

        # Should return empty string
        assert result == ""

    @pytest.mark.asyncio
    async def test_reflection_fn_serializes_feedback_as_json(
        self, mocker: MockerFixture
    ) -> None:
        """Verify reflection function JSON-serializes feedback in session_state."""
        mock_agent = mocker.MagicMock()
        mock_agent.output_key = None

        # Create and call reflection function
        mock_executor = _create_mock_executor("OK")
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)
        feedback = [{"score": 0.8, "output": "good"}]
        await reflection_fn("test", feedback, "instruction")

        # Verify executor was called with session_state containing JSON-serialized trials
        call_kwargs = mock_executor.execute_agent.call_args.kwargs
        assert "session_state" in call_kwargs
        assert "trials" in call_kwargs["session_state"]

        # Should be JSON-serializable string
        feedback_str = call_kwargs["session_state"]["trials"]
        assert isinstance(feedback_str, str)
        parsed = json.loads(feedback_str)
        assert parsed == feedback

    @pytest.mark.asyncio
    async def test_reflection_fn_extracts_instruction_from_reasoning(
        self, mocker: MockerFixture
    ) -> None:
        """Verify reflection returns raw response text."""
        mock_agent = mocker.MagicMock()
        mock_agent.output_key = None
        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session.state = {}
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mock_session
        )
        mock_session_service.get_session = mocker.AsyncMock(return_value=mock_session)

        response_text = (
            "Analysis: The current instruction is too vague and lacks constraints.\n\n"
            "Improved instruction:\n"
            "Provide concise answers, include examples when helpful, and avoid speculation.\n\n"
            "Summary: The updated instruction focuses on clarity and precision."
        )

        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = response_text
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = _create_mock_executor(response_text)
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)
        result = await reflection_fn("Be helpful", [{"score": 0.5}], "instruction")

        assert result == response_text

    @pytest.mark.asyncio
    async def test_reflection_fn_extracts_instruction_from_json(
        self, mocker: MockerFixture
    ) -> None:
        """Verify reflection returns raw JSON response text."""
        from pydantic import BaseModel

        class ReflectionOutput(BaseModel):
            improved_instruction: str

        mock_agent = mocker.MagicMock()
        mock_agent.output_schema = ReflectionOutput
        mock_agent.output_key = None

        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session.state = {}
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mock_session
        )
        mock_session_service.get_session = mocker.AsyncMock(return_value=mock_session)

        response_text = '{"improved_instruction": "Answer with numbered steps."}'

        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = response_text
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = _create_mock_executor(response_text)
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)
        result = await reflection_fn("Be helpful", [{"score": 0.5}], "instruction")

        assert result == response_text

    @pytest.mark.asyncio
    async def test_reflection_fn_stores_core_session_state(
        self, mocker: MockerFixture
    ) -> None:
        """Verify session state only contains core fields."""
        mock_agent = mocker.MagicMock()
        mock_agent.output_key = None

        mock_executor = _create_mock_executor("Improved instruction text")
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)
        await reflection_fn("Be helpful", [{"score": 0.5}], "instruction")

        # Verify executor was called with session_state containing only core fields
        call_kwargs = mock_executor.execute_agent.call_args.kwargs
        assert set(call_kwargs["session_state"].keys()) == {
            "component_text",
            "trials",
        }
