"""Integration tests for AsyncReflectiveMutationProposer with real LLM calls.

These tests make real API calls to LLM providers and are marked with
@pytest.mark.slow and @pytest.mark.api. They are excluded from regular test
runs to avoid accidental API quota usage.

Run with: uv run pytest -m "slow and api" tests/integration/engine/

Note:
    These integration tests verify the proposer works with real LLM providers,
    ensuring our implementation is compatible with actual API responses.
"""

import os

import pytest
from structlog.testing import capture_logs

from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

pytestmark = pytest.mark.integration


@pytest.mark.slow
@pytest.mark.api
@pytest.mark.requires_ollama
class TestOllamaIntegration:
    """Integration tests using local Ollama."""

    @pytest.mark.asyncio
    async def test_propose_returns_valid_mutation_with_real_ollama(self):
        """Verify proposer works with real Ollama LLM call."""
        # Skip if OLLAMA_API_BASE not set
        if not os.getenv("OLLAMA_API_BASE"):
            pytest.skip("OLLAMA_API_BASE not configured")

        proposer = AsyncReflectiveMutationProposer(
            model="ollama_chat/gpt-oss:20b",
            temperature=0.3,  # Lower for more deterministic responses
            max_tokens=512,
        )

        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [
                {
                    "input": "What is 2+2?",
                    "output": "4",
                    "feedback": "Good but needs explanation",
                },
                {
                    "input": "Explain gravity",
                    "output": "Force that pulls things down",
                    "feedback": "Too brief, lacks detail",
                },
            ]
        }

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        # Verify result structure
        assert result is not None
        assert isinstance(result, dict)
        assert "instruction" in result
        assert len(result["instruction"]) > 0

    @pytest.mark.asyncio
    async def test_adk_reflection_extracts_from_mock_ollama_response(self, mocker):
        """Verify ADK reflection extraction with mocked Ollama-style output."""
        mock_agent = mocker.MagicMock()
        mock_agent.model = "ollama_chat/llama3.1:latest"
        mock_agent.output_schema = None

        mock_session_service = mocker.MagicMock()
        mock_session_service.create_session = mocker.AsyncMock(
            return_value=mocker.MagicMock()
        )

        response_text = (
            "Reasoning: The instruction needs more constraints and clarity.\n\n"
            "IMPROVED INSTRUCTION:\n"
            "Answer concisely, cite sources when available, and avoid speculation.\n\n"
            "Additional notes: Keep responses under 5 sentences."
        )

        mock_runner = mocker.MagicMock()
        mock_event = mocker.MagicMock()
        mock_part = mocker.MagicMock()
        mock_part.text = response_text
        mock_content = mocker.MagicMock()
        mock_content.parts = [mock_part]
        mock_event.content = mock_content

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mocker.patch("google.adk.Runner", return_value=mock_runner)

        reflection_fn = create_adk_reflection_fn(
            mock_agent, session_service=mock_session_service
        )
        result = await reflection_fn("Be helpful", [{"score": 0.5}])

        assert "Answer concisely" in result


class TestAdkReflectionPath:
    """Integration tests for ADK reflection proposer path."""

    @pytest.mark.asyncio
    async def test_adk_reflection_used_in_proposer(self, mocker):
        """Verify ADK reflection path avoids LiteLLM fallback."""

        async def fake_reflection(input_text, input_feedback):
            return "Use concise, step-by-step instructions."

        mock_acompletion = mocker.patch(
            "gepa_adk.engine.proposer.acompletion",
            new_callable=mocker.AsyncMock,
        )

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
        mock_acompletion.assert_not_called()

    @pytest.mark.asyncio
    async def test_adk_reflection_logging_emitted(self, mocker):
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
    async def test_propose_handles_real_empty_response_gracefully(self):
        """Verify proposer handles unusual real LLM responses."""
        if not os.getenv("OLLAMA_API_BASE"):
            pytest.skip("OLLAMA_API_BASE not configured")

        proposer = AsyncReflectiveMutationProposer(
            model="ollama_chat/gpt-oss:20b",
            temperature=0.0,  # Deterministic
            max_tokens=10,  # Very low to potentially trigger edge cases
        )

        candidate = {"instruction": "Test"}
        reflective_dataset = {
            "instruction": [
                {"input": "test", "feedback": "ok"},
            ]
        }

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        # Should handle gracefully - either return mutation or original
        assert result is not None
        assert "instruction" in result
        assert len(result["instruction"]) > 0


@pytest.mark.slow
@pytest.mark.api
@pytest.mark.requires_gemini
class TestGeminiIntegration:
    """Integration tests using Gemini API."""

    @pytest.mark.asyncio
    async def test_gemini_model_works(self):
        """Verify proposer works with Gemini API."""
        # Skip if GEMINI_API_KEY not set
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not configured")

        proposer = AsyncReflectiveMutationProposer(
            model="gemini/gemini-2.5-flash",
            temperature=0.5,
            max_tokens=1024,
        )

        candidate = {"instruction": "You are a helpful assistant"}
        reflective_dataset = {
            "instruction": [
                {
                    "input": "Summarize this article",
                    "output": "Article is about...",
                    "feedback": "Good structure, clear summary",
                },
                {
                    "input": "What's the weather?",
                    "output": "I don't have access to weather",
                    "feedback": "Response too brief",
                },
            ]
        }

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction"],
        )

        # Verify Gemini returns valid mutation
        assert result is not None
        assert isinstance(result, dict)
        assert "instruction" in result
        assert len(result["instruction"]) > 10
        # Should be a meaningful mutation
        assert result["instruction"] != candidate["instruction"]

    @pytest.mark.asyncio
    async def test_gemini_handles_complex_feedback(self):
        """Verify Gemini handles complex multi-feedback scenarios."""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not configured")

        proposer = AsyncReflectiveMutationProposer(
            model="gemini/gemini-2.5-flash",
        )

        candidate = {"instruction": "Analyze the data", "context": "Use tables"}
        reflective_dataset = {
            "instruction": [
                {"input": "test1", "feedback": "Too vague"},
                {"input": "test2", "feedback": "Missing examples"},
                {"input": "test3", "feedback": "Good structure"},
            ],
            "context": [
                {"input": "viz1", "feedback": "Tables not used"},
                {"input": "viz2", "feedback": "Good formatting"},
            ],
        }

        result = await proposer.propose(
            candidate=candidate,
            reflective_dataset=reflective_dataset,
            components_to_update=["instruction", "context"],
        )

        # Should handle multiple components
        assert result is not None
        assert "instruction" in result
        assert "context" in result
        # Both should be mutated
        assert result["instruction"] != candidate["instruction"]
        assert result["context"] != candidate["context"]
