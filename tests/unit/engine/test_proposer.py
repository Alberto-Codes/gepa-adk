"""Unit tests for AsyncReflectiveMutationProposer.

This module tests the internal methods and logic of the mutation proposer
with mocked LLM calls. These tests focus on implementation details like
message formatting and feedback serialization.

Note:
    These unit tests use fakes and mocks to isolate the proposer's internal
    logic from external dependencies like LiteLLM.
"""

import asyncio
import json

import pytest
from pytest_mock import MockerFixture

from gepa_adk.engine.proposer import (
    AsyncReflectiveMutationProposer,
    create_adk_reflection_fn,
)


@pytest.mark.unit
class TestFormatFeedback:
    """Test _format_feedback method for feedback serialization."""

    def test_format_single_feedback_item(self):
        """Verify _format_feedback handles single feedback item."""
        proposer = AsyncReflectiveMutationProposer()
        feedback = [
            {"input": "What is 2+2?", "output": "4", "feedback": "Good but brief"}
        ]

        result = proposer._format_feedback(feedback)

        assert isinstance(result, str)
        assert "What is 2+2?" in result
        assert "Good but brief" in result

    def test_format_multiple_feedback_items(self):
        """Verify _format_feedback handles multiple feedback items."""
        proposer = AsyncReflectiveMutationProposer()
        feedback = [
            {"input": "test1", "feedback": "feedback1"},
            {"input": "test2", "feedback": "feedback2"},
            {"input": "test3", "feedback": "feedback3"},
        ]

        result = proposer._format_feedback(feedback)

        assert "test1" in result
        assert "test2" in result
        assert "test3" in result
        assert "feedback1" in result
        assert "feedback2" in result
        assert "feedback3" in result

    def test_format_empty_feedback_list(self):
        """Verify _format_feedback handles empty feedback list."""
        proposer = AsyncReflectiveMutationProposer()
        feedback = []

        result = proposer._format_feedback(feedback)

        # Should return empty or minimal string
        assert isinstance(result, str)


@pytest.mark.unit
class TestBuildMessages:
    """Test _build_messages method for LLM message construction."""

    def test_build_messages_creates_correct_structure(self):
        """Verify _build_messages creates proper message list structure."""
        proposer = AsyncReflectiveMutationProposer()
        current_text = "Be helpful"
        feedback = [{"input": "test", "feedback": "good"}]

        messages = proposer._build_messages(current_text, feedback)

        assert isinstance(messages, list)
        assert len(messages) > 0
        # Should contain role and content keys
        for msg in messages:
            assert "role" in msg
            assert "content" in msg

    def test_build_messages_includes_current_instruction(self):
        """Verify _build_messages includes current instruction in prompt."""
        proposer = AsyncReflectiveMutationProposer()
        current_text = "Be helpful and concise"
        feedback = [{"input": "test", "feedback": "good"}]

        messages = proposer._build_messages(current_text, feedback)

        # Current instruction should appear in message content
        all_content = " ".join(msg["content"] for msg in messages)
        assert "Be helpful and concise" in all_content

    def test_build_messages_includes_feedback_examples(self):
        """Verify _build_messages includes feedback in prompt."""
        proposer = AsyncReflectiveMutationProposer()
        current_text = "Be helpful"
        feedback = [{"input": "What is AI?", "feedback": "Too technical"}]

        messages = proposer._build_messages(current_text, feedback)

        # Feedback should appear in message content
        all_content = " ".join(msg["content"] for msg in messages)
        assert "What is AI?" in all_content or "Too technical" in all_content

    def test_build_messages_with_custom_template(self):
        """Verify _build_messages uses custom prompt template."""
        custom_template = (
            "Improve: {current_instruction}\nFeedback: {feedback_examples}"
        )
        proposer = AsyncReflectiveMutationProposer(prompt_template=custom_template)
        current_text = "Be helpful"
        feedback = [{"input": "test", "feedback": "ok"}]

        messages = proposer._build_messages(current_text, feedback)

        # Should use custom template format
        all_content = " ".join(msg["content"] for msg in messages)
        assert "Improve:" in all_content or "Be helpful" in all_content


class TestProposeAsyncBehavior:
    """Test propose method async behavior (non-blocking)."""

    @pytest.mark.asyncio
    async def test_concurrent_propose_calls_execute_without_blocking(
        self, mocker: MockerFixture
    ) -> None:
        """Verify concurrent propose calls don't block each other."""
        proposer = AsyncReflectiveMutationProposer()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": [{"input": "test", "feedback": "good"}]}

        mock_response = mocker.MagicMock()
        mock_response.choices = [
            mocker.MagicMock(message=mocker.MagicMock(content="Improved instruction"))
        ]

        mocker.patch(
            "gepa_adk.engine.proposer.acompletion",
            new_callable=mocker.AsyncMock,
            return_value=mock_response,
        )

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


class TestProposePerformance:
    """Test propose method performance characteristics."""

    @pytest.mark.asyncio
    async def test_performance_none_returned_within_10ms_for_empty_dataset(self):
        """Verify None returned within 10ms for empty dataset (no LLM call)."""
        import time

        proposer = AsyncReflectiveMutationProposer()
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


@pytest.mark.unit
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
        reflection_fn = create_adk_reflection_fn(mock_agent)

        # Verify it's callable
        assert callable(reflection_fn), "create_adk_reflection_fn must return callable"

    @pytest.mark.asyncio
    async def test_create_adk_reflection_fn_with_mocked_adk(
        self, mocker: MockerFixture
    ) -> None:
        """Verify reflection function calls ADK Runner.run_async."""
        # Mock ADK components
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"

        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)

        # Mock Runner and its run_async method
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()

        # Mock event.content.parts to return the response text
        mock_part = mocker.MagicMock()
        mock_part.text = "Improved instruction"
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async

        # Patch Runner at the import location (inside the function)
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        # Create reflection function
        reflection_fn = create_adk_reflection_fn(
            mock_agent, session_service=mock_session_service
        )

        # Call the reflection function
        result = await reflection_fn(
            "Be helpful",
            [{"score": 0.5, "output": "test"}],
        )

        # Verify session was created with state
        mock_session_service.create_session.assert_called_once()
        call_kwargs = mock_session_service.create_session.call_args[1]
        assert "state" in call_kwargs
        assert "current_instruction" in call_kwargs["state"]
        assert call_kwargs["state"]["current_instruction"] == "Be helpful"

        # Verify result is string
        assert isinstance(result, str)
        assert result == "Improved instruction"

    @pytest.mark.asyncio
    async def test_create_adk_reflection_fn_defaults_to_inmemory_session(
        self, mocker: MockerFixture
    ) -> None:
        """Verify create_adk_reflection_fn defaults to InMemorySessionService."""
        # Mock ADK components
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"

        mock_inmemory_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_inmemory_service.create_session = AsyncMock(return_value=mock_session)

        # Patch InMemorySessionService
        mocker.patch(
            "google.adk.sessions.InMemorySessionService",
            return_value=mock_inmemory_service,
        )

        # Mock Runner
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.actions.response_content = [mocker.MagicMock(text="Improved")]

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        # Create reflection function WITHOUT session_service
        reflection_fn = create_adk_reflection_fn(mock_agent)

        # Call it
        await reflection_fn("test", [])

        # Verify InMemorySessionService was used
        mock_inmemory_service.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_reflection_fn_handles_empty_adk_response(
        self, mocker: MockerFixture
    ) -> None:
        """Verify reflection function handles empty ADK response."""
        mock_agent = mocker.MagicMock()
        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)

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
        reflection_fn = create_adk_reflection_fn(
            mock_agent, session_service=mock_session_service
        )
        result = await reflection_fn("test", [])

        # Should return empty string
        assert result == ""

    @pytest.mark.asyncio
    async def test_reflection_fn_serializes_feedback_as_json(
        self, mocker: MockerFixture
    ) -> None:
        """Verify reflection function JSON-serializes feedback."""
        mock_agent = mocker.MagicMock()
        mock_session_service = mocker.MagicMock()
        mock_session = mocker.MagicMock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)

        # Mock Runner
        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.actions.response_content = [mocker.MagicMock(text="OK")]

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        # Create and call reflection function
        reflection_fn = create_adk_reflection_fn(
            mock_agent, session_service=mock_session_service
        )
        feedback = [{"score": 0.8, "output": "good"}]
        await reflection_fn("test", feedback)

        # Verify session state has JSON-serialized feedback
        call_kwargs = mock_session_service.create_session.call_args[1]
        assert "execution_feedback" in call_kwargs["state"]

        # Should be JSON-serializable string
        feedback_str = call_kwargs["state"]["execution_feedback"]
        assert isinstance(feedback_str, str)
        parsed = json.loads(feedback_str)
        assert parsed == feedback
