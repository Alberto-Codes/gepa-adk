"""Signal stopper for graceful evolution termination on Unix signals.

This module provides a SignalStopper that handles Unix signals (SIGINT, SIGTERM)
for graceful shutdown of evolution runs. Supports both async and sync contexts
with proper signal handler management.

Attributes:
    SignalStopper (class): Stop evolution on Unix signals (SIGINT, SIGTERM).

Examples:
    Using as a context manager (recommended):

    ```python
    from gepa_adk.adapters.stoppers import SignalStopper

    async with SignalStopper() as stopper:
        config = EvolutionConfig(stop_callbacks=[stopper])
        result = await engine.run(config)
        # Ctrl+C will gracefully stop evolution
    ```

    Manual setup and cleanup:

    ```python
    stopper = SignalStopper()
    stopper.setup()
    try:
        # Run evolution
        pass
    finally:
        stopper.cleanup()
    ```

Note:
    This stopper requires careful integration with asyncio's event loop
    for proper signal handling in async contexts.
"""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Callable
from types import FrameType
from typing import TYPE_CHECKING, Any

from gepa_adk.domain.stopper import StopperState

if TYPE_CHECKING:
    from collections.abc import Sequence

# Type alias for signal handlers: can be SIG_DFL, SIG_IGN, or a callable
_SignalHandler = Callable[[int, FrameType | None], Any] | int | None


class SignalStopper:
    """Stop evolution on Unix signals (SIGINT, SIGTERM).

    Handles Ctrl+C (SIGINT) and termination signals gracefully, allowing the
    current iteration to complete before returning results. Supports both
    async contexts (using asyncio signal handling) and sync contexts (using
    traditional signal handlers).

    Attributes:
        signals (tuple[signal.Signals, ...]): Signals to handle.

    Examples:
        Using as async context manager:

        ```python
        from gepa_adk.adapters.stoppers import SignalStopper

        async with SignalStopper() as stopper:
            # stopper.setup() called automatically
            config = EvolutionConfig(stop_callbacks=[stopper])
            result = await engine.run(config)
            # stopper.cleanup() called automatically
        ```

        Using with custom signals:

        ```python
        import signal

        stopper = SignalStopper(signals=[signal.SIGINT])
        stopper.setup()
        try:
            # Only SIGINT will trigger stop
            pass
        finally:
            stopper.cleanup()
        ```

    Note:
        Always call cleanup() after evolution completes to restore original
        signal handlers. The context manager pattern handles this automatically.
    """

    def __init__(self, signals: Sequence[signal.Signals] | None = None) -> None:
        """Initialize signal stopper with signals to handle.

        Args:
            signals: Signals to handle. Defaults to [SIGINT, SIGTERM] which
                covers Ctrl+C and system termination requests.

        Examples:
            ```python
            # Default signals (SIGINT, SIGTERM)
            stopper = SignalStopper()

            # Custom signals
            stopper = SignalStopper(signals=[signal.SIGINT])
            ```

        Note:
            Call setup() before evolution starts and cleanup() after
            evolution completes to properly manage signal handlers.
        """
        if signals is None:
            self.signals: tuple[signal.Signals, ...] = (
                signal.SIGINT,
                signal.SIGTERM,
            )
        else:
            self.signals = tuple(signals)
        self._stop_requested: bool = False
        self._original_handlers: dict[signal.Signals, _SignalHandler] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def setup(self) -> None:
        """Install signal handlers.

        Must be called before evolution starts. In async contexts, uses
        asyncio's signal handling. In sync contexts, uses traditional
        signal handlers.

        Examples:
            ```python
            stopper = SignalStopper()
            stopper.setup()
            try:
                # Run evolution
                pass
            finally:
                stopper.cleanup()
            ```

        Note:
            On platforms where certain signals are unavailable (like Windows
            for SIGTERM), those signals are silently skipped.
        """
        try:
            self._loop = asyncio.get_running_loop()
            for sig in self.signals:
                try:
                    self._loop.add_signal_handler(sig, self._handle_signal)
                except (OSError, ValueError, NotImplementedError):
                    pass  # Signal not available on platform
        except RuntimeError:
            # Not in async context, use traditional signal handling
            for sig in self.signals:
                try:
                    self._original_handlers[sig] = signal.signal(
                        sig, self._sync_handler
                    )
                except (OSError, ValueError):
                    pass  # Signal not available on platform

    def _handle_signal(self) -> None:
        """Handle signal in async context."""
        self._stop_requested = True

    def _sync_handler(
        self,
        signum: int,
        frame: FrameType | None,  # noqa: ARG002
    ) -> None:
        """Handle signal in sync context."""
        self._stop_requested = True

    def __call__(self, state: StopperState) -> bool:  # noqa: ARG002
        """Check if evolution should stop due to signal.

        Args:
            state: Current evolution state snapshot (not used, but required
                by StopperProtocol).

        Returns:
            True if a signal was received, False otherwise.

        Examples:
            ```python
            stopper = SignalStopper()
            stopper.setup()

            state = StopperState(
                iteration=5,
                best_score=0.8,
                stagnation_counter=0,
                total_evaluations=25,
                candidates_count=1,
                elapsed_seconds=30.0,
            )

            # Before signal
            stopper(state)  # False

            # After Ctrl+C
            # stopper(state)  # True
            ```

        Note:
            Often called after each iteration. Returns True as soon as
            a signal is received.
        """
        return self._stop_requested

    def cleanup(self) -> None:
        """Restore original signal handlers.

        Should be called after evolution completes to restore the signal
        handlers that were in place before setup() was called.

        Examples:
            ```python
            stopper = SignalStopper()
            stopper.setup()
            try:
                # Run evolution
                pass
            finally:
                stopper.cleanup()  # Restore original handlers
            ```

        Note:
            On platforms where certain signals are unavailable, those
            signals are silently skipped during cleanup.
        """
        if self._loop is not None:
            for sig in self.signals:
                try:
                    self._loop.remove_signal_handler(sig)
                except (OSError, ValueError, NotImplementedError):
                    pass
        else:
            for sig, handler in self._original_handlers.items():
                try:
                    signal.signal(sig, handler)
                except (OSError, ValueError):
                    pass
        self._original_handlers.clear()
        self._loop = None

    async def __aenter__(self) -> SignalStopper:
        """Enter async context and install signal handlers.

        Returns:
            Self for use as stopper in evolution config.

        Examples:
            ```python
            async with SignalStopper() as stopper:
                config = EvolutionConfig(stop_callbacks=[stopper])
                result = await engine.run(config)
            ```

        Note:
            Signal handlers are installed automatically on entry.
        """
        self.setup()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context and restore signal handlers.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception value if an exception was raised.
            exc_tb: Exception traceback if an exception was raised.

        Note:
            Signal handlers are restored automatically on exit,
            even if an exception was raised.
        """
        self.cleanup()

    def __enter__(self) -> SignalStopper:
        """Enter sync context and install signal handlers.

        Returns:
            Self for use as stopper in evolution config.

        Examples:
            ```python
            with SignalStopper() as stopper:
                config = EvolutionConfig(stop_callbacks=[stopper])
                result = engine.run(config)  # sync run
            ```

        Note:
            Signal handlers are installed automatically on entry.
        """
        self.setup()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit sync context and restore signal handlers.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception value if an exception was raised.
            exc_tb: Exception traceback if an exception was raised.

        Note:
            Signal handlers are restored automatically on exit,
            even if an exception was raised.
        """
        self.cleanup()


__all__ = ["SignalStopper"]
