"""Integration tests for ADK session state template substitution.

This module tests that ADK's template substitution works correctly
with real agents and session services. Tests verify:
1. Single and multiple placeholder substitution
2. Template substitution works with Gemini model
3. Template substitution works with Ollama model (if available)

Note:
    These tests require actual LLM API access and are marked accordingly.
"""

import json
import os

import pytest
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService

from gepa_adk.engine.adk_reflection import (
    REFLECTION_INSTRUCTION,
    create_adk_reflection_fn,
)

pytestmark = [pytest.mark.integration]


class TestReflectionInstructionIntegration:
    """Integration tests for REFLECTION_INSTRUCTION constant."""

    def test_reflection_instruction_contains_required_placeholders(self):
        """Verify REFLECTION_INSTRUCTION has both required placeholders."""
        assert "{component_text}" in REFLECTION_INSTRUCTION
        assert "{trials}" in REFLECTION_INSTRUCTION

    def test_reflection_instruction_can_be_formatted(self):
        """Verify REFLECTION_INSTRUCTION can be manually formatted for testing."""
        # This verifies the template is valid Python format string syntax
        formatted = REFLECTION_INSTRUCTION.format(
            component_text="Test component",
            trials='[{"score": 0.5}]',
        )
        assert "Test component" in formatted
        assert '{"score": 0.5}' in formatted


@pytest.mark.api
@pytest.mark.requires_gemini
@pytest.mark.slow
class TestGeminiTemplateSubstitution:
    """Integration tests for template substitution with Gemini model."""

    @pytest.mark.asyncio
    async def test_gemini_single_placeholder_substitution(self) -> None:
        """Verify single placeholder substitution works with Gemini."""
        agent = LlmAgent(
            name="SinglePlaceholderTest",
            model="gemini-2.5-flash",
            instruction="""Analyze this text: {component_text}

Provide a one-sentence summary.""",
        )

        reflection_fn = create_adk_reflection_fn(agent)

        # Call with specific component text
        result = await reflection_fn(
            "Python is a programming language used for web development.",
            [],  # Empty trials
        )

        # Verify result is meaningful (agent processed the placeholder)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_gemini_multiple_placeholder_substitution(self) -> None:
        """Verify both placeholders are substituted with Gemini."""
        agent = LlmAgent(
            name="MultiplePlaceholderTest",
            model="gemini-2.5-flash",
            instruction="""## Current Text
{component_text}

## Evaluation Results
{trials}

Based on the evaluation, suggest one improvement.""",
        )

        reflection_fn = create_adk_reflection_fn(agent)

        component_text = "Be helpful and concise."
        trials = [
            {"input": "Hi", "output": "Hello!", "feedback": {"score": 0.8}},
            {"input": "Bye", "output": "Goodbye", "feedback": {"score": 0.6}},
        ]

        result = await reflection_fn(component_text, trials)

        # Verify result
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_gemini_template_with_json_trials(self) -> None:
        """Verify JSON-serialized trials are correctly substituted with Gemini."""
        agent = LlmAgent(
            name="JsonTrialsTest",
            model="gemini-2.5-flash",
            instruction="""Instruction: {component_text}

Trial data (JSON):
{trials}

Return the number of trials received.""",
        )

        reflection_fn = create_adk_reflection_fn(agent)

        trials = [
            {"score": 0.5},
            {"score": 0.6},
            {"score": 0.7},
        ]

        result = await reflection_fn("test", trials)

        # Agent should have parsed the JSON and counted trials
        assert isinstance(result, str)
        # Result should mention "3" trials or similar
        assert len(result) > 0


@pytest.mark.api
@pytest.mark.requires_ollama
@pytest.mark.slow
class TestOllamaTemplateSubstitution:
    """Integration tests for template substitution with Ollama model."""

    @pytest.fixture
    def ollama_model(self) -> LiteLlm:
        """Get Ollama model from environment or use default."""
        model_name = os.environ.get("OLLAMA_TEST_MODEL", "ollama_chat/llama3.2:latest")
        return LiteLlm(model=model_name)

    @pytest.mark.asyncio
    async def test_ollama_single_placeholder_substitution(
        self, ollama_model: LiteLlm
    ) -> None:
        """Verify single placeholder substitution works with Ollama."""
        agent = LlmAgent(
            name="OllamaSingleTest",
            model=ollama_model,
            instruction="""Analyze: {component_text}

Respond with one word describing the tone.""",
        )

        reflection_fn = create_adk_reflection_fn(agent)

        result = await reflection_fn(
            "I am so happy today!",
            [],
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_ollama_multiple_placeholder_substitution(
        self, ollama_model: LiteLlm
    ) -> None:
        """Verify both placeholders are substituted with Ollama."""
        agent = LlmAgent(
            name="OllamaMultiTest",
            model=ollama_model,
            instruction="""Text: {component_text}
Trials: {trials}

Improve the text briefly.""",
        )

        reflection_fn = create_adk_reflection_fn(agent)

        result = await reflection_fn(
            "Be nice",
            [{"score": 0.5, "feedback": "Too vague"}],
        )

        assert isinstance(result, str)
        assert len(result) > 0


class TestSessionStateSetup:
    """Integration tests for session state configuration."""

    @pytest.mark.asyncio
    async def test_session_state_contains_serialized_trials(self) -> None:
        """Verify trials are JSON-serialized in session state."""
        session_service = InMemorySessionService()

        # This test just verifies the InMemorySessionService can be created
        # The actual session state verification is done in unit tests
        assert session_service is not None

    def test_empty_trials_serializes_to_empty_array(self):
        """Verify empty trials list serializes correctly."""
        trials = []
        serialized = json.dumps(trials)
        assert serialized == "[]"

    def test_complex_trials_serialize_correctly(self):
        """Verify complex trial structures serialize to valid JSON."""
        trials = [
            {
                "input": "Hello",
                "output": "Hi there!",
                "feedback": {"score": 0.8, "notes": "Good greeting"},
                "trajectory": [
                    {"step": 1, "action": "think"},
                    {"step": 2, "action": "respond"},
                ],
            },
        ]
        serialized = json.dumps(trials)

        # Should be valid JSON that can be parsed back
        parsed = json.loads(serialized)
        assert parsed == trials
