"""Unit tests for ADKAdapter metadata handling.

Tests for dimension_scores formatting and other metadata-related functionality.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


class TestDimensionScoresFormatting:
    """Unit tests for dimension_scores formatting in _build_reflection_example."""

    @pytest.fixture
    def adapter(self) -> Any:
        """Create an ADKAdapter instance for testing."""
        from google.adk.agents import LlmAgent

        from gepa_adk.adapters.adk_adapter import ADKAdapter

        agent = MagicMock(spec=LlmAgent)
        agent.instruction = "test instruction"
        agent.name = "test_agent"

        scorer = MagicMock()
        scorer.async_score = MagicMock()

        return ADKAdapter(agent=agent, scorer=scorer)

    def test_dimension_scores_formatted_correctly(self, adapter: Any) -> None:
        """Dimension scores should be formatted as 'Dimensions: key1=val1, key2=val2'."""
        metadata = {
            "dimension_scores": {"accuracy": 0.9, "clarity": 0.6, "completeness": 0.8}
        }

        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=metadata,
        )

        feedback = result["Feedback"]
        # Should include "Dimensions:" prefix
        assert "Dimensions:" in feedback
        # Should include all dimension keys and values
        assert "accuracy=0.9" in feedback or "accuracy=0.900" in feedback
        assert "clarity=0.6" in feedback or "clarity=0.600" in feedback
        assert "completeness=0.8" in feedback or "completeness=0.800" in feedback

    def test_dimension_scores_with_single_dimension(self, adapter: Any) -> None:
        """Dimension scores with single dimension should format correctly."""
        metadata = {"dimension_scores": {"accuracy": 0.95}}

        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=metadata,
        )

        feedback = result["Feedback"]
        assert "Dimensions:" in feedback
        assert "accuracy" in feedback.lower()
        assert "0.95" in feedback or "0.950" in feedback

    def test_dimension_scores_empty_dict_omitted(self, adapter: Any) -> None:
        """Empty dimension_scores dict should not add Dimensions section."""
        metadata = {"dimension_scores": {}}

        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=metadata,
        )

        feedback = result["Feedback"]
        # Should not include Dimensions section for empty dict
        assert "Dimensions:" not in feedback
        # Should still have score
        assert "score: 0.750" in feedback


class TestBackwardCompatibility:
    """Unit tests for backward compatibility with None, empty, partial, and malformed metadata."""

    @pytest.fixture
    def adapter(self) -> Any:
        """Create an ADKAdapter instance for testing."""
        from google.adk.agents import LlmAgent

        from gepa_adk.adapters.adk_adapter import ADKAdapter

        agent = MagicMock(spec=LlmAgent)
        agent.instruction = "test instruction"
        agent.name = "test_agent"

        scorer = MagicMock()
        scorer.async_score = MagicMock()

        return ADKAdapter(agent=agent, scorer=scorer)

    def test_None_metadata_handling(self, adapter: Any) -> None:
        """_build_reflection_example should handle metadata=None gracefully."""
        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=None,
        )

        # Should produce valid feedback with just score
        assert "score: 0.750" in result["Feedback"]
        assert "Inputs" in result
        assert "Generated Outputs" in result
        # Should not have any metadata-related text
        assert "Feedback:" not in result["Feedback"]
        assert "Guidance:" not in result["Feedback"]
        assert "Dimensions:" not in result["Feedback"]

    def test_empty_dict_metadata_handling(self, adapter: Any) -> None:
        """_build_reflection_example should handle empty dict metadata gracefully."""
        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata={},
        )

        # Should produce valid feedback with just score
        assert "score: 0.750" in result["Feedback"]
        # Should not add any metadata sections for empty dict
        assert "Feedback:" not in result["Feedback"]
        assert "Guidance:" not in result["Feedback"]
        assert "Dimensions:" not in result["Feedback"]

    def test_partial_metadata_handling(self, adapter: Any) -> None:
        """_build_reflection_example should handle partial metadata (only some fields) gracefully."""
        # Only feedback, no guidance or dimension_scores
        metadata = {"feedback": "Good response"}

        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=metadata,
        )

        feedback = result["Feedback"]
        # Should include feedback
        assert "Feedback: Good response" in feedback
        # Should not include guidance or dimensions
        assert "Guidance:" not in feedback
        assert "Dimensions:" not in feedback

    def test_malformed_metadata_type_handling(self, adapter: Any) -> None:
        """_build_reflection_example should log warning and handle non-dict metadata gracefully."""
        # Pass a non-dict type (should log warning and fall back to score-only)
        metadata = "not a dict"  # type: ignore[assignment]

        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=metadata,  # type: ignore[arg-type]
        )

        # Should still produce valid feedback with just score (falls back gracefully)
        assert "score: 0.750" in result["Feedback"]
        # Should not include any metadata sections
        assert "Feedback:" not in result["Feedback"]
        assert "Guidance:" not in result["Feedback"]
        assert "Dimensions:" not in result["Feedback"]
