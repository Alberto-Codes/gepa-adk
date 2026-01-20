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
from pytest_mock import MockerFixture

from gepa_adk.engine.adk_reflection import (
    REFLECTION_INSTRUCTION,
    SESSION_STATE_KEYS,
    create_adk_reflection_fn,
)
from gepa_adk.ports.agent_executor import ExecutionStatus

pytestmark = pytest.mark.unit


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
    async def test_single_placeholder_component_text_in_session_state(
        self, mocker: MockerFixture
    ) -> None:
        """Verify component_text is passed in session state for template substitution."""
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
        mock_part.text = "Improved text"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = MagicMock()
        mock_executor.execute_agent = AsyncMock(
            return_value=MagicMock(
                status=ExecutionStatus.SUCCESS,
                extracted_value="proposed text",
                session_id="test_session",
            )
        )

        reflection_fn = create_adk_reflection_fn(
            mock_agent, mock_executor, session_service=mock_session_service
        )

        component_text = "Be a helpful assistant that provides clear explanations."
        await reflection_fn(component_text, [])

        # Verify session state contains component_text
        call_kwargs = mock_session_service.create_session.call_args[1]
        assert "state" in call_kwargs
        assert call_kwargs["state"]["component_text"] == component_text


class TestMissingStateKeyHandling:
    """Tests for US1: Missing state key error handling."""

    def test_session_state_keys_schema_defines_required_keys(self):
        """Verify SESSION_STATE_KEYS defines both required keys."""
        required_keys = {"component_text", "trials"}
        assert set(SESSION_STATE_KEYS.keys()) == required_keys


class TestMultiplePlaceholderSubstitution:
    """Tests for US2: Multiple placeholder substitution."""

    @pytest.mark.asyncio
    async def test_multiple_placeholders_both_in_session_state(
        self, mocker: MockerFixture
    ) -> None:
        """Verify both component_text and trials are in session state."""
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
        mock_part.text = "Improved text"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = MagicMock()
        mock_executor.execute_agent = AsyncMock(
            return_value=MagicMock(
                status=ExecutionStatus.SUCCESS,
                extracted_value="proposed text",
                session_id="test_session",
            )
        )

        reflection_fn = create_adk_reflection_fn(
            mock_agent, mock_executor, session_service=mock_session_service
        )

        component_text = "Be helpful"
        trials = [
            {"input": "Hello", "output": "Hi", "feedback": {"score": 0.8}},
            {"input": "Bye", "output": "Goodbye", "feedback": {"score": 0.6}},
        ]
        await reflection_fn(component_text, trials)

        # Verify session state contains both keys
        call_kwargs = mock_session_service.create_session.call_args[1]
        state = call_kwargs["state"]
        assert "component_text" in state
        assert "trials" in state
        assert state["component_text"] == component_text
        # trials should be JSON-serialized
        assert isinstance(state["trials"], str)


class TestNonStringValueSerialization:
    """Tests for US2: Non-string value serialization to JSON."""

    @pytest.mark.asyncio
    async def test_trials_dict_serialized_to_json(self, mocker: MockerFixture) -> None:
        """Verify trials list is JSON-serialized in session state."""
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

        # Mock Runner
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = "Improved"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = MagicMock()
        mock_executor.execute_agent = AsyncMock(
            return_value=MagicMock(
                status=ExecutionStatus.SUCCESS,
                extracted_value="proposed text",
                session_id="test_session",
            )
        )

        reflection_fn = create_adk_reflection_fn(
            mock_agent, mock_executor, session_service=mock_session_service
        )

        trials = [
            {"input": "test", "output": "result", "feedback": {"score": 0.7}},
        ]
        await reflection_fn("component", trials)

        # Verify trials is JSON string
        call_kwargs = mock_session_service.create_session.call_args[1]
        trials_str = call_kwargs["state"]["trials"]

        # Should be valid JSON
        parsed = json.loads(trials_str)
        assert parsed == trials

    @pytest.mark.asyncio
    async def test_empty_trials_list_serialized_correctly(
        self, mocker: MockerFixture
    ) -> None:
        """Verify empty trials list is correctly JSON-serialized."""
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

        # Mock Runner
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = "Improved"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = MagicMock()
        mock_executor.execute_agent = AsyncMock(
            return_value=MagicMock(
                status=ExecutionStatus.SUCCESS,
                extracted_value="proposed text",
                session_id="test_session",
            )
        )

        reflection_fn = create_adk_reflection_fn(
            mock_agent, mock_executor, session_service=mock_session_service
        )

        trials = []
        await reflection_fn("component", trials)

        # Verify empty list is serialized as "[]"
        call_kwargs = mock_session_service.create_session.call_args[1]
        trials_str = call_kwargs["state"]["trials"]
        assert trials_str == "[]"


class TestUserMessageSimplification:
    """Tests for verifying user message is simplified (not data carrier)."""

    @pytest.mark.asyncio
    async def test_user_message_is_simple_trigger(self, mocker: MockerFixture) -> None:
        """Verify user message is a simple trigger, not containing trial data."""
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

        # Capture the user message
        captured_message = None

        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = "Improved"
        mock_part.thought = False
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content
        mock_event.is_final_response = mocker.MagicMock(return_value=True)

        async def mock_run_async(*args, **kwargs):
            nonlocal captured_message
            captured_message = kwargs.get("new_message")
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        mock_executor = MagicMock()
        mock_executor.execute_agent = AsyncMock(
            return_value=MagicMock(
                status=ExecutionStatus.SUCCESS,
                extracted_value="proposed text",
                session_id="test_session",
            )
        )

        reflection_fn = create_adk_reflection_fn(
            mock_agent, mock_executor, session_service=mock_session_service
        )

        # Call with a specific component_text and trials
        component_text = "Be very helpful"
        trials = [{"input": "test", "output": "result", "feedback": {"score": 0.5}}]
        await reflection_fn(component_text, trials)

        # Verify user message does NOT contain the trial data
        # (data should be in session state, not user message)
        assert captured_message is not None
        message_text = captured_message.parts[0].text

        # User message should be simple, not contain JSON-formatted trials
        assert "score" not in message_text.lower() or "0.5" not in message_text
