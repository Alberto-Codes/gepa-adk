"""Contract tests for StopperProtocol compliance.

Tests ensure implementations satisfy the StopperProtocol with correct
method signatures, return types, and runtime checkability.
"""

import pytest

from gepa_adk.adapters.stoppers import (
    FileStopper,
    MaxEvaluationsStopper,
    RegressionStopper,
)
from gepa_adk.domain.stopper import StopperState
from gepa_adk.ports.stopper import StopperProtocol

pytestmark = pytest.mark.contract


class MaxIterationsStopper:
    """Sample stopper that stops after a maximum number of iterations.

    Note:
        Minimal implementation for contract testing.
    """

    def __init__(self, max_iterations: int) -> None:
        """Initialize with maximum iteration count."""
        self.max_iterations = max_iterations

    def __call__(self, state: StopperState) -> bool:
        """Stop when iteration count reaches max_iterations."""
        return state.iteration >= self.max_iterations


class ScoreThresholdStopper:
    """Sample stopper that stops when best score exceeds a threshold.

    Note:
        Minimal implementation for contract testing.
    """

    def __init__(self, threshold: float) -> None:
        """Initialize with score threshold."""
        self.threshold = threshold

    def __call__(self, state: StopperState) -> bool:
        """Stop when best score meets or exceeds threshold."""
        return state.best_score >= self.threshold


def function_stopper(state: StopperState) -> bool:
    """Sample function-based stopper for protocol testing.

    Note:
        Functions with the correct signature also satisfy the protocol.
    """
    return state.stagnation_counter >= 5


class TestStopperProtocolRuntimeCheckable:
    """Tests for @runtime_checkable decorator on StopperProtocol."""

    def test_class_stopper_satisfies_protocol(self) -> None:
        """Class implementing __call__(StopperState) -> bool satisfies protocol."""
        stopper = MaxIterationsStopper(100)
        assert isinstance(stopper, StopperProtocol)

    def test_function_stopper_satisfies_protocol(self) -> None:
        """Function with correct signature satisfies protocol."""
        assert isinstance(function_stopper, StopperProtocol)

    def test_lambda_stopper_satisfies_protocol(self) -> None:
        """Lambda with correct signature satisfies protocol."""
        lambda_stopper = lambda state: state.iteration >= 10  # noqa: E731
        assert isinstance(lambda_stopper, StopperProtocol)

    def test_multiple_stopper_implementations(self) -> None:
        """Different stopper implementations all satisfy protocol."""
        stoppers = [
            MaxIterationsStopper(50),
            ScoreThresholdStopper(0.95),
            function_stopper,
            lambda state: state.elapsed_seconds >= 3600.0,
        ]

        for stopper in stoppers:
            assert isinstance(stopper, StopperProtocol)

    def test_max_evaluations_stopper_satisfies_protocol(self) -> None:
        """MaxEvaluationsStopper from adapters satisfies StopperProtocol."""
        stopper = MaxEvaluationsStopper(100)
        assert isinstance(stopper, StopperProtocol)

    def test_file_stopper_satisfies_protocol(self, tmp_path) -> None:
        """FileStopper from adapters satisfies StopperProtocol."""
        stopper = FileStopper(tmp_path / "stop_file")
        assert isinstance(stopper, StopperProtocol)

    def test_regression_stopper_satisfies_protocol(self) -> None:
        """RegressionStopper from adapters satisfies StopperProtocol."""
        stopper = RegressionStopper()
        assert isinstance(stopper, StopperProtocol)


class TestStopperProtocolBehavior:
    """Tests for StopperProtocol behavior contracts."""

    def test_stopper_returns_bool(self) -> None:
        """Stopper __call__ returns a boolean value."""
        stopper = MaxIterationsStopper(10)
        state = StopperState(
            iteration=5,
            best_score=0.5,
            stagnation_counter=0,
            total_evaluations=25,
            candidates_count=1,
            elapsed_seconds=60.0,
        )

        result = stopper(state)
        assert isinstance(result, bool)

    def test_stopper_returns_false_when_condition_not_met(self) -> None:
        """Stopper returns False when stop condition is not met."""
        stopper = MaxIterationsStopper(10)
        state = StopperState(
            iteration=5,
            best_score=0.5,
            stagnation_counter=0,
            total_evaluations=25,
            candidates_count=1,
            elapsed_seconds=60.0,
        )

        assert stopper(state) is False

    def test_stopper_returns_true_when_condition_met(self) -> None:
        """Stopper returns True when stop condition is met."""
        stopper = MaxIterationsStopper(10)
        state = StopperState(
            iteration=10,
            best_score=0.5,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=1,
            elapsed_seconds=120.0,
        )

        assert stopper(state) is True

    def test_stopper_returns_true_when_condition_exceeded(self) -> None:
        """Stopper returns True when stop condition is exceeded."""
        stopper = MaxIterationsStopper(10)
        state = StopperState(
            iteration=15,
            best_score=0.5,
            stagnation_counter=0,
            total_evaluations=75,
            candidates_count=1,
            elapsed_seconds=180.0,
        )

        assert stopper(state) is True


class TestStopperProtocolEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_stopper_with_zero_iteration(self) -> None:
        """Stopper handles state with zero iteration."""
        stopper = MaxIterationsStopper(0)
        state = StopperState(
            iteration=0,
            best_score=0.0,
            stagnation_counter=0,
            total_evaluations=0,
            candidates_count=0,
            elapsed_seconds=0.0,
        )

        # max_iterations=0 means stop immediately
        assert stopper(state) is True

    def test_score_threshold_stopper_exact_match(self) -> None:
        """Score threshold stopper handles exact threshold match."""
        stopper = ScoreThresholdStopper(0.95)
        state = StopperState(
            iteration=10,
            best_score=0.95,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=1,
            elapsed_seconds=120.0,
        )

        # Exact match should trigger stop
        assert stopper(state) is True

    def test_score_threshold_stopper_just_below(self) -> None:
        """Score threshold stopper handles score just below threshold."""
        stopper = ScoreThresholdStopper(0.95)
        state = StopperState(
            iteration=10,
            best_score=0.9499,
            stagnation_counter=0,
            total_evaluations=50,
            candidates_count=1,
            elapsed_seconds=120.0,
        )

        # Just below threshold should not trigger stop
        assert stopper(state) is False

    def test_function_stopper_behavior(self) -> None:
        """Function-based stopper works correctly."""
        state_no_stop = StopperState(
            iteration=10,
            best_score=0.5,
            stagnation_counter=3,
            total_evaluations=50,
            candidates_count=1,
            elapsed_seconds=120.0,
        )
        assert function_stopper(state_no_stop) is False

        state_stop = StopperState(
            iteration=10,
            best_score=0.5,
            stagnation_counter=5,
            total_evaluations=50,
            candidates_count=1,
            elapsed_seconds=120.0,
        )
        assert function_stopper(state_stop) is True


class TestStopperProtocolNonCompliance:
    """Tests verifying non-compliant classes don't satisfy protocol."""

    def test_class_without_call_does_not_satisfy(self) -> None:
        """Class without __call__ does not satisfy StopperProtocol."""

        class NotAStopper:
            def check(self, state: StopperState) -> bool:
                return False

        obj = NotAStopper()
        assert not isinstance(obj, StopperProtocol)

    def test_class_with_wrong_signature_documents_limitation(self) -> None:
        """Document that runtime_checkable doesn't verify signatures.

        Note:
            Runtime checkable only verifies method existence, not signature.
            This is a limitation of Python's Protocol runtime checking.
            Type checkers will catch signature mismatches at static analysis time.
        """

        class WrongSigStopper:
            def __call__(self) -> bool:
                return False

        # Runtime checkable doesn't verify signature - it only checks method exists
        # This will pass isinstance() but fail type checking
        wrong_stopper = WrongSigStopper()
        # Documenting that this IS considered satisfying by isinstance
        # even though it has the wrong signature
        assert isinstance(wrong_stopper, StopperProtocol)
