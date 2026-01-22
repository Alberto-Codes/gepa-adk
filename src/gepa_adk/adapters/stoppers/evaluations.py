"""MaxEvaluationsStopper for stopping evolution after a set number of evaluations.

This module provides a stopper that terminates evolution when the total number
of evaluations reaches a configured limit, useful for controlling API costs.

Attributes:
    MaxEvaluationsStopper (class): Stop evolution after maximum evaluations.

Examples:
    Basic usage:

    ```python
    from gepa_adk.adapters.stoppers import MaxEvaluationsStopper

    stopper = MaxEvaluationsStopper(1000)  # Stop after 1000 evaluations
    ```

    With EvolutionConfig:

    ```python
    from gepa_adk.domain.models import EvolutionConfig
    from gepa_adk.adapters.stoppers import MaxEvaluationsStopper

    config = EvolutionConfig(
        max_iterations=100,
        stop_callbacks=[MaxEvaluationsStopper(5000)],
    )
    ```

Note:
    This stopper is particularly useful for controlling API costs when using
    expensive model evaluations. The evaluation count is cumulative across
    all iterations.
"""

from gepa_adk.domain.stopper import StopperState


class MaxEvaluationsStopper:
    """Stop evolution after maximum number of evaluations.

    Useful for controlling API costs when evaluations are expensive.
    Checks the total_evaluations field from StopperState against
    the configured limit.

    Attributes:
        max_evaluations (int): Maximum number of evaluate() calls allowed.

    Examples:
        Stop after 1000 evaluations:

        ```python
        stopper = MaxEvaluationsStopper(1000)
        ```

        Check if evolution should stop:

        ```python
        state = StopperState(total_evaluations=1000, ...)
        stopper(state)  # Returns True
        ```

    Note:
        Any evaluation count at or above the limit triggers a stop. This handles
        the case where batch evaluations cause the count to exceed the exact limit.
    """

    def __init__(self, max_evaluations: int) -> None:
        """Initialize the stopper with maximum evaluation count.

        Args:
            max_evaluations: Maximum number of evaluate() calls allowed.
                Must be a positive integer.

        Raises:
            ValueError: If max_evaluations is not positive.

        Note:
            Configure this value based on your API budget. Each evaluation
            typically corresponds to one model API call.
        """
        if max_evaluations <= 0:
            msg = "max_evaluations must be positive"
            raise ValueError(msg)
        self.max_evaluations = max_evaluations

    def __call__(self, state: StopperState) -> bool:
        """Check if evolution should stop based on evaluation count.

        Args:
            state: Current evolution state snapshot containing the
                total_evaluations count.

        Returns:
            True if total_evaluations >= max_evaluations, False otherwise.

        Note:
            Once this returns True, evolution should terminate to stay
            within the configured evaluation budget.
        """
        return state.total_evaluations >= self.max_evaluations


__all__ = ["MaxEvaluationsStopper"]
