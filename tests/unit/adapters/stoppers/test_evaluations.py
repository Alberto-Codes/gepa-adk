"""Unit tests for MaxEvaluationsStopper.

Tests cover all acceptance criteria from issue #197:
- Stop at exact evaluation limit
- Stop when limit exceeded between checks
- Continue below limit
- Reject invalid evaluations (0)
- Reject negative evaluations
- Protocol compliance
"""

import pytest

from gepa_adk.adapters.stoppers import MaxEvaluationsStopper
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
        total_evaluations=50,
        candidates_count=1,
        elapsed_seconds=30.0,
    )


class TestMaxEvaluationsStopperInitialization:
    """Tests for MaxEvaluationsStopper initialization and validation."""

    def test_init_with_positive_evaluations_succeeds(self) -> None:
        """MaxEvaluationsStopper accepts positive evaluation values."""
        stopper = MaxEvaluationsStopper(100)

        assert stopper.max_evaluations == 100

    def test_init_with_zero_evaluations_raises_value_error(self) -> None:
        """MaxEvaluationsStopper rejects zero evaluations."""
        with pytest.raises(ValueError) as excinfo:
            MaxEvaluationsStopper(0)

        assert "max_evaluations must be positive" in str(excinfo.value)

    def test_init_with_negative_evaluations_raises_value_error(self) -> None:
        """MaxEvaluationsStopper rejects negative evaluations."""
        with pytest.raises(ValueError) as excinfo:
            MaxEvaluationsStopper(-5)

        assert "max_evaluations must be positive" in str(excinfo.value)

    def test_init_with_one_evaluation_succeeds(self) -> None:
        """MaxEvaluationsStopper accepts minimum valid value of 1."""
        stopper = MaxEvaluationsStopper(1)

        assert stopper.max_evaluations == 1


class TestMaxEvaluationsStopperBehavior:
    """Tests for MaxEvaluationsStopper stopping behavior."""

    def test_stops_at_exact_limit(self) -> None:
        """Stopper returns True when evaluations exactly match limit."""
        stopper = MaxEvaluationsStopper(100)
        state = StopperState(
            iteration=10,
            best_score=0.8,
            stagnation_counter=0,
            total_evaluations=100,
            candidates_count=2,
            elapsed_seconds=60.0,
        )

        result = stopper(state)

        assert result is True

    def test_stops_above_limit(self) -> None:
        """Stopper returns True when evaluations exceed limit."""
        stopper = MaxEvaluationsStopper(100)
        state = StopperState(
            iteration=15,
            best_score=0.85,
            stagnation_counter=0,
            total_evaluations=150,
            candidates_count=3,
            elapsed_seconds=90.0,
        )

        result = stopper(state)

        assert result is True

    def test_stops_when_limit_exceeded_between_checks(self) -> None:
        """Stopper returns True when limit exceeded between iteration checks.

        This covers the edge case where batch evaluations cause the count
        to jump past the exact limit value (e.g., limit=100, but count
        goes from 95 to 105 in one batch).
        """
        stopper = MaxEvaluationsStopper(100)
        state = StopperState(
            iteration=11,
            best_score=0.82,
            stagnation_counter=0,
            total_evaluations=105,  # Exceeded between checks
            candidates_count=2,
            elapsed_seconds=65.0,
        )

        result = stopper(state)

        assert result is True

    def test_continues_below_limit(self) -> None:
        """Stopper returns False when evaluations below limit."""
        stopper = MaxEvaluationsStopper(100)
        state = StopperState(
            iteration=5,
            best_score=0.6,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=1,
            elapsed_seconds=30.0,
        )

        result = stopper(state)

        assert result is False

    def test_continues_at_zero_evaluations(self) -> None:
        """Stopper returns False when evolution just started."""
        stopper = MaxEvaluationsStopper(100)
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


class TestMaxEvaluationsStopperProtocolCompliance:
    """Tests verifying MaxEvaluationsStopper satisfies StopperProtocol."""

    def test_satisfies_stopper_protocol(self) -> None:
        """MaxEvaluationsStopper instance satisfies StopperProtocol."""
        stopper = MaxEvaluationsStopper(100)

        assert isinstance(stopper, StopperProtocol)

    def test_call_returns_bool(self, default_state: StopperState) -> None:
        """MaxEvaluationsStopper __call__ returns a boolean value."""
        stopper = MaxEvaluationsStopper(100)

        result = stopper(default_state)

        assert isinstance(result, bool)


class TestMaxEvaluationsStopperEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_limit(self) -> None:
        """Stopper handles very large evaluation limits."""
        stopper = MaxEvaluationsStopper(1_000_000)
        state = StopperState(
            iteration=100,
            best_score=0.99,
            stagnation_counter=0,
            total_evaluations=500_000,
            candidates_count=10,
            elapsed_seconds=3600.0,
        )

        result = stopper(state)

        assert result is False

    def test_limit_of_one_with_one_evaluation(self) -> None:
        """Stopper with limit=1 stops on first evaluation."""
        stopper = MaxEvaluationsStopper(1)
        state = StopperState(
            iteration=1,
            best_score=0.5,
            stagnation_counter=0,
            total_evaluations=1,
            candidates_count=1,
            elapsed_seconds=1.0,
        )

        result = stopper(state)

        assert result is True

    def test_just_below_limit(self) -> None:
        """Stopper returns False when evaluations just below limit."""
        stopper = MaxEvaluationsStopper(100)
        state = StopperState(
            iteration=9,
            best_score=0.78,
            stagnation_counter=0,
            total_evaluations=99,
            candidates_count=2,
            elapsed_seconds=58.0,
        )

        result = stopper(state)

        assert result is False
