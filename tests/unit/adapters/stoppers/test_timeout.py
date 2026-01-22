"""Unit tests for TimeoutStopper.

Tests cover all acceptance criteria from issue #192:
- Stop after timeout
- Continue before timeout
- Reject invalid timeout (0)
- Reject negative timeout
- Protocol compliance
"""

import pytest

from gepa_adk.adapters.stoppers import TimeoutStopper
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


class TestTimeoutStopperInitialization:
    """Tests for TimeoutStopper initialization and validation."""

    def test_init_with_positive_timeout_succeeds(self) -> None:
        """TimeoutStopper accepts positive timeout values."""
        stopper = TimeoutStopper(60.0)

        assert stopper.timeout_seconds == 60.0

    def test_init_with_zero_timeout_raises_value_error(self) -> None:
        """TimeoutStopper rejects zero timeout."""
        with pytest.raises(ValueError) as excinfo:
            TimeoutStopper(0)

        assert "timeout_seconds must be positive" in str(excinfo.value)

    def test_init_with_negative_timeout_raises_value_error(self) -> None:
        """TimeoutStopper rejects negative timeout."""
        with pytest.raises(ValueError) as excinfo:
            TimeoutStopper(-5)

        assert "timeout_seconds must be positive" in str(excinfo.value)

    def test_init_with_very_small_positive_timeout_succeeds(self) -> None:
        """TimeoutStopper accepts very small positive values."""
        stopper = TimeoutStopper(0.001)

        assert stopper.timeout_seconds == 0.001


class TestTimeoutStopperBehavior:
    """Tests for TimeoutStopper stopping behavior."""

    def test_returns_true_when_elapsed_exceeds_timeout(self) -> None:
        """Stopper returns True when elapsed time exceeds timeout."""
        stopper = TimeoutStopper(1.0)
        state = StopperState(
            iteration=10,
            best_score=0.8,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=2,
            elapsed_seconds=1.5,
        )

        result = stopper(state)

        assert result is True

    def test_returns_false_when_elapsed_below_timeout(self) -> None:
        """Stopper returns False when elapsed time is below timeout."""
        stopper = TimeoutStopper(60.0)
        state = StopperState(
            iteration=10,
            best_score=0.8,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=2,
            elapsed_seconds=30.0,
        )

        result = stopper(state)

        assert result is False

    def test_returns_true_when_elapsed_equals_timeout(self) -> None:
        """Stopper returns True when elapsed time exactly equals timeout."""
        stopper = TimeoutStopper(60.0)
        state = StopperState(
            iteration=10,
            best_score=0.8,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=2,
            elapsed_seconds=60.0,
        )

        result = stopper(state)

        assert result is True

    def test_returns_false_at_zero_elapsed(self, default_state: StopperState) -> None:
        """Stopper returns False when evolution just started."""
        stopper = TimeoutStopper(60.0)
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


class TestTimeoutStopperProtocolCompliance:
    """Tests verifying TimeoutStopper satisfies StopperProtocol."""

    def test_satisfies_stopper_protocol(self) -> None:
        """TimeoutStopper instance satisfies StopperProtocol."""
        stopper = TimeoutStopper(60.0)

        assert isinstance(stopper, StopperProtocol)

    def test_call_returns_bool(self, default_state: StopperState) -> None:
        """TimeoutStopper __call__ returns a boolean value."""
        stopper = TimeoutStopper(60.0)

        result = stopper(default_state)

        assert isinstance(result, bool)


class TestTimeoutStopperEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_timeout(self) -> None:
        """Stopper handles very large timeout values."""
        stopper = TimeoutStopper(float("inf"))
        state = StopperState(
            iteration=1000,
            best_score=0.99,
            stagnation_counter=0,
            total_evaluations=5000,
            candidates_count=10,
            elapsed_seconds=86400.0,  # 24 hours
        )

        result = stopper(state)

        assert result is False

    def test_float_precision_boundary(self) -> None:
        """Stopper handles float precision at boundary."""
        stopper = TimeoutStopper(1.0)
        state = StopperState(
            iteration=5,
            best_score=0.5,
            stagnation_counter=0,
            total_evaluations=25,
            candidates_count=1,
            elapsed_seconds=0.9999999999,
        )

        result = stopper(state)

        assert result is False
