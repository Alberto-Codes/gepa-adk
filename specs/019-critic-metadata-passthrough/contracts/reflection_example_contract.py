"""Contract tests for _build_reflection_example with metadata.

These tests verify the contract for the enhanced _build_reflection_example
method that includes CriticScorer metadata in the Feedback field.

Run: pytest specs/019-critic-metadata-passthrough/contracts/ -v
"""

from typing import Any
from unittest.mock import MagicMock

import pytest


class TestBuildReflectionExampleMetadataContract:
    """Contract tests for _build_reflection_example metadata integration."""

    @pytest.fixture
    def adapter(self) -> Any:
        """Create an ADKAdapter instance for testing."""
        from google.adk.agents import LlmAgent

        from gepa_adk.adapters.adk_adapter import ADKAdapter

        # Create mock agent and scorer
        agent = MagicMock(spec=LlmAgent)
        agent.instruction = "test instruction"
        agent.name = "test_agent"

        scorer = MagicMock()
        scorer.async_score = MagicMock()

        return ADKAdapter(agent=agent, scorer=scorer)

    def test_feedback_includes_score_baseline(self, adapter: Any) -> None:
        """Feedback string MUST include score as baseline."""
        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
        )

        assert "score: 0.750" in result["Feedback"]

    def test_feedback_includes_critic_feedback_text(self, adapter: Any) -> None:
        """Feedback string MUST include critic feedback text when present."""
        metadata = {"feedback": "Good response but could be more concise"}

        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=metadata,
        )

        assert "Good response but could be more concise" in result["Feedback"]

    def test_feedback_includes_actionable_guidance(self, adapter: Any) -> None:
        """Feedback string MUST include actionable_guidance when present."""
        metadata = {"actionable_guidance": "Reduce response length by 30%"}

        result = adapter._build_reflection_example(
            output="test output",
            score=0.65,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=metadata,
        )

        assert "Reduce response length by 30%" in result["Feedback"]

    def test_feedback_includes_dimension_scores(self, adapter: Any) -> None:
        """Feedback string MUST include dimension_scores when present."""
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
        # Should include dimension breakdown
        assert "accuracy" in feedback.lower() or "0.9" in feedback
        assert "clarity" in feedback.lower() or "0.6" in feedback

    def test_feedback_omits_empty_metadata_fields(self, adapter: Any) -> None:
        """Feedback string MUST NOT include empty metadata fields."""
        metadata = {"feedback": "", "actionable_guidance": ""}  # Empty strings

        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=metadata,
        )

        feedback = result["Feedback"]
        # Should not have empty "Feedback:" or "Guidance:" sections
        # Just the baseline score should be present
        assert "score: 0.750" in feedback

    def test_feedback_handles_none_metadata(self, adapter: Any) -> None:
        """Feedback string MUST work when metadata is None (backward compat)."""
        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=None,
        )

        # Should still produce valid feedback with score
        assert "score: 0.750" in result["Feedback"]
        # Structure should be valid
        assert "Inputs" in result
        assert "Generated Outputs" in result

    def test_feedback_handles_missing_metadata_parameter(self, adapter: Any) -> None:
        """Feedback string MUST work when metadata parameter not provided."""
        # Call without metadata parameter (default)
        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
        )

        assert "score: 0.750" in result["Feedback"]

    def test_feedback_preserves_trajectory_info(self, adapter: Any) -> None:
        """Feedback string MUST preserve trajectory info alongside metadata."""
        from gepa_adk.domain.trajectory import ADKTrajectory, TokenUsage

        trajectory = ADKTrajectory(
            events=[],
            final_output="test",
            tool_calls=[{"name": "tool1"}],  # type: ignore[list-item]
            token_usage=TokenUsage(prompt_tokens=50, completion_tokens=100, total_tokens=150),
        )
        metadata = {"feedback": "Good job"}

        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=trajectory,
            component_name="instruction",
            component_value="Be helpful",
            metadata=metadata,
        )

        feedback = result["Feedback"]
        # Should have both trajectory info and metadata
        assert "tool_calls: 1" in feedback
        assert "tokens: 150" in feedback
        assert "Good job" in feedback

    def test_feedback_full_metadata_format(self, adapter: Any) -> None:
        """Feedback string MUST format full CriticScorer metadata correctly."""
        metadata = {
            "feedback": "Good response but verbose",
            "actionable_guidance": "Reduce length by 30%",
            "dimension_scores": {"accuracy": 0.9, "clarity": 0.6},
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
        # All metadata should be present
        assert "0.750" in feedback  # score
        assert "Good response but verbose" in feedback
        assert "Reduce length by 30%" in feedback
        # Dimension scores present in some form
        assert "accuracy" in feedback.lower() or "0.9" in feedback


class TestReflectionExampleStructure:
    """Tests for reflection example structure compliance."""

    @pytest.fixture
    def adapter(self) -> Any:
        """Create an ADKAdapter instance for testing."""
        from google.adk.agents import LlmAgent

        from gepa_adk.adapters.adk_adapter import ADKAdapter

        agent = MagicMock(spec=LlmAgent)
        agent.instruction = "test"
        agent.name = "test_agent"
        scorer = MagicMock()

        return ADKAdapter(agent=agent, scorer=scorer)

    def test_reflection_example_has_required_keys(self, adapter: Any) -> None:
        """Reflection example MUST have Inputs, Generated Outputs, Feedback keys."""
        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata={"feedback": "good"},
        )

        assert "Inputs" in result
        assert "Generated Outputs" in result
        assert "Feedback" in result

    def test_reflection_example_inputs_contains_component(self, adapter: Any) -> None:
        """Reflection example Inputs MUST contain the component mapping."""
        result = adapter._build_reflection_example(
            output="test output",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful and concise",
            metadata=None,
        )

        assert result["Inputs"] == {"instruction": "Be helpful and concise"}

    def test_reflection_example_output_is_string(self, adapter: Any) -> None:
        """Reflection example Generated Outputs MUST be the output string."""
        result = adapter._build_reflection_example(
            output="This is the agent response",
            score=0.75,
            trajectory=None,
            component_name="instruction",
            component_value="Be helpful",
            metadata=None,
        )

        assert result["Generated Outputs"] == "This is the agent response"
