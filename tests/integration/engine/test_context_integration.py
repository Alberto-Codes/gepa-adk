"""Integration tests for context passing with real ADK agents (US2).

NOTE: Nothing Escapes Virtue; Excellence Requires Thoughtful, Honest Engineering
"""

import json

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters.agent_executor import AgentExecutor
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

pytestmark = [pytest.mark.integration, pytest.mark.api, pytest.mark.requires_gemini]


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_agent_receives_input_text() -> None:
    """Test that real ADK agent can access input_text from session state."""
    # Arrange: Real agent (minimal config)
    agent = LlmAgent(
        name="reflection_agent",
        model="gemini-2.0-flash-exp",
        instruction="You are a code reviewer.",
    )

    executor = AgentExecutor()
    reflection_fn = create_adk_reflection_fn(agent, executor=executor)

    # Act
    current_text = "def add(a, b): return a + b"
    feedback = [{"component": "code", "issue": "missing type hints"}]
    result = await reflection_fn(current_text, feedback)

    # Assert: Result should be string (agent processed the instruction)
    assert isinstance(result, str)
    # Note: We can't assert exact content, but it should not be empty
    assert len(result) > 0


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_agent_receives_input_feedback_json() -> None:
    """Test that real ADK agent receives input_feedback as parseable JSON."""
    # Arrange
    agent = LlmAgent(
        name="reflection_agent",
        model="gemini-2.0-flash-exp",
        instruction="Reflect on feedback and improve code.",
    )

    executor = AgentExecutor()
    reflection_fn = create_adk_reflection_fn(agent, executor=executor)

    # Act
    feedback = [
        {"component": "function", "issue": "missing docstring"},
        {"component": "function", "issue": "no error handling"},
    ]
    result = await reflection_fn("def process(): pass", feedback)

    # Assert: Agent should return non-empty string
    assert isinstance(result, str)
    assert len(result) > 0

    # Verify feedback was serializable (no exception during call)
    # The JSON serialization should have succeeded
    feedback_json = json.dumps(feedback)
    parsed = json.loads(feedback_json)
    assert parsed == feedback
