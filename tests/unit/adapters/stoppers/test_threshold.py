"""Unit tests for ScoreThresholdStopper.

Tests cover all acceptance criteria from issue #193:
- Stop when threshold reached (best_score > threshold)
- Stop when threshold exactly met (best_score == threshold)
- Continue below threshold (best_score < threshold)
- Handle negative scores (-0.3 >= -0.5)
- Protocol compliance
"""

import pytest

from gepa_adk.adapters.stoppers import ScoreThresholdStopper
from gepa_adk.domain.stopper import StopperState
from gepa_adk.ports.stopper import StopperProtocol

pytestmark = pytest.mark.unit


@pytest.fixture
def default_state() -> StopperState:
    """Create a default stopper state for testing."""
    return StopperState(
        iteration=5,
        best_score=0.5,
        stagnation_counter=0,
        total_evaluations=25,
        candidates_count=1,
        elapsed_seconds=30.0,
    )


class TestScoreThresholdStopperInitialization:
    """Tests for ScoreThresholdStopper initialization."""

    def test_init_with_positive_threshold_succeeds(self) -> None:
        """ScoreThresholdStopper accepts positive threshold values."""
        stopper = ScoreThresholdStopper(0.9)

        assert stopper.threshold == 0.9

    def test_init_with_zero_threshold_succeeds(self) -> None:
        """ScoreThresholdStopper accepts zero threshold."""
        stopper = ScoreThresholdStopper(0.0)

        assert stopper.threshold == 0.0

    def test_init_with_negative_threshold_succeeds(self) -> None:
        """ScoreThresholdStopper accepts negative threshold values."""
        stopper = ScoreThresholdStopper(-0.5)

        assert stopper.threshold == -0.5

    def test_init_with_one_threshold_succeeds(self) -> None:
        """ScoreThresholdStopper accepts threshold of 1.0."""
        stopper = ScoreThresholdStopper(1.0)

        assert stopper.threshold == 1.0


class TestScoreThresholdStopperBehavior:
    """Tests for ScoreThresholdStopper stopping behavior."""

    def test_returns_true_when_score_exceeds_threshold(self) -> None:
        """Stopper returns True when best score exceeds threshold."""
        stopper = ScoreThresholdStopper(0.9)
        state = StopperState(
            iteration=10,
            best_score=0.92,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=2,
            elapsed_seconds=60.0,
        )

        result = stopper(state)

        assert result is True

    def test_returns_true_when_score_equals_threshold(self) -> None:
        """Stopper returns True when best score exactly equals threshold."""
        stopper = ScoreThresholdStopper(0.9)
        state = StopperState(
            iteration=10,
            best_score=0.9,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=2,
            elapsed_seconds=60.0,
        )

        result = stopper(state)

        assert result is True

    def test_returns_false_when_score_below_threshold(self) -> None:
        """Stopper returns False when best score is below threshold."""
        stopper = ScoreThresholdStopper(0.9)
        state = StopperState(
            iteration=10,
            best_score=0.85,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=2,
            elapsed_seconds=60.0,
        )

        result = stopper(state)

        assert result is False

    def test_returns_false_at_zero_score(self, default_state: StopperState) -> None:
        """Stopper returns False when evolution just started with zero score."""
        stopper = ScoreThresholdStopper(0.9)
        state = StopperState(
            iteration=0,
            best_score=0.0,
            stagnation_counter=0,
            total_evaluations=0,
            candidates_count=0,
            elapsed_seconds=0.0,
        )

        result = stopper(state)

        assert result is False


class TestScoreThresholdStopperNegativeScores:
    """Tests for ScoreThresholdStopper with negative scores."""

    def test_returns_true_when_negative_score_exceeds_negative_threshold(self) -> None:
        """Stopper returns True when -0.3 >= -0.5."""
        stopper = ScoreThresholdStopper(-0.5)
        state = StopperState(
            iteration=10,
            best_score=-0.3,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=2,
            elapsed_seconds=60.0,
        )

        result = stopper(state)

        assert result is True

    def test_returns_true_when_negative_scores_equal(self) -> None:
        """Stopper returns True when negative score equals negative threshold."""
        stopper = ScoreThresholdStopper(-0.5)
        state = StopperState(
            iteration=10,
            best_score=-0.5,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=2,
            elapsed_seconds=60.0,
        )

        result = stopper(state)

        assert result is True

    def test_returns_false_when_negative_score_below_threshold(self) -> None:
        """Stopper returns False when -0.7 < -0.5."""
        stopper = ScoreThresholdStopper(-0.5)
        state = StopperState(
            iteration=10,
            best_score=-0.7,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=2,
            elapsed_seconds=60.0,
        )

        result = stopper(state)

        assert result is False


class TestScoreThresholdStopperProtocolCompliance:
    """Tests verifying ScoreThresholdStopper satisfies StopperProtocol."""

    def test_satisfies_stopper_protocol(self) -> None:
        """ScoreThresholdStopper instance satisfies StopperProtocol."""
        stopper = ScoreThresholdStopper(0.9)

        assert isinstance(stopper, StopperProtocol)

    def test_call_returns_bool(self, default_state: StopperState) -> None:
        """ScoreThresholdStopper __call__ returns a boolean value."""
        stopper = ScoreThresholdStopper(0.9)

        result = stopper(default_state)

        assert isinstance(result, bool)


class TestScoreThresholdStopperEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_threshold(self) -> None:
        """Stopper handles very large threshold values."""
        stopper = ScoreThresholdStopper(float("inf"))
        state = StopperState(
            iteration=1000,
            best_score=0.99,
            stagnation_counter=0,
            total_evaluations=5000,
            candidates_count=10,
            elapsed_seconds=86400.0,
        )

        result = stopper(state)

        assert result is False

    def test_very_small_threshold(self) -> None:
        """Stopper handles very small threshold values."""
        stopper = ScoreThresholdStopper(float("-inf"))
        state = StopperState(
            iteration=0,
            best_score=-1000.0,
            stagnation_counter=0,
            total_evaluations=1,
            candidates_count=1,
            elapsed_seconds=1.0,
        )

        result = stopper(state)

        assert result is True

    def test_float_precision_boundary(self) -> None:
        """Stopper handles float precision at boundary."""
        stopper = ScoreThresholdStopper(0.9)
        state = StopperState(
            iteration=5,
            best_score=0.8999999999,
            stagnation_counter=0,
            total_evaluations=25,
            candidates_count=1,
            elapsed_seconds=30.0,
        )

        result = stopper(state)

        assert result is False

    def test_score_slightly_above_threshold(self) -> None:
        """Stopper handles score slightly above threshold."""
        stopper = ScoreThresholdStopper(0.9)
        state = StopperState(
            iteration=5,
            best_score=0.9000000001,
            stagnation_counter=0,
            total_evaluations=25,
            candidates_count=1,
            elapsed_seconds=30.0,
        )

        result = stopper(state)

        assert result is True
