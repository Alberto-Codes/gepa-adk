"""Regression detection stopper for evolution termination on score decline.

This module provides a RegressionStopper that terminates evolution when
the best score consistently declines over a configurable lookback window,
preventing wasted compute on degrading runs.

Attributes:
    RegressionStopper (class): Stop evolution when score declines over N iterations,
        using a bounded ``deque`` for O(1) memory regardless of run length.

Examples:
    Basic usage with default window:

    ```python
    from gepa_adk import RegressionStopper

    stopper = RegressionStopper()  # window=3
    # Use stopper in evolution config
    ```

    Custom lookback window:

    ```python
    from gepa_adk import RegressionStopper

    stopper = RegressionStopper(window=5)  # Stop if score drops vs 5 iters ago
    ```

    Composing with other stoppers:

    ```python
    from gepa_adk import RegressionStopper
    from gepa_adk.adapters.stoppers import CompositeStopper, ScoreThresholdStopper

    composite = CompositeStopper(
        [RegressionStopper(window=3), ScoreThresholdStopper(0.99)],
        mode="any",
    )
    ```

See Also:
    - [`gepa_adk.ports.stopper.StopperProtocol`][gepa_adk.ports.stopper.StopperProtocol]:
        Protocol interface for stop conditions.
    - [`gepa_adk.domain.stopper.StopperState`][gepa_adk.domain.stopper.StopperState]:
        Immutable snapshot of evolution state for stopper decisions.
"""

from __future__ import annotations

from collections import deque

import structlog

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.stopper import StopperState

logger = structlog.get_logger(__name__)


class RegressionStopper:
    """Stops evolution when best score declines over a lookback window.

    Detects regression by comparing the current best score to the best score
    from ``window`` iterations ago. Returns ``True`` (stop) when the current
    score is strictly lower than the score ``window`` steps prior.

    Requires at least ``window + 1`` calls before any regression can be detected.
    Call ``setup()`` (or let the engine call it) to reset history between runs.

    Attributes:
        window (int): Number of iterations to look back for comparison.

    Args:
        window: Number of iterations to look back for comparison. Must be >= 1.
            Default is 3.

    Examples:
        Detecting degrading runs:

        ```python
        from gepa_adk import RegressionStopper
        from gepa_adk.domain.stopper import StopperState

        stopper = RegressionStopper(window=3)

        # Simulated evolution calls (StopperState requires all 6 fields)
        stopper(
            StopperState(
                iteration=0,
                best_score=0.5,
                stagnation_counter=0,
                total_evaluations=0,
                candidates_count=1,
                elapsed_seconds=0.0,
            )
        )  # False (cold start)
        stopper(
            StopperState(
                iteration=1,
                best_score=0.6,
                stagnation_counter=0,
                total_evaluations=1,
                candidates_count=1,
                elapsed_seconds=1.0,
            )
        )  # False
        stopper(
            StopperState(
                iteration=2,
                best_score=0.7,
                stagnation_counter=0,
                total_evaluations=2,
                candidates_count=1,
                elapsed_seconds=2.0,
            )
        )  # False
        stopper(
            StopperState(
                iteration=3,
                best_score=0.4,
                stagnation_counter=0,
                total_evaluations=3,
                candidates_count=1,
                elapsed_seconds=3.0,
            )
        )  # True (0.4 < 0.5, the baseline from window=3 ago)
        ```

    Note:
        Equal scores (plateau) are NOT considered regression. Only strictly
        lower scores trigger a stop.
    """

    def __init__(self, *, window: int = 3) -> None:
        """Initialize RegressionStopper with lookback window.

        Args:
            window: Number of iterations to look back for score comparison.
                Must be >= 1. Default is 3.

        Raises:
            ConfigurationError: If window < 1.

        Examples:
            ```python
            stopper = RegressionStopper()  # window=3
            stopper = RegressionStopper(window=5)  # window=5
            ```

        Note:
            Score history is stored in a ``deque(maxlen=window+1)`` so memory
            usage is bounded to exactly ``window + 1`` floats regardless of
            run length.
        """
        if window < 1:
            raise ConfigurationError(
                f"RegressionStopper window must be >= 1, got {window}",
                field="window",
                value=window,
                constraint="Must be >= 1",
            )
        self.window = window
        self._score_history: deque[float] = deque(maxlen=self.window + 1)

    def setup(self) -> None:
        """Reset score history. Called by engine at start of each run.

        Clears the internal score history by replacing the bounded deque with
        a fresh one, so the stopper can be safely reused across multiple
        ``evolve()`` calls with the same instance. Without this reset, history
        from one run would bleed into the next.

        Examples:
            ```python
            stopper = RegressionStopper()
            # ... run evolution ...
            stopper.setup()  # reset for next run
            ```
        """
        self._score_history = deque(maxlen=self.window + 1)

    def __call__(self, state: StopperState) -> bool:
        """Check if evolution should stop due to score regression.

        Appends the current best score to history, then compares the latest
        score against the score from ``window`` iterations ago. Returns
        ``False`` during the cold-start phase (fewer than ``window + 1`` calls).

        Args:
            state: Current evolution state snapshot containing best_score.

        Returns:
            True if current best score is strictly lower than the score
            ``window`` iterations ago, False otherwise.

        Examples:
            ```python
            stopper = RegressionStopper(window=3)
            # Prime with 3 cold-start calls
            for score in [0.5, 0.6, 0.7]:
                stopper(
                    StopperState(
                        iteration=0,
                        best_score=score,
                        stagnation_counter=0,
                        total_evaluations=0,
                        candidates_count=1,
                        elapsed_seconds=0.0,
                    )
                )
            state = StopperState(
                iteration=3,
                best_score=0.4,
                stagnation_counter=0,
                total_evaluations=3,
                candidates_count=1,
                elapsed_seconds=3.0,
            )
            stopper(state)  # True (0.4 < 0.5, the baseline from window=3 ago)
            ```
        """
        self._score_history.append(state.best_score)
        if len(self._score_history) <= self.window:
            return False
        current = self._score_history[-1]
        baseline = self._score_history[-(self.window + 1)]
        if current < baseline:
            logger.info(
                "stopper.regression.triggered",
                window=self.window,
                current_score=current,
                baseline_score=baseline,
            )
            return True
        return False


__all__ = ["RegressionStopper"]
