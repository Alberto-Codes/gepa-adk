"""Score threshold stopper for evolution termination at target performance.

This module provides a ScoreThresholdStopper that terminates evolution when
the best score meets or exceeds a threshold, enabling "early success" termination
to avoid wasting compute once "good enough" performance is achieved.

Attributes:
    ScoreThresholdStopper (class): Stop evolution when best score reaches threshold.

Examples:
    Basic usage with evolution config:

    ```python
    from gepa_adk.adapters.stoppers import ScoreThresholdStopper

    stopper = ScoreThresholdStopper(0.95)  # Stop at 95% accuracy
    # Use stopper in evolution config
    ```

Note:
    This stopper is useful when you have a known target score and want to
    terminate as soon as it is reached, rather than continuing unnecessarily.

See Also:
    - [`gepa_adk.ports.stopper.StopperProtocol`][gepa_adk.ports.stopper.StopperProtocol]:
        Protocol interface for stop conditions.
    - [`gepa_adk.domain.stopper.StopperState`][gepa_adk.domain.stopper.StopperState]:
        Immutable snapshot of evolution state for stopper decisions.
"""

from __future__ import annotations

from gepa_adk.domain.stopper import StopperState


class ScoreThresholdStopper:
    """Stop evolution when best score reaches threshold.

    Terminates evolution when the best achieved score meets or exceeds the
    configured threshold. Useful for "early success" scenarios where continued
    evolution beyond a target performance is unnecessary.

    Attributes:
        threshold (float): Target score to achieve (evolution stops when
            best_score >= threshold).

    Examples:
        Creating a 95% accuracy threshold:

        ```python
        from gepa_adk.adapters.stoppers import ScoreThresholdStopper
        from gepa_adk.domain.stopper import StopperState

        stopper = ScoreThresholdStopper(0.95)

        state = StopperState(
            iteration=10,
            best_score=0.97,
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=120.0,
        )

        stopper(state)  # Returns True (should stop)
        ```

    Note:
        Any float value can be used as threshold, including negative numbers
        for domains where scores can be negative (e.g., loss minimization).
    """

    def __init__(self, threshold: float) -> None:
        """Initialize threshold stopper with target score.

        Args:
            threshold: Target score to achieve. Evolution stops when
                best_score >= threshold. Can be any float value including
                negative numbers.

        Examples:
            ```python
            stopper = ScoreThresholdStopper(0.9)  # 90% target
            stopper = ScoreThresholdStopper(-0.5)  # For negative score domains
            ```

        Note:
            Compared to timeout values, threshold has no restrictions on sign
            or magnitude since score domains vary by application.
        """
        self.threshold = threshold

    def __call__(self, state: StopperState) -> bool:
        """Check if evolution should stop due to reaching threshold.

        Args:
            state: Current evolution state snapshot containing best_score.

        Returns:
            True if best score meets or exceeds threshold, False otherwise.

        Examples:
            ```python
            stopper = ScoreThresholdStopper(0.9)

            # Below threshold
            state1 = StopperState(
                iteration=5,
                best_score=0.85,
                stagnation_counter=0,
                total_evaluations=25,
                candidates_count=1,
                elapsed_seconds=30.0,
            )
            stopper(state1)  # False

            # At threshold
            state2 = StopperState(
                iteration=10,
                best_score=0.9,
                stagnation_counter=1,
                total_evaluations=50,
                candidates_count=2,
                elapsed_seconds=65.0,
            )
            stopper(state2)  # True
            ```

        Note:
            Often called after each iteration. Returns True as soon as
            the threshold is reached.
        """
        return state.best_score >= self.threshold


__all__ = ["ScoreThresholdStopper"]
