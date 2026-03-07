"""Timeout stopper for evolution termination after elapsed time.

This module provides a TimeoutStopper that terminates evolution after
a specified wall-clock duration, useful for fitting evolutions into
CI/CD pipelines and controlling resource usage.

Attributes:
    TimeoutStopper (class): Stop evolution after a specified timeout.

Examples:
    Basic usage with evolution config:

    ```python
    from gepa_adk.adapters.stoppers import TimeoutStopper

    stopper = TimeoutStopper(300.0)  # 5 minutes
    # Use stopper in evolution config
    ```

Note:
    This stopper is the simplest implementation and serves as a good
    template for other stoppers.

See Also:
    - [`gepa_adk.ports.stopper.StopperProtocol`][gepa_adk.ports.stopper.StopperProtocol]:
        Protocol interface for stop conditions.
    - [`gepa_adk.domain.stopper.StopperState`][gepa_adk.domain.stopper.StopperState]:
        Immutable snapshot of evolution state for stopper decisions.
"""

from __future__ import annotations

from gepa_adk.domain.stopper import StopperState


class TimeoutStopper:
    """Stop evolution after a specified timeout.

    Terminates evolution when wall-clock time exceeds the configured
    timeout duration. Useful for resource management and CI/CD pipelines.

    Attributes:
        timeout_seconds (float): Maximum wall-clock time for evolution.

    Examples:
        Creating a 5-minute timeout:

        ```python
        from gepa_adk.adapters.stoppers import TimeoutStopper
        from gepa_adk.domain.stopper import StopperState

        stopper = TimeoutStopper(300.0)  # 5 minutes

        state = StopperState(
            iteration=10,
            best_score=0.8,
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=400.0,  # Exceeds timeout
        )

        stopper(state)  # Returns True (should stop)
        ```

    Note:
        All timeout values must be positive. Zero and negative values
        raise ValueError to prevent invalid configurations.
    """

    def __init__(self, timeout_seconds: float) -> None:
        """Initialize timeout stopper with maximum duration.

        Args:
            timeout_seconds: Maximum wall-clock time for evolution in seconds.
                Must be a positive value.

        Raises:
            ValueError: If timeout_seconds is zero or negative.

        Examples:
            ```python
            stopper = TimeoutStopper(60.0)  # 1 minute
            stopper = TimeoutStopper(3600.0)  # 1 hour
            ```

        Note:
            Consider using reasonable timeouts for your use case. Very
            short timeouts may not allow sufficient evolution progress.
        """
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds

    def __call__(self, state: StopperState) -> bool:
        """Check if evolution should stop due to timeout.

        Args:
            state: Current evolution state snapshot containing elapsed_seconds.

        Returns:
            True if elapsed time meets or exceeds timeout, False otherwise.

        Examples:
            ```python
            stopper = TimeoutStopper(60.0)

            # Not yet timed out
            state1 = StopperState(
                iteration=5,
                best_score=0.5,
                stagnation_counter=0,
                total_evaluations=25,
                candidates_count=1,
                elapsed_seconds=30.0,
            )
            stopper(state1)  # False

            # Timed out
            state2 = StopperState(
                iteration=10,
                best_score=0.7,
                stagnation_counter=1,
                total_evaluations=50,
                candidates_count=2,
                elapsed_seconds=65.0,
            )
            stopper(state2)  # True
            ```

        Note:
            Often called after each iteration. Returns True as soon as
            the time limit is reached.
        """
        return state.elapsed_seconds >= self.timeout_seconds


__all__ = ["TimeoutStopper"]
