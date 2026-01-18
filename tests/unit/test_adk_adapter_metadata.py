"""Unit tests for ADKAdapter metadata handling.

Tests for dimension_scores formatting and other metadata-related functionality
in the _build_trial method.

Terminology:
    - trial: One performance record {input, output, feedback, trajectory}
    - feedback: Critic evaluation {score, feedback_text, feedback_*}
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


class TestDimensionScoresFormatting:
    """Unit tests for dimension_scores formatting in _build_trial."""

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
        """Dimension scores should be in feedback_dimensions dict."""
        metadata = {
            "dimension_scores": {"accuracy": 0.9, "clarity": 0.6, "completeness": 0.8}
        }

        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=metadata,
        )

        feedback = result["feedback"]
        assert "feedback_dimensions" in feedback
        assert feedback["feedback_dimensions"]["accuracy"] == 0.9
        assert feedback["feedback_dimensions"]["clarity"] == 0.6
        assert feedback["feedback_dimensions"]["completeness"] == 0.8

    def test_dimension_scores_with_single_dimension(self, adapter: Any) -> None:
        """Dimension scores with single dimension should format correctly."""
        metadata = {"dimension_scores": {"accuracy": 0.95}}

        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=metadata,
        )

        feedback = result["feedback"]
        assert "feedback_dimensions" in feedback
        assert feedback["feedback_dimensions"]["accuracy"] == 0.95

    def test_dimension_scores_empty_dict_omitted(self, adapter: Any) -> None:
        """Empty dimension_scores dict should not add feedback_dimensions."""
        metadata = {"dimension_scores": {}}

        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=metadata,
        )

        feedback = result["feedback"]
        # Should not include feedback_dimensions for empty dict
        assert "feedback_dimensions" not in feedback
        # Should still have score
        assert feedback["score"] == 0.75


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
        """_build_trial should handle metadata=None gracefully."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=None,
        )

        # Should produce valid trial with just score in feedback
        assert result["feedback"]["score"] == 0.75
        # input/output nested in trajectory
        assert "input" in result["trajectory"]
        assert "output" in result["trajectory"]
        # Should not have any extra feedback fields
        assert "feedback_text" not in result["feedback"]
        assert "feedback_guidance" not in result["feedback"]
        assert "feedback_dimensions" not in result["feedback"]

    def test_empty_dict_metadata_handling(self, adapter: Any) -> None:
        """_build_trial should handle empty dict metadata gracefully."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata={},
        )

        # Should produce valid trial with just score
        assert result["feedback"]["score"] == 0.75
        # Should not add any metadata fields for empty dict
        assert "feedback_text" not in result["feedback"]
        assert "feedback_guidance" not in result["feedback"]
        assert "feedback_dimensions" not in result["feedback"]

    def test_partial_metadata_handling(self, adapter: Any) -> None:
        """_build_trial handles partial metadata gracefully."""
        # Only feedback, no guidance or dimension_scores
        metadata = {"feedback": "Good response"}

        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=metadata,
        )

        feedback = result["feedback"]
        # Should include feedback_text
        assert feedback["feedback_text"] == "Good response"
        # Should not include guidance or dimensions
        assert "feedback_guidance" not in feedback
        assert "feedback_dimensions" not in feedback

    def test_malformed_metadata_type_handling(self, adapter: Any) -> None:
        """_build_trial should log warning and handle non-dict metadata gracefully."""
        # Pass a non-dict type (should log warning and fall back to score-only)
        metadata = "not a dict"

        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=metadata,
        )

        # Should still produce valid trial with just score (falls back gracefully)
        assert result["feedback"]["score"] == 0.75
        # Should not include any extra feedback fields
        assert "feedback_text" not in result["feedback"]
        assert "feedback_guidance" not in result["feedback"]
        assert "feedback_dimensions" not in result["feedback"]
