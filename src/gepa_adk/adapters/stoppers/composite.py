"""Composite stopper for combining multiple stop conditions.

This module provides a CompositeStopper that combines multiple stoppers with
configurable AND/OR logic, enabling complex stopping rules like "stop after
5 minutes OR when score >= 0.95".

Attributes:
    CompositeStopper (class): Combine multiple stoppers with AND/OR logic.

Examples:
    Combining stoppers with OR logic (stop if any fires):

    ```python
    from gepa_adk.adapters.stoppers import (
        CompositeStopper,
        ScoreThresholdStopper,
        TimeoutStopper,
    )

    # Stop after 5 minutes OR when score >= 0.95
    composite = CompositeStopper(
        [TimeoutStopper(300), ScoreThresholdStopper(0.95)],
        mode="any",
    )
    ```

    Combining stoppers with AND logic (stop only if all fire):

    ```python
    # Stop only when BOTH conditions met
    composite = CompositeStopper(
        [TimeoutStopper(60), ScoreThresholdStopper(0.8)],
        mode="all",
    )
    ```

Note:
    This composite stopper is useful for building complex termination
    policies from simpler building blocks.

See Also:
    - [`gepa_adk.ports.stopper.StopperProtocol`][gepa_adk.ports.stopper.StopperProtocol]:
        Protocol interface for stop conditions.
    - [`gepa_adk.domain.stopper.StopperState`][gepa_adk.domain.stopper.StopperState]:
        Immutable snapshot of evolution state for stopper decisions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

    from gepa_adk.ports.stopper import StopperProtocol

from gepa_adk.domain.stopper import StopperState


class CompositeStopper:
    """Combine multiple stoppers with AND/OR logic.

    A meta-stopper that composes multiple stoppers into a single stopping
    condition with configurable logic. Use mode='any' for OR semantics
    (stop if any stopper fires) or mode='all' for AND semantics (stop
    only if all stoppers fire).

    Attributes:
        stoppers (list[StopperProtocol]): The sequence of stoppers to combine.
        mode (Literal["any", "all"]): Combination mode - 'any' for OR, 'all' for AND.

    Examples:
        Stop after 5 minutes OR when score reaches 95%:

        ```python
        from gepa_adk.adapters.stoppers import (
            CompositeStopper,
            ScoreThresholdStopper,
            TimeoutStopper,
        )
        from gepa_adk.domain.stopper import StopperState

        composite = CompositeStopper(
            [TimeoutStopper(300), ScoreThresholdStopper(0.95)],
            mode="any",
        )

        state = StopperState(
            iteration=10,
            best_score=0.97,  # Exceeds threshold
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=120.0,  # Below timeout
        )

        composite(state)  # Returns True (score threshold met)
        ```

        Stop only when minimum time AND score threshold are both met:

        ```python
        composite = CompositeStopper(
            [TimeoutStopper(60), ScoreThresholdStopper(0.8)],
            mode="all",
        )
        ```

    Note:
        A composite stopper can contain other composite stoppers for arbitrarily
        complex stopping conditions like "(A OR B) AND (C OR D)".

        Supports ``setup()`` propagation: calling ``setup()`` on a
        CompositeStopper resets all child stoppers that implement it,
        making stateful children (e.g., ``RegressionStopper``) safe
        for reuse across multiple evolution runs.
    """

    def __init__(
        self,
        stoppers: Sequence[StopperProtocol],
        mode: Literal["any", "all"] = "any",
    ) -> None:
        """Initialize composite stopper with child stoppers and mode.

        Args:
            stoppers: Sequence of stoppers to combine. Must contain at least
                one stopper. Each stopper must implement StopperProtocol.
            mode: Combination logic - 'any' (OR) or 'all' (AND). Defaults
                to 'any'.

        Raises:
            ValueError: If stoppers sequence is empty.
            ValueError: If mode is not 'any' or 'all'.

        Examples:
            ```python
            # OR logic - stop if either condition met
            composite = CompositeStopper(
                [TimeoutStopper(300), ScoreThresholdStopper(0.95)],
                mode="any",
            )

            # AND logic - stop only if both conditions met
            composite = CompositeStopper(
                [TimeoutStopper(60), ScoreThresholdStopper(0.8)],
                mode="all",
            )
            ```

        Note:
            Consider using 'any' mode for fail-safe conditions (timeout OR
            resource limit) and 'all' mode for minimum requirements.
        """
        if not stoppers:
            raise ValueError("At least one stopper required")
        if mode not in ("any", "all"):
            raise ValueError(f"mode must be 'any' or 'all', got {mode!r}")

        self.stoppers: list[StopperProtocol] = list(stoppers)
        self.mode: Literal["any", "all"] = mode

    def setup(self) -> None:
        """Propagate lifecycle resets to all child stoppers that support it.

        Called by the engine at the start of each run. Ensures stateful
        child stoppers (e.g., RegressionStopper) have their history reset
        between runs, even when nested inside a CompositeStopper.

        Note:
            Only calls setup() on children that implement the method.
            Children without setup() are unaffected.

            If a child stopper's ``setup()`` raises, the exception propagates
            out of this method. The engine will then exclude the entire
            ``CompositeStopper`` (all children) from the run, not just the
            failing child. Write defensive ``setup()`` implementations in
            custom stoppers to avoid disabling the whole composite.
        """
        for stopper in self.stoppers:
            setup_method = getattr(stopper, "setup", None)
            if setup_method is not None and callable(setup_method):
                setup_method()

    def __call__(self, state: StopperState) -> bool:
        """Check if evolution should stop based on combined stopper logic.

        Args:
            state: Current evolution state snapshot passed to all child stoppers.

        Returns:
            For mode='any': True if any child stopper returns True.
            For mode='all': True only if all child stoppers return True.

        Examples:
            ```python
            composite = CompositeStopper(
                [TimeoutStopper(60), ScoreThresholdStopper(0.9)],
                mode="any",
            )

            # Below both thresholds
            state1 = StopperState(
                iteration=5,
                best_score=0.5,
                stagnation_counter=0,
                total_evaluations=25,
                candidates_count=1,
                elapsed_seconds=30.0,
            )
            composite(state1)  # False

            # Score threshold met
            state2 = StopperState(
                iteration=10,
                best_score=0.95,
                stagnation_counter=1,
                total_evaluations=50,
                candidates_count=2,
                elapsed_seconds=45.0,
            )
            composite(state2)  # True (any mode - score threshold met)
            ```

        Note:
            Often called after each iteration. For 'any' mode, evaluation
            short-circuits on first True. For 'all' mode, short-circuits on
            first False.

            **Stateful stopper ordering caveat:** Short-circuit evaluation means
            stoppers listed later in the sequence may not be called on every
            iteration. Stateful stoppers (e.g., ``RegressionStopper``) that
            require being called every iteration to accumulate history must be
            listed **first** in ``mode='all'`` compositions, or placed before
            any stopper that frequently returns ``False``. Otherwise the
            stateful stopper will never accumulate history and can never fire.
        """
        if self.mode == "any":
            return any(stopper(state) for stopper in self.stoppers)
        # mode == "all"
        return all(stopper(state) for stopper in self.stoppers)

    def __repr__(self) -> str:
        """Return string representation of the composite stopper.

        Returns:
            String showing the stoppers list and mode.

        Examples:
            ```python
            composite = CompositeStopper(
                [TimeoutStopper(60), ScoreThresholdStopper(0.9)],
                mode="any",
            )
            repr(composite)
            # "CompositeStopper([TimeoutStopper(...), ScoreThresholdStopper(...)], mode='any')"
            ```
        """
        return f"CompositeStopper({self.stoppers!r}, mode={self.mode!r})"


__all__ = ["CompositeStopper"]
