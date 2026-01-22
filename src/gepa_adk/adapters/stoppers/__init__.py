"""Stoppers for evolution termination conditions.

This subpackage provides concrete stopper implementations that terminate
evolution based on various conditions like timeout, iterations, or score.

Attributes:
    TimeoutStopper (class): Stop evolution after a specified timeout.

Examples:
    Using a timeout stopper:

    ```python
    from gepa_adk.adapters.stoppers import TimeoutStopper

    stopper = TimeoutStopper(300.0)  # Stop after 5 minutes
    ```

See Also:
    - [`gepa_adk.ports.stopper`][gepa_adk.ports.stopper]: StopperProtocol interface.
    - [`gepa_adk.domain.stopper`][gepa_adk.domain.stopper]: StopperState domain model.

Note:
    This subpackage contains adapters layer implementations. All stoppers
    implement the StopperProtocol from the ports layer.
"""

from gepa_adk.adapters.stoppers.timeout import TimeoutStopper

__all__ = ["TimeoutStopper"]
