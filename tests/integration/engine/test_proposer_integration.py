"""Integration tests for AsyncReflectiveMutationProposer with ADK reflection.

These tests verify the proposer works correctly with ADK reflection functions,
both with mocked and real LLM responses.

Note:
    These integration tests verify the proposer works with ADK reflection,
    ensuring our implementation correctly delegates to the reflection function.
"""

import pytest
from structlog.testing import capture_logs

from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

pytestmark = pytest.mark.integration


class TestAdkReflectionPath:
    """Integration tests for ADK reflection proposer path."""

    @pytest.mark.asyncio
    async def test_adk_reflection_used_in_proposer(self):
        """Verify ADK reflection function is called by proposer."""

        async def fake_reflection(input_text, input_feedback):
            return "Use concise, step-by-step instructions."

        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=fake_reflection)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": [{"input": "x", "feedback": "y"}]}

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        assert result is not None
        assert result["instruction"] == "Use concise, step-by-step instructions."

    @pytest.mark.asyncio
    async def test_adk_reflection_logging_emitted(self):
        """Verify proposer logs ADK reflection path."""

        async def fake_reflection(input_text, input_feedback):
            return "Return only the improved instruction."

        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=fake_reflection)
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": [{"input": "x", "feedback": "y"}]}

        with capture_logs() as cap_logs:
            result = await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )

        log_events = [
            log
            for log in cap_logs
            if log.get("event") == "proposer.reflection_path"
            and log.get("method") == "adk"
        ]
        assert log_events
        assert result is not None
        assert result["instruction"] != candidate["instruction"]

    @pytest.mark.asyncio
    async def test_proposer_handles_multiple_components(self):
        """Verify proposer can handle multiple components."""
        call_count = 0

        async def fake_reflection(input_text, input_feedback):
            nonlocal call_count
            call_count += 1
            return f"Improved {input_text}"

        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=fake_reflection)
        candidate = {"instruction": "Be helpful", "context": "Use tables"}
        reflective_dataset = {
            "instruction": [{"input": "x", "feedback": "y"}],
            "context": [{"input": "a", "feedback": "b"}],
        }

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction", "context"],
        )

        assert result is not None
        assert "instruction" in result
        assert "context" in result
        assert call_count == 2  # Called once per component
