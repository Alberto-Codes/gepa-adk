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

        from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter

        agent = MagicMock(spec=LlmAgent)
        agent.instruction = "test instruction"
        agent.name = "test_agent"

        scorer = MagicMock()
        scorer.async_score = MagicMock()

        mock_executor = MagicMock()
        mock_proposer = MagicMock()
        mock_proposer.propose = MagicMock()
        return ADKAdapter(
            agent=agent,
            scorer=scorer,
            executor=mock_executor,
            proposer=mock_proposer,
        )

    def test_dimension_scores_formatted_correctly(self, adapter: Any) -> None:
        """Dimension scores should be in dimensions dict."""
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
        assert "dimensions" in feedback
        assert feedback["dimensions"]["accuracy"] == 0.9
        assert feedback["dimensions"]["clarity"] == 0.6
        assert feedback["dimensions"]["completeness"] == 0.8

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
        assert "dimensions" in feedback
        assert feedback["dimensions"]["accuracy"] == 0.95

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
        # Should not include dimensions for empty dict
        assert "dimensions" not in feedback
        # Should still have score
        assert feedback["score"] == 0.75


class TestBackwardCompatibility:
    """Unit tests for backward compatibility with None, empty, partial, and malformed metadata."""

    @pytest.fixture
    def adapter(self) -> Any:
        """Create an ADKAdapter instance for testing."""
        from google.adk.agents import LlmAgent

        from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter

        agent = MagicMock(spec=LlmAgent)
        agent.instruction = "test instruction"
        agent.name = "test_agent"

        scorer = MagicMock()
        scorer.async_score = MagicMock()

        mock_executor = MagicMock()
        mock_proposer = MagicMock()
        mock_proposer.propose = MagicMock()
        return ADKAdapter(
            agent=agent,
            scorer=scorer,
            executor=mock_executor,
            proposer=mock_proposer,
        )

    def test_None_metadata_handling(self, adapter: Any) -> None:
        """_build_trial should handle metadata=None gracefully."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=None,
        )

        # Should produce valid trial with score and empty feedback_text
        assert result["feedback"]["score"] == 0.75
        assert (
            result["feedback"]["feedback_text"] == ""
        )  # Always present, empty if no metadata
        # input/output nested in trajectory
        assert "input" in result["trajectory"]
        assert "output" in result["trajectory"]
        # Should not have optional fields when metadata is None
        assert "guidance" not in result["feedback"]
        assert "dimensions" not in result["feedback"]

    def test_empty_dict_metadata_handling(self, adapter: Any) -> None:
        """_build_trial should handle empty dict metadata gracefully."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata={},
        )

        # Should produce valid trial with score and empty feedback_text
        assert result["feedback"]["score"] == 0.75
        assert (
            result["feedback"]["feedback_text"] == ""
        )  # Always present, empty if no data
        # Should not add optional fields for empty dict
        assert "guidance" not in result["feedback"]
        assert "dimensions" not in result["feedback"]

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
        # Should not include optional fields
        assert "guidance" not in feedback
        assert "dimensions" not in feedback

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

        # Should still produce valid trial, treating string as feedback_text
        assert result["feedback"]["score"] == 0.75
        assert (
            result["feedback"]["feedback_text"] == "not a dict"
        )  # String metadata becomes feedback_text
        # Should not include optional fields when metadata is not a dict
        assert "guidance" not in result["feedback"]
        assert "dimensions" not in result["feedback"]
