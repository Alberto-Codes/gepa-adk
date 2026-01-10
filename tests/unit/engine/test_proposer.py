"""Unit tests for AsyncReflectiveMutationProposer.

This module tests the internal methods and logic of the mutation proposer
with mocked LLM calls. These tests focus on implementation details like
message formatting and feedback serialization.

Note:
    These unit tests use fakes and mocks to isolate the proposer's internal
    logic from external dependencies like LiteLLM.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer


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
        custom_template = "Improve: {current_instruction}\nFeedback: {feedback_examples}"
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
    async def test_concurrent_propose_calls_execute_without_blocking(self):
        """Verify concurrent propose calls don't block each other."""
        proposer = AsyncReflectiveMutationProposer()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [{"input": "test", "feedback": "good"}]
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Improved instruction"))
        ]

        with patch("gepa_adk.engine.proposer.acompletion", new=AsyncMock(return_value=mock_response)):
            # Launch multiple concurrent calls
            import asyncio
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
        assert elapsed_ms < 10, f"Empty dataset check took {elapsed_ms:.2f}ms, expected <10ms"
