"""Unit tests for ADK reflection template substitution.

This module tests the template substitution functionality in adk_reflection.py,
verifying that ADK's {key} placeholder syntax works correctly with session state.

Tests cover:
- Single placeholder substitution (US1)
- Multiple placeholder substitution (US2)
- Missing state key error handling
- Non-string value serialization (JSON)
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gepa_adk.engine.adk_reflection import (
    REFLECTION_INSTRUCTION,
    SESSION_STATE_KEYS,
    create_adk_reflection_fn,
)


class TestReflectionInstructionConstant:
    """Tests for the REFLECTION_INSTRUCTION constant."""

    def test_contains_component_text_placeholder(self) -> None:
        """T006: Verify REFLECTION_INSTRUCTION contains {component_text} placeholder."""
        assert "{component_text}" in REFLECTION_INSTRUCTION
        assert "{trials}" in REFLECTION_INSTRUCTION

    def test_placeholder_format_matches_adk_syntax(self) -> None:
        """Verify placeholder format uses ADK's {key} syntax, not {state.key}."""
        # ADK uses {key} not {state.key}
        assert "{state.component_text}" not in REFLECTION_INSTRUCTION
        assert "{state.trials}" not in REFLECTION_INSTRUCTION
        # Should use simple {key} format
        assert "{component_text}" in REFLECTION_INSTRUCTION
        assert "{trials}" in REFLECTION_INSTRUCTION


class TestSessionStateKeys:
    """Tests for SESSION_STATE_KEYS constant."""

    def test_has_required_keys(self) -> None:
        """Verify SESSION_STATE_KEYS contains expected keys."""
        assert "component_text" in SESSION_STATE_KEYS
        assert "trials" in SESSION_STATE_KEYS

    def test_key_types(self) -> None:
        """Verify SESSION_STATE_KEYS specifies correct types."""
        assert SESSION_STATE_KEYS["component_text"] is str
        assert SESSION_STATE_KEYS["trials"] is str  # JSON-serialized


class TestCreateAdkReflectionFn:
    """Tests for create_adk_reflection_fn factory."""

    @pytest.mark.asyncio
    async def test_session_state_contains_component_text(self) -> None:
        """T006: Verify session state is populated with component_text."""
        captured_state: dict[str, Any] = {}

        # Mock ADK components
        mock_session_service = AsyncMock()

        async def capture_create_session(**kwargs: Any) -> None:
            captured_state.update(kwargs.get("state", {}))

        mock_session_service.create_session = capture_create_session

        # Mock runner to return events
        mock_runner = MagicMock()
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.actions = MagicMock()
        mock_event.actions.response_content = [MagicMock(text="Improved text", thought=False)]

        async def mock_run_async(**kwargs: Any):
            yield mock_event

        mock_runner.run_async = mock_run_async

        with patch("google.adk.Runner", return_value=mock_runner):
            mock_agent = MagicMock()
            reflection_fn = create_adk_reflection_fn(
                mock_agent, session_service=mock_session_service
            )

            # Call reflection function
            component_text = "Be helpful and concise"
            trials = [{"score": 0.7, "feedback": "Good"}]
            await reflection_fn(component_text, trials)

            # Verify session state contains component_text
            assert "component_text" in captured_state
            assert captured_state["component_text"] == component_text

    @pytest.mark.asyncio
    async def test_session_state_contains_trials_as_json(self) -> None:
        """T006: Verify session state contains trials as JSON string."""
        captured_state: dict[str, Any] = {}

        mock_session_service = AsyncMock()

        async def capture_create_session(**kwargs: Any) -> None:
            captured_state.update(kwargs.get("state", {}))

        mock_session_service.create_session = capture_create_session

        mock_runner = MagicMock()
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.actions = MagicMock()
        mock_event.actions.response_content = [MagicMock(text="Improved text", thought=False)]

        async def mock_run_async(**kwargs: Any):
            yield mock_event

        mock_runner.run_async = mock_run_async

        with patch("google.adk.Runner", return_value=mock_runner):
            mock_agent = MagicMock()
            reflection_fn = create_adk_reflection_fn(
                mock_agent, session_service=mock_session_service
            )

            trials = [
                {"score": 0.7, "feedback": "Good"},
                {"score": 0.5, "feedback": "Needs work"},
            ]
            await reflection_fn("Test instruction", trials)

            # Verify trials is JSON-serialized string
            assert "trials" in captured_state
            assert isinstance(captured_state["trials"], str)
            # Should be valid JSON
            parsed = json.loads(captured_state["trials"])
            assert parsed == trials

    @pytest.mark.asyncio
    async def test_user_message_is_simple_trigger(self) -> None:
        """T009: Verify user message is simple trigger, not data carrier."""
        captured_message: str = ""

        mock_session_service = AsyncMock()

        mock_runner = MagicMock()
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.actions = MagicMock()
        mock_event.actions.response_content = [MagicMock(text="Improved text", thought=False)]

        async def mock_run_async(**kwargs: Any):
            nonlocal captured_message
            new_message = kwargs.get("new_message")
            if new_message and hasattr(new_message, "parts"):
                for part in new_message.parts:
                    if hasattr(part, "text"):
                        captured_message = part.text
            yield mock_event

        mock_runner.run_async = mock_run_async

        with patch("google.adk.Runner", return_value=mock_runner):
            mock_agent = MagicMock()
            reflection_fn = create_adk_reflection_fn(
                mock_agent, session_service=mock_session_service
            )

            component_text = "Be helpful"
            trials = [{"score": 0.5}]
            await reflection_fn(component_text, trials)

            # Verify user message is simple trigger, not containing data
            assert "Please improve" in captured_message
            # Should NOT contain the actual component_text or trials data
            assert component_text not in captured_message
            assert "0.5" not in captured_message

    @pytest.mark.asyncio
    async def test_returns_extracted_output(self) -> None:
        """Verify reflection function returns extracted final output."""
        mock_session_service = AsyncMock()

        mock_runner = MagicMock()
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.actions = MagicMock()
        expected_output = "This is the improved instruction"
        mock_event.actions.response_content = [MagicMock(text=expected_output, thought=False)]

        async def mock_run_async(**kwargs: Any):
            yield mock_event

        mock_runner.run_async = mock_run_async

        with patch("google.adk.Runner", return_value=mock_runner):
            mock_agent = MagicMock()
            reflection_fn = create_adk_reflection_fn(
                mock_agent, session_service=mock_session_service
            )

            result = await reflection_fn("Test", [])
            assert result == expected_output

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_string(self) -> None:
        """Verify empty agent response returns empty string."""
        mock_session_service = AsyncMock()

        mock_runner = MagicMock()
        # No final response events
        async def mock_run_async(**kwargs: Any):
            return
            yield  # Make it an async generator

        mock_runner.run_async = mock_run_async

        with patch("google.adk.Runner", return_value=mock_runner):
            mock_agent = MagicMock()
            reflection_fn = create_adk_reflection_fn(
                mock_agent, session_service=mock_session_service
            )

            result = await reflection_fn("Test", [])
            assert result == ""


class TestMultiplePlaceholderSubstitution:
    """Tests for multiple placeholder substitution (US2)."""

    @pytest.mark.asyncio
    async def test_both_placeholders_in_session_state(self) -> None:
        """T012: Verify both component_text and trials are in session state."""
        captured_state: dict[str, Any] = {}

        mock_session_service = AsyncMock()

        async def capture_create_session(**kwargs: Any) -> None:
            captured_state.update(kwargs.get("state", {}))

        mock_session_service.create_session = capture_create_session

        mock_runner = MagicMock()
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.actions = MagicMock()
        mock_event.actions.response_content = [MagicMock(text="Improved", thought=False)]

        async def mock_run_async(**kwargs: Any):
            yield mock_event

        mock_runner.run_async = mock_run_async

        with patch("google.adk.Runner", return_value=mock_runner):
            mock_agent = MagicMock()
            reflection_fn = create_adk_reflection_fn(
                mock_agent, session_service=mock_session_service
            )

            component_text = "Be concise and helpful"
            trials = [
                {"input": "Hi", "output": "Hello", "score": 0.8},
                {"input": "Bye", "output": "Goodbye", "score": 0.9},
            ]
            await reflection_fn(component_text, trials)

            # Both keys should be present
            assert "component_text" in captured_state
            assert "trials" in captured_state
            # Values should match
            assert captured_state["component_text"] == component_text
            assert json.loads(captured_state["trials"]) == trials

    @pytest.mark.asyncio
    async def test_complex_trials_serialization(self) -> None:
        """T014: Verify complex nested trial data is properly serialized."""
        captured_state: dict[str, Any] = {}

        mock_session_service = AsyncMock()

        async def capture_create_session(**kwargs: Any) -> None:
            captured_state.update(kwargs.get("state", {}))

        mock_session_service.create_session = capture_create_session

        mock_runner = MagicMock()
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.actions = MagicMock()
        mock_event.actions.response_content = [MagicMock(text="Improved", thought=False)]

        async def mock_run_async(**kwargs: Any):
            yield mock_event

        mock_runner.run_async = mock_run_async

        with patch("google.adk.Runner", return_value=mock_runner):
            mock_agent = MagicMock()
            reflection_fn = create_adk_reflection_fn(
                mock_agent, session_service=mock_session_service
            )

            # Complex nested trial data
            trials = [
                {
                    "input": "What is 2+2?",
                    "output": "4",
                    "feedback": {
                        "score": 0.95,
                        "criteria": ["accuracy", "clarity"],
                        "details": {"accuracy": 1.0, "clarity": 0.9},
                    },
                    "trajectory": {
                        "tool_calls": [{"name": "calculate", "args": {"expr": "2+2"}}],
                    },
                },
            ]
            await reflection_fn("Be accurate", trials)

            # Trials should be valid JSON
            parsed = json.loads(captured_state["trials"])
            assert parsed[0]["feedback"]["criteria"] == ["accuracy", "clarity"]
            assert parsed[0]["trajectory"]["tool_calls"][0]["name"] == "calculate"


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_exception_is_propagated(self) -> None:
        """T007: Verify exceptions from runner are propagated."""
        mock_session_service = AsyncMock()

        mock_runner = MagicMock()

        async def mock_run_async(**kwargs: Any):
            raise RuntimeError("LLM API error")
            yield  # Make it an async generator

        mock_runner.run_async = mock_run_async

        with patch("google.adk.Runner", return_value=mock_runner):
            mock_agent = MagicMock()
            reflection_fn = create_adk_reflection_fn(
                mock_agent, session_service=mock_session_service
            )

            with pytest.raises(RuntimeError, match="LLM API error"):
                await reflection_fn("Test", [])

    @pytest.mark.asyncio
    async def test_session_creation_error_propagated(self) -> None:
        """Verify session creation errors are propagated."""
        mock_session_service = AsyncMock()
        mock_session_service.create_session.side_effect = ValueError("Invalid state")

        with patch("google.adk.Runner"):
            mock_agent = MagicMock()
            reflection_fn = create_adk_reflection_fn(
                mock_agent, session_service=mock_session_service
            )

            with pytest.raises(ValueError, match="Invalid state"):
                await reflection_fn("Test", [])
