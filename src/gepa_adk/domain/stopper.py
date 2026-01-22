"""Stopper state model for evolution stop condition decisions.

This module defines the immutable state snapshot passed to stoppers
when checking if evolution should terminate.

Attributes:
    StopperState (class): Immutable snapshot of evolution state for stopper decisions.

Examples:
    Creating a stopper state:

    ```python
    from gepa_adk.domain.stopper import StopperState

    state = StopperState(
        iteration=5,
        best_score=0.85,
        stagnation_counter=2,
        total_evaluations=50,
        candidates_count=3,
        elapsed_seconds=120.5,
    )
    ```

Note:
    StopperState is intentionally minimal. Add fields as needed for specific
    stopper implementations. The frozen dataclass ensures stoppers cannot
    accidentally mutate evolution state.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StopperState:
    """Immutable snapshot of evolution state for stopper decisions.

    Provides stoppers with read-only access to evolution metrics
    without exposing internal engine state.

    Attributes:
        iteration (int): Current iteration number (0-indexed).
        best_score (float): Best score achieved so far.
        stagnation_counter (int): Number of iterations without improvement.
        total_evaluations (int): Count of all evaluate() calls made.
        candidates_count (int): Number of candidates in the frontier.
        elapsed_seconds (float): Wall-clock time since evolution started.

    Examples:
        Creating a state snapshot:

        ```python
        from gepa_adk.domain.stopper import StopperState

        state = StopperState(
            iteration=10,
            best_score=0.92,
            stagnation_counter=3,
            total_evaluations=100,
            candidates_count=5,
            elapsed_seconds=300.0,
        )
        print(state.best_score)  # 0.92
        print(state.stagnation_counter)  # 3
        ```

        Attempting to modify raises an error:

        ```python
        state.iteration = 11  # Raises FrozenInstanceError
        ```

    Note:
        This is a frozen dataclass - all fields are immutable after creation.
        Using slots=True for memory efficiency.
    """

    iteration: int
    best_score: float
    stagnation_counter: int
    total_evaluations: int
    candidates_count: int
    elapsed_seconds: float


__all__ = ["StopperState"]
