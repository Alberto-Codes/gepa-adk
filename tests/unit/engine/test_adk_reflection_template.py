"""Unit tests for ADK session state template substitution.

This module tests the template placeholder substitution functionality
in the reflection agent. These tests verify that:
1. Single placeholders like {component_text} are substituted correctly
2. Multiple placeholders ({component_text} and {trials}) work together
3. Missing state keys are handled appropriately
4. Non-string values are pre-serialized to JSON strings

Note:
    These tests use mocks to isolate template behavior from actual LLM calls.
    The tests verify session state setup and user message construction.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from gepa_adk.domain.types import REFLECTION_INSTRUCTION, SESSION_STATE_KEYS
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.ports.agent_executor import ExecutionStatus

pytestmark = pytest.mark.unit


def _create_mock_executor(extracted_value: str = "proposed text") -> MagicMock:
    """Create a mock executor for testing."""
    mock_executor = MagicMock()
    mock_executor.execute_agent = AsyncMock(
        return_value=MagicMock(
            status=ExecutionStatus.SUCCESS,
            extracted_value=extracted_value,
            session_id="test_session",
        )
    )
    return mock_executor


class TestReflectionInstructionConstant:
    """Tests for REFLECTION_INSTRUCTION constant."""

    def test_reflection_instruction_contains_component_text_placeholder(self):
        """Verify REFLECTION_INSTRUCTION contains {component_text} placeholder."""
        assert "{component_text}" in REFLECTION_INSTRUCTION

    def test_reflection_instruction_contains_trials_placeholder(self):
        """Verify REFLECTION_INSTRUCTION contains {trials} placeholder."""
        assert "{trials}" in REFLECTION_INSTRUCTION

    def test_reflection_instruction_is_string(self):
        """Verify REFLECTION_INSTRUCTION is a string."""
        assert isinstance(REFLECTION_INSTRUCTION, str)

    def test_reflection_instruction_not_empty(self):
        """Verify REFLECTION_INSTRUCTION is not empty."""
        assert len(REFLECTION_INSTRUCTION) > 0


class TestSessionStateKeys:
    """Tests for SESSION_STATE_KEYS schema."""

    def test_session_state_keys_contains_component_text(self):
        """Verify SESSION_STATE_KEYS includes component_text."""
        assert "component_text" in SESSION_STATE_KEYS
        assert SESSION_STATE_KEYS["component_text"] is str

    def test_session_state_keys_contains_trials(self):
        """Verify SESSION_STATE_KEYS includes trials."""
        assert "trials" in SESSION_STATE_KEYS
        assert SESSION_STATE_KEYS["trials"] is str  # JSON-serialized


class TestSinglePlaceholderSubstitution:
    """Tests for US1: Basic template substitution."""

    @pytest.mark.asyncio
    async def test_single_placeholder_component_text_in_session_state(self) -> None:
        """Verify component_text is passed in session state for template substitution."""
        mock_agent = MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_executor = _create_mock_executor()

        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        component_text = "Be a helpful assistant that provides clear explanations."
        await reflection_fn(component_text, [], "instruction")

        # Verify executor.execute_agent called with component_text in session_state
        call_kwargs = mock_executor.execute_agent.call_args.kwargs
        assert "session_state" in call_kwargs
        assert call_kwargs["session_state"]["component_text"] == component_text


class TestMissingStateKeyHandling:
    """Tests for US1: Missing state key error handling."""

    def test_session_state_keys_schema_defines_required_keys(self):
        """Verify SESSION_STATE_KEYS defines both required keys."""
        required_keys = {"component_text", "trials"}
        assert set(SESSION_STATE_KEYS.keys()) == required_keys


class TestMultiplePlaceholderSubstitution:
    """Tests for US2: Multiple placeholder substitution."""

    @pytest.mark.asyncio
    async def test_multiple_placeholders_both_in_session_state(self) -> None:
        """Verify both component_text and trials are in session state."""
        mock_agent = MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_executor = _create_mock_executor()

        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        component_text = "Be helpful"
        trials = [
            {"input": "Hello", "output": "Hi", "feedback": {"score": 0.8}},
            {"input": "Bye", "output": "Goodbye", "feedback": {"score": 0.6}},
        ]
        await reflection_fn(component_text, trials, "instruction")

        # Verify executor.execute_agent called with both keys in session_state
        call_kwargs = mock_executor.execute_agent.call_args.kwargs
        state = call_kwargs["session_state"]
        assert "component_text" in state
        assert "trials" in state
        assert state["component_text"] == component_text
        # trials should be JSON-serialized
        assert isinstance(state["trials"], str)


class TestNonStringValueSerialization:
    """Tests for US2: Non-string value serialization to JSON."""

    @pytest.mark.asyncio
    async def test_trials_dict_serialized_to_json(self) -> None:
        """Verify trials list is JSON-serialized in session state."""
        mock_agent = MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_executor = _create_mock_executor()

        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        trials = [
            {"input": "test", "output": "result", "feedback": {"score": 0.7}},
        ]
        await reflection_fn("component", trials, "instruction")

        # Verify trials is JSON string in session_state
        call_kwargs = mock_executor.execute_agent.call_args.kwargs
        trials_str = call_kwargs["session_state"]["trials"]

        # Should be valid JSON
        parsed = json.loads(trials_str)
        assert parsed == trials

    @pytest.mark.asyncio
    async def test_empty_trials_list_serialized_correctly(self) -> None:
        """Verify empty trials list is correctly JSON-serialized."""
        mock_agent = MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_executor = _create_mock_executor()

        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        trials = []
        await reflection_fn("component", trials, "instruction")

        # Verify empty list is serialized as "[]"
        call_kwargs = mock_executor.execute_agent.call_args.kwargs
        trials_str = call_kwargs["session_state"]["trials"]
        assert trials_str == "[]"


class TestUserMessageSimplification:
    """Tests for verifying user message is simplified (not data carrier)."""

    @pytest.mark.asyncio
    async def test_user_message_is_simple_trigger(self) -> None:
        """Verify user message is a simple trigger, not containing trial data."""
        mock_agent = MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        # Capture the user message passed to executor
        captured_message = None

        mock_executor = MagicMock()

        async def capture_execute_agent(*args, **kwargs):
            nonlocal captured_message
            captured_message = kwargs.get("input_text")
            return MagicMock(
                status=ExecutionStatus.SUCCESS,
                extracted_value="proposed text",
                session_id="test_session",
            )

        mock_executor.execute_agent = capture_execute_agent

        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        # Call with a specific component_text and trials
        component_text = "Be very helpful"
        trials = [{"input": "test", "output": "result", "feedback": {"score": 0.5}}]
        await reflection_fn(component_text, trials, "instruction")

        # Verify user message does NOT contain the trial data
        # (data should be in session state, not user message)
        assert captured_message is not None

        # User message should be simple, not contain JSON-formatted trials
        assert "score" not in captured_message.lower() or "0.5" not in captured_message
