"""Integration tests for end-to-end critic→reflection metadata flow.

Tests the complete flow from CriticScorer returning metadata through
ADKAdapter to reflection agent receiving enriched feedback.

Run: pytest tests/integration/test_critic_reflection_metadata.py -v --slow
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.integration


class TestCriticReflectionMetadataFlow:
    """Integration tests for critic metadata passthrough to reflection."""

    @pytest.fixture
    def mock_agent(self) -> Any:
        """Create a mock ADK agent."""
        from google.adk.agents import LlmAgent

        agent = MagicMock(spec=LlmAgent)
        agent.instruction = "Be helpful"
        agent.name = "test_agent"
        return agent

    @pytest.fixture
    def critic_scorer(self) -> Any:
        """Create a mock CriticScorer that returns metadata."""
        scorer = MagicMock()

        async def async_score(
            input_text: str, output: str, expected: str | None = None
        ) -> tuple[float, dict[str, Any]]:
            """Return score with rich metadata."""
            score = 0.75
            metadata = {
                "feedback": "Good response but could be more concise",
                "actionable_guidance": "Reduce length by 30%",
                "dimension_scores": {"accuracy": 0.9, "clarity": 0.6},
            }
            return (score, metadata)

        scorer.async_score = AsyncMock(side_effect=async_score)
        return scorer

    @pytest.fixture
    def simple_scorer(self) -> Any:
        """Create a simple scorer that returns only score (no metadata)."""
        scorer = MagicMock()

        async def async_score(
            input_text: str, output: str, expected: str | None = None
        ) -> tuple[float, dict[str, Any]]:
            """Return score with empty metadata."""
            return (0.8, {})

        scorer.async_score = AsyncMock(side_effect=async_score)
        return scorer

    @pytest.mark.asyncio
    async def test_metadata_captured_from_evaluate(
        self, mock_agent: Any, critic_scorer: Any
    ) -> None:
        """evaluate() MUST capture scorer metadata and return it in EvaluationBatch."""
        from gepa_adk.adapters.adk_adapter import ADKAdapter

        adapter = ADKAdapter(agent=mock_agent, scorer=critic_scorer)

        # Mock the agent runner to avoid network calls
        async def mock_run(*args: Any, **kwargs: Any) -> Any:
            """Mock runner that yields a simple response event."""
            from google.genai import types

            event = MagicMock()
            event.is_final_response = MagicMock(return_value=True)
            event.actions = MagicMock()
            event.actions.response_content = [types.Part(text="Test response")]
            yield event

        import google.adk.runners

        original_run_async = google.adk.runners.Runner.run_async
        google.adk.runners.Runner.run_async = mock_run

        try:
            batch = [{"input": "What is 2+2?", "expected": "4"}]
            candidate = {"instruction": "Be precise"}

            result = await adapter.evaluate(batch, candidate, capture_traces=False)

            assert result.metadata is not None
            assert len(result.metadata) == 1
            assert (
                result.metadata[0]["feedback"]
                == "Good response but could be more concise"
            )
            assert result.metadata[0]["actionable_guidance"] == "Reduce length by 30%"
            assert result.metadata[0]["dimension_scores"]["accuracy"] == 0.9
        finally:
            google.adk.runners.Runner.run_async = original_run_async

    @pytest.mark.asyncio
    async def test_critic_metadata_flows_to_reflection(
        self, mock_agent: Any, critic_scorer: Any
    ) -> None:
        """Metadata from CriticScorer MUST flow to reflection dataset."""
        from gepa_adk.adapters.adk_adapter import ADKAdapter
        from gepa_adk.ports.adapter import EvaluationBatch

        adapter = ADKAdapter(agent=mock_agent, scorer=critic_scorer)

        # Create a mock EvaluationBatch with metadata (simulating what evaluate() would return)
        # This tests the metadata passthrough without needing to mock the full ADK runner
        mock_batch = EvaluationBatch(
            outputs=["Test response"],
            scores=[0.75],
            trajectories=None,
            metadata=[
                {
                    "feedback": "Good response but could be more concise",
                    "actionable_guidance": "Reduce length by 30%",
                    "dimension_scores": {"accuracy": 0.9, "clarity": 0.6},
                }
            ],
        )

        # Build reflection dataset with metadata
        candidate = {"instruction": "Be precise"}
        dataset = await adapter.make_reflective_dataset(
            candidate, mock_batch, ["instruction"]
        )

        # Verify metadata is in reflection examples
        assert "instruction" in dataset
        examples = dataset["instruction"]
        assert len(examples) == 1

        feedback = examples[0]["Feedback"]
        # Should include critic metadata
        assert "Good response but could be more concise" in feedback
        assert "Reduce length by 30%" in feedback
        assert "accuracy=0.9" in feedback or "accuracy=0.90" in feedback
        assert "clarity=0.6" in feedback or "clarity=0.60" in feedback

    @pytest.mark.asyncio
    async def test_simple_scorer_backward_compatibility(
        self, mock_agent: Any, simple_scorer: Any
    ) -> None:
        """Simple scorer (no metadata) MUST work without errors."""
        from gepa_adk.adapters.adk_adapter import ADKAdapter

        adapter = ADKAdapter(agent=mock_agent, scorer=simple_scorer)

        # Mock the agent runner
        async def mock_run(*args: Any, **kwargs: Any) -> Any:
            """Mock runner that yields a simple response event."""
            from google.genai import types

            event = MagicMock()
            event.is_final_response = MagicMock(return_value=True)
            event.actions = MagicMock()
            event.actions.response_content = [types.Part(text="Test response")]
            yield event

        import google.adk.runners

        original_run_async = google.adk.runners.Runner.run_async
        google.adk.runners.Runner.run_async = mock_run

        try:
            # Evaluate with simple scorer (no metadata)
            batch = [{"input": "What is 2+2?", "expected": "4"}]
            candidate = {"instruction": "Be precise"}
            result = await adapter.evaluate(batch, candidate, capture_traces=False)

            # Metadata should be None (all empty dicts converted to None)
            assert result.metadata is None

            # Build reflection dataset (should work without errors)
            dataset = await adapter.make_reflective_dataset(
                candidate, result, ["instruction"]
            )

            # Should still produce valid reflection examples
            assert "instruction" in dataset
            examples = dataset["instruction"]
            assert len(examples) == 1

            feedback = examples[0]["Feedback"]
            # Should have score but no metadata fields
            assert "score:" in feedback
            assert "Feedback:" not in feedback
            assert "Guidance:" not in feedback
            assert "Dimensions:" not in feedback
        finally:
            # Restore original
            google.adk.runners.Runner.run_async = original_run_async
