"""Stopper protocol for evolution stop conditions.

This module defines the protocol interface that all stopper implementations
must follow. Stoppers are callables that receive evolution state and return
whether evolution should terminate.

Attributes:
    StopperProtocol (protocol): Protocol for stop condition objects.

Examples:
    Implementing a custom stopper:

    ```python
    from gepa_adk.ports.stopper import StopperProtocol
    from gepa_adk.domain.stopper import StopperState


    class MaxIterationsStopper:
        def __init__(self, max_iterations: int) -> None:
            self.max_iterations = max_iterations

        def __call__(self, state: StopperState) -> bool:
            return state.iteration >= self.max_iterations


    # Runtime type checking works
    stopper = MaxIterationsStopper(100)
    assert isinstance(stopper, StopperProtocol)
    ```

Note:
    This protocol is runtime_checkable, allowing isinstance() checks
    to work without explicit inheritance and follows the structural
    typing pattern used throughout gepa-adk's ports layer.
"""

from typing import Protocol, runtime_checkable

from gepa_adk.domain.stopper import StopperState


@runtime_checkable
class StopperProtocol(Protocol):
    """Protocol for stop condition objects.

    A stopper is a callable that returns True when evolution should stop.
    Stoppers receive a StopperState snapshot of current evolution progress.

    The protocol uses structural typing - any callable with the correct
    signature satisfies it, no explicit inheritance required.

    Examples:
        Class-based stopper:

        ```python
        from gepa_adk.ports.stopper import StopperProtocol
        from gepa_adk.domain.stopper import StopperState


        class TimeoutStopper:
            def __init__(self, max_seconds: float) -> None:
                self.max_seconds = max_seconds

            def __call__(self, state: StopperState) -> bool:
                return state.elapsed_seconds >= self.max_seconds


        stopper = TimeoutStopper(3600.0)  # 1 hour
        isinstance(stopper, StopperProtocol)  # True
        ```

        Function-based stopper:

        ```python
        def score_threshold_stopper(state: StopperState) -> bool:
            return state.best_score >= 0.95


        isinstance(score_threshold_stopper, StopperProtocol)  # True
        ```

    Note:
        All stoppers should be pure functions of their input state - they
        ought not have side effects or depend on external mutable state for
        deterministic behavior.
    """

    def __call__(self, state: StopperState) -> bool:
        """Check if evolution should stop.

        Args:
            state: Current evolution state snapshot containing iteration count,
                best score, stagnation counter, and other metrics.

        Returns:
            True if evolution should stop, False to continue.

        Note:
            Often this method is called after each iteration. Return True as
            soon as the stop condition is met to avoid unnecessary computation.
        """
        ...


__all__ = ["StopperProtocol"]
