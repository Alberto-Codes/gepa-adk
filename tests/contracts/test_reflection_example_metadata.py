"""Contract tests for _build_trial with metadata.

These tests verify the contract for the _build_trial method that builds
trial records with structured feedback for reflection.

Terminology:
    - trial: One performance record {feedback, trajectory}
    - feedback: Critic evaluation {score, feedback_text, feedback_*}
    - trajectory: The journey {input, output, optional trace details}

Run: pytest tests/contracts/test_reflection_example_metadata.py -v
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.contract


class TestBuildTrialMetadataContract:
    """Contract tests for _build_trial metadata integration."""

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

        mock_executor = MagicMock()
        reflection_agent = LlmAgent(name="reflector", model="gemini-2.0-flash")

        return ADKAdapter(
            agent=agent,
            scorer=scorer,
            executor=mock_executor,
            reflection_agent=reflection_agent,
        )

    def test_feedback_includes_score_baseline(self, adapter: Any) -> None:
        """Feedback dict MUST include score as baseline."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
        )

        assert result["feedback"]["score"] == 0.75

    def test_feedback_includes_critic_feedback_text(self, adapter: Any) -> None:
        """Feedback dict MUST include feedback_text when present in metadata."""
        metadata = {"feedback": "Good response but could be more concise"}

        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=metadata,
        )

        assert (
            result["feedback"]["feedback_text"]
            == "Good response but could be more concise"
        )

    def test_feedback_includes_actionable_guidance(self, adapter: Any) -> None:
        """Feedback dict MUST include guidance when present."""
        metadata = {"actionable_guidance": "Reduce response length by 30%"}

        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.65,
            trajectory=None,
            metadata=metadata,
        )

        assert (
            result["feedback"]["guidance"] == "Reduce response length by 30%"
        )

    def test_feedback_includes_dimension_scores(self, adapter: Any) -> None:
        """Feedback dict MUST include dimensions when present."""
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

        assert result["feedback"]["dimensions"] == {
            "accuracy": 0.9,
            "clarity": 0.6,
            "completeness": 0.8,
        }

    def test_feedback_omits_empty_metadata_fields(self, adapter: Any) -> None:
        """Feedback dict MUST NOT include empty optional fields but ALWAYS has feedback_text."""
        metadata = {"feedback": "", "actionable_guidance": ""}  # Empty strings

        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=metadata,
        )

        feedback = result["feedback"]
        # Should always have score and feedback_text (even if empty)
        assert feedback["score"] == 0.75
        assert feedback["feedback_text"] == ""
        # Empty optional fields should be omitted
        assert "guidance" not in feedback

    def test_feedback_handles_none_metadata(self, adapter: Any) -> None:
        """Feedback dict MUST work when metadata is None (backward compat)."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=None,
        )

        # Should still produce valid feedback with score
        assert result["feedback"]["score"] == 0.75
        # Structure should be valid (input/output nested in trajectory)
        assert "input" in result["trajectory"]
        assert "output" in result["trajectory"]

    def test_feedback_handles_missing_metadata_parameter(self, adapter: Any) -> None:
        """Feedback dict MUST work when metadata parameter not provided."""
        # Call without metadata parameter (default)
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
        )

        assert result["feedback"]["score"] == 0.75

    def test_trajectory_info_in_separate_field(self, adapter: Any) -> None:
        """Trajectory info MUST be in separate trajectory field."""
        from gepa_adk.domain.trajectory import ADKTrajectory, TokenUsage, ToolCallRecord

        trajectory = ADKTrajectory(
            tool_calls=(
                ToolCallRecord(
                    name="tool1",
                    arguments={},
                    result=None,
                    timestamp=0.0,
                ),
            ),
            state_deltas=(),
            token_usage=TokenUsage(
                input_tokens=50, output_tokens=100, total_tokens=150
            ),
            final_output="test",
            error=None,
        )
        metadata = {"feedback": "Good job"}

        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=trajectory,
            metadata=metadata,
        )

        # Trajectory should be separate from feedback
        assert "trajectory" in result
        # Trace details are nested inside trajectory.trace
        assert "trace" in result["trajectory"]
        assert result["trajectory"]["trace"]["tool_calls"] == 1
        assert result["trajectory"]["trace"]["tokens"] == 150
        # Feedback should have critic data
        assert result["feedback"]["feedback_text"] == "Good job"

    def test_full_metadata_format(self, adapter: Any) -> None:
        """Trial MUST include all CriticScorer metadata in feedback."""
        metadata = {
            "feedback": "Good response but verbose",
            "actionable_guidance": "Reduce length by 30%",
            "dimension_scores": {"accuracy": 0.9, "clarity": 0.6},
        }

        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=metadata,
        )

        feedback = result["feedback"]
        assert feedback["score"] == 0.75
        assert feedback["feedback_text"] == "Good response but verbose"
        assert feedback["guidance"] == "Reduce length by 30%"
        assert feedback["dimensions"] == {"accuracy": 0.9, "clarity": 0.6}


class TestNormalizedFeedbackSchema:
    """Contract tests for normalized feedback schema (T022)."""

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

        mock_executor = MagicMock()
        reflection_agent = LlmAgent(name="reflector", model="gemini-2.0-flash")

        return ADKAdapter(
            agent=agent,
            scorer=scorer,
            executor=mock_executor,
            reflection_agent=reflection_agent,
        )

    def test_normalized_feedback_always_has_score(self, adapter: Any) -> None:
        """T022: Normalized feedback MUST always contain score key."""
        # Test with None metadata
        result = adapter._build_trial(
            input_text="Test input",
            output="Test output",
            score=0.5,
            trajectory=None,
            metadata=None,
        )
        assert "score" in result["feedback"]
        assert result["feedback"]["score"] == 0.5

        # Test with string metadata (simple format)
        result = adapter._build_trial(
            input_text="Test input",
            output="Test output",
            score=0.75,
            trajectory=None,
            metadata="Simple feedback",
        )
        assert "score" in result["feedback"]
        assert result["feedback"]["score"] == 0.75

        # Test with dict metadata (advanced format)
        result = adapter._build_trial(
            input_text="Test input",
            output="Test output",
            score=0.9,
            trajectory=None,
            metadata={"feedback_text": "Advanced feedback"},
        )
        assert "score" in result["feedback"]
        assert result["feedback"]["score"] == 0.9

    def test_normalized_feedback_always_has_feedback_text(self, adapter: Any) -> None:
        """T022: Normalized feedback MUST always contain feedback_text key."""
        # Test with None metadata - should default to empty string
        result = adapter._build_trial(
            input_text="Test input",
            output="Test output",
            score=0.5,
            trajectory=None,
            metadata=None,
        )
        assert "feedback_text" in result["feedback"]
        assert result["feedback"]["feedback_text"] == ""

        # Test with string metadata
        result = adapter._build_trial(
            input_text="Test input",
            output="Test output",
            score=0.75,
            trajectory=None,
            metadata="Simple feedback",
        )
        assert "feedback_text" in result["feedback"]
        assert result["feedback"]["feedback_text"] == "Simple feedback"

        # Test with dict metadata containing feedback key
        result = adapter._build_trial(
            input_text="Test input",
            output="Test output",
            score=0.9,
            trajectory=None,
            metadata={"feedback": "Legacy feedback"},
        )
        assert "feedback_text" in result["feedback"]
        assert result["feedback"]["feedback_text"] == "Legacy feedback"

        # Test with dict metadata containing feedback_text key
        result = adapter._build_trial(
            input_text="Test input",
            output="Test output",
            score=0.85,
            trajectory=None,
            metadata={"feedback_text": "Direct feedback_text"},
        )
        assert "feedback_text" in result["feedback"]
        assert result["feedback"]["feedback_text"] == "Direct feedback_text"

    def test_normalized_field_mapping_dimension_scores_to_dimensions(
        self, adapter: Any
    ) -> None:
        """T022: dimension_scores in input MUST map to dimensions in output."""
        metadata = {
            "feedback_text": "Good work",
            "dimension_scores": {"clarity": 0.8, "accuracy": 0.9},
        }

        result = adapter._build_trial(
            input_text="Test input",
            output="Test output",
            score=0.85,
            trajectory=None,
            metadata=metadata,
        )

        # Should have dimensions, not dimension_scores
        assert "dimensions" in result["feedback"]
        assert result["feedback"]["dimensions"] == {"clarity": 0.8, "accuracy": 0.9}
        # Original key should not be in output
        assert "dimension_scores" not in result["feedback"]

    def test_normalized_field_mapping_actionable_guidance_to_guidance(
        self, adapter: Any
    ) -> None:
        """T022: actionable_guidance in input MUST map to guidance in output."""
        metadata = {
            "feedback_text": "Needs improvement",
            "actionable_guidance": "Add more examples",
        }

        result = adapter._build_trial(
            input_text="Test input",
            output="Test output",
            score=0.6,
            trajectory=None,
            metadata=metadata,
        )

        # Should have guidance, not actionable_guidance
        assert "guidance" in result["feedback"]
        assert result["feedback"]["guidance"] == "Add more examples"
        # Original key should not be in output
        assert "actionable_guidance" not in result["feedback"]

    def test_normalized_custom_fields_pass_through(self, adapter: Any) -> None:
        """T022: Custom fields in metadata MUST pass through unchanged."""
        metadata = {
            "feedback_text": "Good",
            "custom_metric": 42,
            "user_data": {"id": 123},
        }

        result = adapter._build_trial(
            input_text="Test input",
            output="Test output",
            score=0.7,
            trajectory=None,
            metadata=metadata,
        )

        # Custom fields should pass through
        assert result["feedback"]["custom_metric"] == 42
        assert result["feedback"]["user_data"] == {"id": 123}


class TestTrialStructure:
    """Tests for trial structure compliance."""

    @pytest.fixture
    def adapter(self) -> Any:
        """Create an ADKAdapter instance for testing."""
        from google.adk.agents import LlmAgent

        from gepa_adk.adapters.adk_adapter import ADKAdapter

        agent = MagicMock(spec=LlmAgent)
        agent.instruction = "test"
        agent.name = "test_agent"
        scorer = MagicMock()
        mock_executor = MagicMock()
        reflection_agent = LlmAgent(name="reflector", model="gemini-2.0-flash")

        return ADKAdapter(
            agent=agent,
            scorer=scorer,
            executor=mock_executor,
            reflection_agent=reflection_agent,
        )

    def test_trial_has_required_keys(self, adapter: Any) -> None:
        """Trial MUST have feedback and trajectory keys."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata={"feedback": "good"},
        )

        assert "feedback" in result
        assert "trajectory" in result
        # input/output are nested in trajectory
        assert "input" in result["trajectory"]
        assert "output" in result["trajectory"]

    def test_trial_input_is_string(self, adapter: Any) -> None:
        """Trial trajectory.input MUST be the input text directly."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=None,
        )

        assert result["trajectory"]["input"] == "I am the King"

    def test_trial_output_is_string(self, adapter: Any) -> None:
        """Trial trajectory.output MUST be the output string."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="This is the agent response",
            score=0.75,
            trajectory=None,
            metadata=None,
        )

        assert result["trajectory"]["output"] == "This is the agent response"

    def test_trial_feedback_is_dict(self, adapter: Any) -> None:
        """Trial feedback MUST be a dict with score."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=None,
        )

        assert isinstance(result["feedback"], dict)
        assert "score" in result["feedback"]

    def test_trial_trajectory_always_has_input_output(self, adapter: Any) -> None:
        """Trial trajectory MUST always have input and output."""
        result = adapter._build_trial(
            input_text="I am the King",
            output="test output",
            score=0.75,
            trajectory=None,
            metadata=None,
        )

        # trajectory always has input/output, trace details are optional
        assert "trajectory" in result
        assert result["trajectory"]["input"] == "I am the King"
        assert result["trajectory"]["output"] == "test output"
        # trace details like tool_calls are optional
        assert "tool_calls" not in result["trajectory"]
