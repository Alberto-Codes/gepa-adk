"""Unit tests for TrialBuilder and normalize_feedback function."""

from gepa_adk.adapters.trial_builder import TrialBuilder, normalize_feedback


class TestNormalizeFeedback:
    """Unit tests for the normalize_feedback function."""

    # T007: Simple string feedback
    def test_normalize_string_feedback(self):
        """Test normalizing simple string feedback."""
        result = normalize_feedback(0.75, "Good but verbose")
        assert result == {"score": 0.75, "feedback_text": "Good but verbose"}

    # T008: Empty string feedback
    def test_normalize_empty_string(self):
        """Test normalizing empty string feedback."""
        result = normalize_feedback(0.0, "")
        assert result == {"score": 0.0, "feedback_text": ""}

    # T009: None feedback
    def test_normalize_none_feedback(self):
        """Test normalizing None feedback."""
        result = normalize_feedback(1.0, None)
        assert result == {"score": 1.0, "feedback_text": ""}

    # T014: Advanced format with full dict
    def test_normalize_advanced_full(self):
        """Test normalizing advanced feedback with all fields."""
        result = normalize_feedback(
            0.45,
            {
                "feedback_text": "Too clinical",
                "dimension_scores": {"voice": 0.2, "urgency": 0.4},
                "actionable_guidance": "Add I statements",
            },
        )
        assert result["score"] == 0.45
        assert result["feedback_text"] == "Too clinical"
        assert result["dimensions"] == {"voice": 0.2, "urgency": 0.4}
        assert result["guidance"] == "Add I statements"

    # T015: Fallback to "feedback" key
    def test_normalize_fallback_feedback_key(self):
        """Test normalizing with legacy 'feedback' key."""
        result = normalize_feedback(0.6, {"feedback": "Legacy format"})
        assert result == {"score": 0.6, "feedback_text": "Legacy format"}

    # T016: Custom fields pass through
    def test_normalize_custom_fields(self):
        """Test that custom fields are preserved."""
        result = normalize_feedback(
            0.7,
            {"feedback_text": "OK", "custom_metric": 42, "user_data": {"id": 123}},
        )
        assert result["score"] == 0.7
        assert result["feedback_text"] == "OK"
        assert result["custom_metric"] == 42
        assert result["user_data"] == {"id": 123}

    # T017: Explicit score parameter wins
    def test_normalize_dict_score_ignored(self):
        """Test that explicit score parameter takes precedence over dict score."""
        result = normalize_feedback(0.5, {"score": 0.9, "feedback": "X"})
        assert result["score"] == 0.5  # Explicit param wins
        assert result["feedback_text"] == "X"

    # T018: Non-string feedback_text converts to string
    def test_normalize_nonstring_feedback(self):
        """Test that non-string feedback_text is converted to string."""
        result = normalize_feedback(0.5, {"feedback_text": 123})
        assert result["feedback_text"] == "123"

    # T019: Empty dimensions dict is excluded
    def test_normalize_empty_dimensions(self):
        """Test that empty dimension_scores dict is not included."""
        result = normalize_feedback(0.5, {"dimension_scores": {}})
        assert "dimensions" not in result
        assert result["feedback_text"] == ""

    # Edge case: Empty feedback_text with fallback feedback key present
    def test_normalize_empty_feedback_text_with_fallback(self):
        """Test that empty string feedback_text is preserved, not overwritten by fallback."""
        result = normalize_feedback(
            0.5, {"feedback_text": "", "feedback": "Fallback text"}
        )
        assert result["feedback_text"] == ""  # Empty string preserved, not fallback


class TestTrialBuilder:
    """Unit tests for the TrialBuilder class."""

    def test_build_feedback_minimal(self):
        """Test building minimal feedback with just score."""
        builder = TrialBuilder()
        feedback = builder.build_feedback(0.75)
        assert feedback["score"] == 0.75
        assert "feedback_text" in feedback

    def test_build_feedback_with_metadata(self):
        """Test building feedback with metadata."""
        builder = TrialBuilder()
        feedback = builder.build_feedback(
            0.85,
            metadata={"feedback": "Good work", "dimension_scores": {"accuracy": 0.9}},
        )
        assert feedback["score"] == 0.85
        assert feedback["feedback_text"] == "Good work"
        assert feedback["dimensions"] == {"accuracy": 0.9}

    def test_build_trial_minimal(self):
        """Test building minimal trial record."""
        builder = TrialBuilder()
        trial = builder.build_trial(
            input_text="What is 2+2?",
            output="4",
            score=0.95,
        )
        assert trial["feedback"]["score"] == 0.95
        assert trial["trajectory"]["input"] == "What is 2+2?"
        assert trial["trajectory"]["output"] == "4"
