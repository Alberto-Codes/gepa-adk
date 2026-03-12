"""Unit tests for RegressionStopper.

Tests cover all acceptance criteria from Story 6.1:
- Regression detection with default window (window=3)
- Regression detection with custom window
- No regression with improving scores
- Edge case with insufficient history
- Instance reuse safety via setup()
- Composition with CompositeStopper
- Protocol compliance
"""

import pytest

from gepa_adk.adapters.stoppers import (
    CompositeStopper,
    RegressionStopper,
    ScoreThresholdStopper,
)
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.stopper import StopperState
from gepa_adk.ports.stopper import StopperProtocol

pytestmark = pytest.mark.unit


def make_state(best_score: float, iteration: int = 0) -> StopperState:
    """Create a StopperState with the given best_score for testing."""
    return StopperState(
        iteration=iteration,
        best_score=best_score,
        stagnation_counter=0,
        total_evaluations=iteration,
        candidates_count=1,
        elapsed_seconds=float(iteration),
    )


class TestRegressionStopperInitialization:
    """Tests for RegressionStopper initialization."""

    def test_init_default_window(self) -> None:
        """RegressionStopper initializes with default window=3."""
        stopper = RegressionStopper()

        assert stopper.window == 3

    def test_init_window_one(self) -> None:
        """RegressionStopper accepts window=1."""
        stopper = RegressionStopper(window=1)

        assert stopper.window == 1

    def test_init_custom_window(self) -> None:
        """RegressionStopper accepts custom window value."""
        stopper = RegressionStopper(window=5)

        assert stopper.window == 5

    def test_init_window_zero_raises_configuration_error(self) -> None:
        """RegressionStopper raises ConfigurationError for window=0."""
        with pytest.raises(ConfigurationError) as exc_info:
            RegressionStopper(window=0)

        error = exc_info.value
        assert error.field == "window"
        assert error.value == 0
        assert error.constraint == "Must be >= 1"

    def test_init_window_negative_raises_configuration_error(self) -> None:
        """RegressionStopper raises ConfigurationError for window=-1."""
        with pytest.raises(ConfigurationError) as exc_info:
            RegressionStopper(window=-1)

        error = exc_info.value
        assert error.field == "window"
        assert error.value == -1
        assert error.constraint == "Must be >= 1"

    def test_score_history_starts_empty(self) -> None:
        """RegressionStopper initializes with empty score history."""
        stopper = RegressionStopper()

        assert len(stopper._score_history) == 0


class TestRegressionStopperBehavior:
    """Tests for RegressionStopper core stopping behavior."""

    def test_insufficient_history_returns_false(self) -> None:
        """Stopper returns False when fewer than window+1 calls have been made."""
        stopper = RegressionStopper(window=3)

        # 3 calls — fewer than window+1=4 — must all return False
        assert stopper(make_state(0.5)) is False
        assert stopper(make_state(0.6)) is False
        assert stopper(make_state(0.7)) is False

    def test_exactly_at_window_plus_one_regression_detected(self) -> None:
        """Stopper returns True at exactly window+1 calls when regression present."""
        stopper = RegressionStopper(window=3)

        # 3 cold-start calls
        stopper(make_state(0.5))
        stopper(make_state(0.6))
        stopper(make_state(0.7))
        # 4th call: history=[0.5,0.6,0.7,0.4], compare 0.4 vs 0.5 → True
        result = stopper(make_state(0.4))

        assert result is True

    def test_exactly_at_window_plus_one_no_regression(self) -> None:
        """Stopper returns False at window+1 calls when no regression."""
        stopper = RegressionStopper(window=3)

        stopper(make_state(0.5))
        stopper(make_state(0.6))
        stopper(make_state(0.7))
        # 4th call: compare 0.8 vs 0.5 → no regression
        result = stopper(make_state(0.8))

        assert result is False

    def test_improving_scores_never_stops(self) -> None:
        """Stopper never returns True with consistently improving scores."""
        stopper = RegressionStopper(window=3)

        scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        results = [stopper(make_state(s)) for s in scores]

        assert all(r is False for r in results)

    def test_custom_window_five_needs_six_calls(self) -> None:
        """Stopper with window=5 requires 6 calls before any detection."""
        stopper = RegressionStopper(window=5)

        # 5 cold-start calls — all False
        for _ in range(5):
            assert stopper(make_state(0.9)) is False

        # 6th call — first chance to detect
        result = stopper(make_state(0.1))
        assert result is True  # 0.1 < 0.9 (the first value)


class TestRegressionStopperEdgeCases:
    """Tests for boundary conditions and edge cases."""

    def test_window_one_detects_single_step_regression(self) -> None:
        """window=1 detects regression after just 2 calls."""
        stopper = RegressionStopper(window=1)

        stopper(make_state(0.8))
        result = stopper(make_state(0.5))  # 0.5 < 0.8 → True

        assert result is True

    def test_window_one_no_regression_after_two_calls(self) -> None:
        """window=1 returns False on 2nd call when no regression."""
        stopper = RegressionStopper(window=1)

        stopper(make_state(0.5))
        result = stopper(make_state(0.8))  # 0.8 >= 0.5 → False

        assert result is False

    def test_plateau_scores_not_regression(self) -> None:
        """Equal scores (plateau) do NOT trigger regression (strict less-than)."""
        stopper = RegressionStopper(window=3)

        scores = [0.8, 0.8, 0.8, 0.8]
        results = [stopper(make_state(s)) for s in scores]

        assert all(r is False for r in results)

    def test_long_run_detection_uses_correct_lookback(self) -> None:
        """After many calls, detection compares last vs N-window, not first."""
        stopper = RegressionStopper(window=3)

        # Build history: 0.1,0.2,...,0.9 (9 improving scores → no regression)
        for i in range(1, 10):
            assert stopper(make_state(i / 10.0)) is False

        # Now add a score that's lower than 3 steps ago (0.9 - 3 → 0.7)
        # history[-4] = 0.7, add 0.5 → 0.5 < 0.7 → True
        result = stopper(make_state(0.5))

        assert result is True

    def test_scores_recover_then_decline(self) -> None:
        """Score recovery followed by decline triggers regression on decline."""
        stopper = RegressionStopper(window=3)

        # history will be [0.5, 0.6, 0.7, 0.4]
        stopper(make_state(0.5))
        stopper(make_state(0.6))
        stopper(make_state(0.7))
        result = stopper(make_state(0.4))  # 0.4 < 0.5 → True

        assert result is True

    def test_setup_clears_history(self) -> None:
        """setup() resets score history so stopper doesn't fire immediately after."""
        stopper = RegressionStopper(window=3)

        # Trigger regression in first run
        stopper(make_state(0.5))
        stopper(make_state(0.6))
        stopper(make_state(0.7))
        assert stopper(make_state(0.4)) is True  # triggered

        # Reset for next run
        stopper.setup()
        assert len(stopper._score_history) == 0

        # Cold start: first 3 calls must be False
        assert stopper(make_state(0.4)) is False
        assert stopper(make_state(0.3)) is False
        assert stopper(make_state(0.2)) is False


class TestRegressionStopperComposition:
    """Tests for RegressionStopper composed with CompositeStopper."""

    def test_composite_with_regression_stopper_is_protocol(self) -> None:
        """CompositeStopper containing RegressionStopper satisfies StopperProtocol."""
        composite = CompositeStopper(
            [RegressionStopper(window=3), ScoreThresholdStopper(0.99)],
            mode="any",
        )

        assert isinstance(composite, StopperProtocol)

    def test_composite_any_stops_on_regression(self) -> None:
        """CompositeStopper(mode='any') stops when RegressionStopper fires."""
        regression = RegressionStopper(window=2)
        composite = CompositeStopper(
            [regression, ScoreThresholdStopper(0.99)], mode="any"
        )

        # Cold start
        composite(make_state(0.5))
        composite(make_state(0.6))
        # Regression: 0.3 < 0.5 (window=2 → compare history[-1] vs history[-3])
        result = composite(make_state(0.3))

        assert result is True

    def test_composite_all_short_circuit_skips_regression_history(self) -> None:
        """Document: mode='all' short-circuits when first stopper returns False.

        When RegressionStopper is listed after a stopper that frequently returns
        False, all() short-circuits before calling RegressionStopper. The stateful
        stopper never accumulates history and therefore never fires.

        Mitigation: list RegressionStopper first in mode='all' compositions.
        """
        regression = RegressionStopper(window=2)
        # ScoreThresholdStopper(0.99) returns False for scores below 0.99,
        # causing all() to short-circuit before RegressionStopper is called.
        composite = CompositeStopper(
            [ScoreThresholdStopper(0.99), regression], mode="all"
        )

        for _ in range(5):
            result = composite(make_state(0.1))  # threshold not met → short-circuits
            assert result is False

        # RegressionStopper was never called — history is empty despite 5 calls
        assert len(regression._score_history) == 0

    def test_composite_propagates_setup_to_regression_stopper(self) -> None:
        """CompositeStopper.setup() resets nested RegressionStopper for multi-run safety."""
        regression = RegressionStopper(window=2)
        composite = CompositeStopper(
            [regression, ScoreThresholdStopper(0.99)], mode="any"
        )

        # Run 1: trigger regression
        composite(make_state(0.8))
        composite(make_state(0.7))
        assert composite(make_state(0.3)) is True  # regression fires

        # Reset for run 2 via composite.setup()
        composite.setup()
        assert len(regression._score_history) == 0

        # Run 2: cold start — must not fire immediately
        assert composite(make_state(0.3)) is False  # history cleared, cold start
        assert (
            composite(make_state(0.2)) is False
        )  # still cold start (window=2 needs 3 calls)
        assert (
            composite(make_state(0.1)) is True
        )  # now window+1 calls, regression detected


class TestRegressionStopperProtocolCompliance:
    """Tests verifying RegressionStopper satisfies StopperProtocol."""

    def test_satisfies_stopper_protocol(self) -> None:
        """RegressionStopper instance satisfies StopperProtocol."""
        stopper = RegressionStopper()

        assert isinstance(stopper, StopperProtocol)

    def test_call_returns_bool(self) -> None:
        """RegressionStopper __call__ returns a boolean value."""
        stopper = RegressionStopper()

        result = stopper(make_state(0.5))

        assert isinstance(result, bool)
