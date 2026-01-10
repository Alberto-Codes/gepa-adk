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

from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer


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
            model="ollama/gpt-oss:20b",
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
        # Should be different from original (mutation occurred)
        assert result["instruction"] != candidate["instruction"]

    @pytest.mark.asyncio
    async def test_propose_handles_real_empty_response_gracefully(self):
        """Verify proposer handles unusual real LLM responses."""
        if not os.getenv("OLLAMA_API_BASE"):
            pytest.skip("OLLAMA_API_BASE not configured")

        proposer = AsyncReflectiveMutationProposer(
            model="ollama/gpt-oss:20b",
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
