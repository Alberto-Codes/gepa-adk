"""Stoppers for evolution termination conditions.

This subpackage provides concrete stopper implementations that terminate
evolution based on various conditions like timeout, iterations, score,
or external signals.

Attributes:
    CompositeStopper (class): Combine multiple stoppers with AND/OR logic.
    FileStopper (class): Stop evolution when a specified file exists.
    MaxEvaluationsStopper (class): Stop evolution after maximum evaluations.
    RegressionStopper (class): Stop evolution when score declines over N iterations.
    ScoreThresholdStopper (class): Stop evolution when best score reaches threshold.
    SignalStopper (class): Stop evolution on Unix signals (SIGINT, SIGTERM).
    TimeoutStopper (class): Stop evolution after a specified timeout.

Examples:
    Using a timeout stopper:

    ```python
    from gepa_adk.adapters.stoppers import TimeoutStopper

    stopper = TimeoutStopper(300.0)  # Stop after 5 minutes
    ```

    Using a score threshold stopper:

    ```python
    from gepa_adk.adapters.stoppers import ScoreThresholdStopper

    stopper = ScoreThresholdStopper(0.95)  # Stop at 95% accuracy
    ```

    Using a signal stopper:

    ```python
    from gepa_adk.adapters.stoppers import SignalStopper

    async with SignalStopper() as stopper:
        # Ctrl+C will gracefully stop evolution
        config = EvolutionConfig(stop_callbacks=[stopper])
        result = await engine.run(config)
    ```

    Combining multiple stoppers:

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

See Also:
    - [`gepa_adk.ports.stopper`][gepa_adk.ports.stopper]: StopperProtocol interface.
    - [`gepa_adk.domain.stopper`][gepa_adk.domain.stopper]: StopperState domain model.

Note:
    This subpackage contains adapters layer implementations. All stoppers
    implement the StopperProtocol from the ports layer.
"""

from gepa_adk.adapters.stoppers.composite import CompositeStopper
from gepa_adk.adapters.stoppers.evaluations import MaxEvaluationsStopper
from gepa_adk.adapters.stoppers.file import FileStopper
from gepa_adk.adapters.stoppers.regression import RegressionStopper
from gepa_adk.adapters.stoppers.signal import SignalStopper
from gepa_adk.adapters.stoppers.threshold import ScoreThresholdStopper
from gepa_adk.adapters.stoppers.timeout import TimeoutStopper

__all__ = [
    "CompositeStopper",
    "FileStopper",
    "MaxEvaluationsStopper",
    "RegressionStopper",
    "ScoreThresholdStopper",
    "SignalStopper",
    "TimeoutStopper",
]
