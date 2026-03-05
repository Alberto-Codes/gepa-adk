"""Integration tests for reflection reasoning capture pipeline.

Tests end-to-end reasoning extraction from mock agents through the
reflection function factory, verifying that thought-tagged parts and
full text fallback are handled correctly.

Note:
    These tests exercise the integration between extract_reasoning_from_events,
    create_adk_reflection_fn, and AsyncReflectiveMutationProposer without
    requiring real LLM calls.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.integration


def _make_part(text: str, thought: bool = False) -> MagicMock:
    """Create a mock Part with text and thought attributes."""
    part = MagicMock()
    part.text = text
    part.thought = thought
    return part


def _make_final_event(parts: list[MagicMock]) -> MagicMock:
    """Create a mock final response event with content.parts."""
    event = MagicMock()
    event.is_final_response.return_value = True
    event.content.parts = parts
    event.actions.response_content = None
    return event


def _make_executor(
    extracted_value: str, captured_events: list | None = None
) -> MagicMock:
    """Create a mock executor returning an ExecutionResult with captured_events."""
    executor = MagicMock()
    result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        extracted_value=extracted_value,
        session_id="test_session",
        error_message=None,
        captured_events=captured_events,
    )
    executor.execute_agent = AsyncMock(return_value=result)
    return executor


class TestReasoningCaptureWithThoughtParts:
    """Integration: reasoning captured from thought-tagged parts."""

    @pytest.mark.asyncio
    async def test_thought_parts_captured_as_reasoning(self) -> None:
        """Verify thought-tagged parts are extracted as reasoning."""
        thought_part = _make_part("I should add constraints", thought=True)
        text_part = _make_part("Be helpful and concise", thought=False)
        event = _make_final_event([thought_part, text_part])

        agent = MagicMock()
        agent.name = "Reflector"
        agent.output_key = None
        executor = _make_executor("Be helpful and concise", [event])

        reflection_fn = create_adk_reflection_fn(agent, executor)
        proposed_text, reasoning = await reflection_fn("Be helpful", [], "instruction")

        assert proposed_text == "Be helpful and concise"
        assert reasoning == "I should add constraints"

    @pytest.mark.asyncio
    async def test_multiple_thought_parts_concatenated(self) -> None:
        """Verify multiple thought parts are joined with newlines."""
        thought1 = _make_part("Step 1: analyze", thought=True)
        thought2 = _make_part("Step 2: improve", thought=True)
        text_part = _make_part("Improved text", thought=False)
        event = _make_final_event([thought1, thought2, text_part])

        agent = MagicMock()
        agent.name = "Reflector"
        agent.output_key = None
        executor = _make_executor("Improved text", [event])

        reflection_fn = create_adk_reflection_fn(agent, executor)
        _, reasoning = await reflection_fn("Original", [], "instruction")

        assert reasoning == "Step 1: analyze\nStep 2: improve"


class TestReasoningCaptureWithoutThoughtParts:
    """Integration: reasoning falls back to full text when no thought parts."""

    @pytest.mark.asyncio
    async def test_no_thought_parts_falls_back_to_full_text(self) -> None:
        """Verify fallback to full text parts when no thought parts exist."""
        text_part = _make_part("The instruction needs more specificity")
        event = _make_final_event([text_part])

        agent = MagicMock()
        agent.name = "Reflector"
        agent.output_key = None
        executor = _make_executor("The instruction needs more specificity", [event])

        reflection_fn = create_adk_reflection_fn(agent, executor)
        _, reasoning = await reflection_fn("Be helpful", [], "instruction")

        assert reasoning == "The instruction needs more specificity"


class TestReasoningCaptureEmptyResponse:
    """Integration: reasoning is None when agent produces no events."""

    @pytest.mark.asyncio
    async def test_empty_captured_events_returns_none_reasoning(self) -> None:
        """Verify None reasoning when captured_events is empty."""
        agent = MagicMock()
        agent.name = "Reflector"
        agent.output_key = None
        executor = _make_executor("Proposed text", [])

        reflection_fn = create_adk_reflection_fn(agent, executor)
        _, reasoning = await reflection_fn("Be helpful", [], "instruction")

        assert reasoning is None

    @pytest.mark.asyncio
    async def test_no_captured_events_returns_none_reasoning(self) -> None:
        """Verify None reasoning when captured_events is None."""
        agent = MagicMock()
        agent.name = "Reflector"
        agent.output_key = None
        executor = _make_executor("Proposed text", None)

        reflection_fn = create_adk_reflection_fn(agent, executor)
        _, reasoning = await reflection_fn("Be helpful", [], "instruction")

        assert reasoning is None


class TestReasoningPipelineEndToEnd:
    """Integration: reasoning flows from reflection fn through proposer."""

    @pytest.mark.asyncio
    async def test_reasoning_stored_in_proposer_last_reasoning(self) -> None:
        """Verify reasoning flows from reflection fn to proposer.last_reasoning."""
        thought_part = _make_part("Score was low due to vagueness", thought=True)
        text_part = _make_part("Be helpful, concise, and specific", thought=False)
        event = _make_final_event([thought_part, text_part])

        agent = MagicMock()
        agent.name = "Reflector"
        agent.output_key = None
        executor = _make_executor("Be helpful, concise, and specific", [event])

        reflection_fn = create_adk_reflection_fn(agent, executor)
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=reflection_fn)

        result = await proposer.propose(
            candidate={"instruction": "Be helpful"},
            reflective_dataset={"instruction": [{"input": "test", "score": 0.3}]},
            components_to_update=["instruction"],
        )

        assert result == {"instruction": "Be helpful, concise, and specific"}
        assert proposer.last_reasoning == "Score was low due to vagueness"
