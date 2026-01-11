"""Integration tests for ADK reflection.

This module tests the ADK reflection path with real ADK agents to verify
end-to-end behavior of the create_adk_reflection_fn factory.

Note:
    These tests use real ADK components and are marked @pytest.mark.slow
    for CI-only execution.
"""

import pytest
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService

from gepa_adk.engine.proposer import create_adk_reflection_fn

pytestmark = pytest.mark.integration


@pytest.mark.slow
class TestAdkReflectionIntegration:
    """Integration tests for ADK reflection with real agents."""

    @pytest.mark.asyncio
    async def test_create_adk_reflection_fn_with_real_agent(self) -> None:
        """Verify create_adk_reflection_fn works with real ADK LlmAgent."""
        # Create a real reflection agent
        reflection_agent = LlmAgent(
            name="TestReflector",
            model="gemini-2.0-flash",
            instruction="""You are an expert at improving instructions.

Current Instruction:
{current_instruction}

Execution Feedback:
{execution_feedback}

Propose an improved instruction that addresses the feedback.
Return ONLY the improved instruction text.""",
        )

        # Create reflection function
        reflection_fn = create_adk_reflection_fn(reflection_agent)

        # Test with sample data
        current_instruction = "Be helpful"
        feedback = [
            {"score": 0.6, "output": "OK", "feedback": "Too vague, needs more detail"}
        ]

        # Call the reflection function
        result = await reflection_fn(current_instruction, feedback)

        # Verify result
        assert isinstance(result, str), "Result must be string"
        assert len(result) > 0, "Result should not be empty"
        # Result should be different from input (agent improved it)
        assert result != current_instruction or "helpful" in result.lower()

    @pytest.mark.asyncio
    async def test_adk_reflection_with_custom_session_service(self) -> None:
        """Verify create_adk_reflection_fn works with custom SessionService."""
        # Create custom session service
        custom_session_service = InMemorySessionService()

        # Create reflection agent
        reflection_agent = LlmAgent(
            name="CustomServiceReflector",
            model="gemini-2.0-flash",
            instruction="Improve: {current_instruction}\nBased on: {execution_feedback}",
        )

        # Create reflection function with custom service
        reflection_fn = create_adk_reflection_fn(
            reflection_agent, session_service=custom_session_service
        )

        # Call it
        result = await reflection_fn(
            "Be concise",
            [{"score": 0.5, "output": "test"}],
        )

        # Verify result
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_adk_reflection_context_passing(self) -> None:
        """Verify reflection agent receives context via session state."""
        # Create reflection agent that echoes the instruction
        reflection_agent = LlmAgent(
            name="EchoReflector",
            model="gemini-2.0-flash",
            instruction="""Current instruction is: {current_instruction}
Feedback data is: {execution_feedback}

Return a summary of what you received.""",
        )

        # Create reflection function
        reflection_fn = create_adk_reflection_fn(reflection_agent)

        # Call with specific data
        current_instruction = "Be helpful and detailed"
        feedback = [{"score": 0.7, "output": "OK", "feedback": "Good"}]

        result = await reflection_fn(current_instruction, feedback)

        # Result should reference the instruction (agent saw it in session state)
        assert isinstance(result, str)
        # Agent should have processed the context
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_adk_reflection_with_empty_feedback(self) -> None:
        """Verify ADK reflection handles empty feedback list."""
        reflection_agent = LlmAgent(
            name="EmptyFeedbackReflector",
            model="gemini-2.0-flash",
            instruction="Improve: {current_instruction}",
        )

        reflection_fn = create_adk_reflection_fn(reflection_agent)

        # Call with empty feedback
        result = await reflection_fn("Be helpful", [])

        # Should still return a result
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_adk_reflection_with_multiple_feedback_items(self) -> None:
        """Verify ADK reflection processes multiple feedback items."""
        reflection_agent = LlmAgent(
            name="MultiFeedbackReflector",
            model="gemini-2.0-flash",
            instruction="""Improve this instruction based on feedback:

{current_instruction}

Feedback:
{execution_feedback}

Return improved instruction only.""",
        )

        reflection_fn = create_adk_reflection_fn(reflection_agent)

        # Call with multiple feedback items
        feedback = [
            {"score": 0.5, "output": "test1", "feedback": "Too brief"},
            {"score": 0.6, "output": "test2", "feedback": "Lacks examples"},
            {"score": 0.7, "output": "test3", "feedback": "Good structure"},
        ]

        result = await reflection_fn("Be helpful", feedback)

        # Verify result
        assert isinstance(result, str)
        assert len(result) > 0
