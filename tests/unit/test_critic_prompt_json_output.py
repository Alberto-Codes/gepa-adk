"""Acceptance tests for JSON rendering of a schema agent's output.

An agent with ``output_schema`` and ``output_key`` stores a dict in session
state. That value must reach the critic prompt as JSON, not as a Python
repr, so a critic that parses the "Agent Output" section succeeds.

Notes:
    The critic executor is a recording stub, so no LLM runs. The state
    extraction helper and the critic prompt builder are the real ones.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from google.adk.agents import LlmAgent
from pydantic import BaseModel

from gepa_adk.adapters.scoring import CriticScorer
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus
from gepa_adk.utils.events import extract_output_from_state

pytestmark = pytest.mark.unit


class Decision(BaseModel):
    """Schema output stored under the agent's output_key."""

    decision: str
    probability: float
    label: str


class RecordingExecutor:
    """Executor stub that records the critic prompt and returns a fixed score.

    Attributes:
        prompts: Every ``input_text`` the critic was asked to evaluate.
    """

    def __init__(self) -> None:
        """Start with no recorded prompts."""
        self.prompts: list[str] = []

    async def execute_agent(
        self, agent: Any, input_text: str, **kwargs: Any
    ) -> ExecutionResult:
        """Record the prompt and answer with a valid critic JSON document.

        Args:
            agent: Ignored.
            input_text: The critic prompt built by CriticScorer.
            **kwargs: Ignored.

        Returns:
            A successful ExecutionResult carrying a score of 0.5.
        """
        self.prompts.append(input_text)
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id="stub",
            extracted_value='{"score": 0.5, "feedback": "ok"}',
        )


def _agent_output_section(prompt: str) -> str:
    """Return the text between "Agent Output:" and the next section header."""
    start = prompt.index("Agent Output:\n") + len("Agent Output:\n")
    rest = prompt[start:]
    for header in ("\nExpected Output:", "\nPlease evaluate"):
        idx = rest.find(header)
        if idx != -1:
            rest = rest[:idx]
    return rest.strip()


class TestStateOutputIsJson:
    """extract_output_from_state serialises structured values as JSON."""

    def test_dict_state_value_is_json(self) -> None:
        """A dict under output_key comes back as a JSON document."""
        state = {"out": {"decision": "b", "probability": 0.62, "label": "x"}}
        text = extract_output_from_state(state, "out")
        assert text is not None
        assert json.loads(text) == state["out"]

    def test_pydantic_state_value_is_json(self) -> None:
        """A BaseModel under output_key comes back as its JSON dump."""
        value = Decision(decision="b", probability=0.62, label="x")
        text = extract_output_from_state({"out": value}, "out")
        assert text is not None
        assert json.loads(text) == value.model_dump()

    def test_string_state_value_is_unchanged(self) -> None:
        """A plain string under output_key is returned as-is."""
        assert extract_output_from_state({"out": "plain text"}, "out") == "plain text"

    def test_list_state_value_is_json(self) -> None:
        """A list under output_key comes back as a JSON array."""
        text = extract_output_from_state({"out": [1, "a", None]}, "out")
        assert text is not None
        assert json.loads(text) == [1, "a", None]


class TestCriticPromptAgentOutputIsJson:
    """The critic prompt's Agent Output section parses with json.loads."""

    @pytest.mark.asyncio
    async def test_schema_agent_output_reaches_critic_as_json(self) -> None:
        """A dict stored by a schema agent renders as JSON in the critic prompt."""
        state = {"decision": {"decision": "b", "probability": 0.62, "label": "x"}}
        output = extract_output_from_state(state, "decision")
        assert output is not None

        executor = RecordingExecutor()
        critic = LlmAgent(name="critic", model="gemini-3.8-flash", instruction="Score.")
        scorer = CriticScorer(critic_agent=critic, executor=executor)

        await scorer.async_score("Classify this.", output, expected="x")

        assert len(executor.prompts) == 1
        section = _agent_output_section(executor.prompts[0])
        assert json.loads(section) == state["decision"]
        assert "'" not in section

    @pytest.mark.asyncio
    async def test_plain_text_output_is_unchanged_in_prompt(self) -> None:
        """A plain-string output is rendered verbatim, not quoted as JSON."""
        executor = RecordingExecutor()
        critic = LlmAgent(name="critic", model="gemini-3.8-flash", instruction="Score.")
        scorer = CriticScorer(critic_agent=critic, executor=executor)

        await scorer.async_score("Say hi.", "Hello there", expected=None)

        assert _agent_output_section(executor.prompts[0]) == "Hello there"
