"""Unit tests for SignalStopper.

Tests cover all acceptance criteria from issue #194:
- Stop on SIGINT
- Continue without signal
- Cleanup restores handlers
- Works in async context
- Works in sync context
- Protocol compliance
"""

import asyncio
import signal

import pytest
from pytest_mock import MockerFixture

from gepa_adk.adapters.stoppers import SignalStopper
from gepa_adk.domain.stopper import StopperState
from gepa_adk.ports.stopper import StopperProtocol

pytestmark = pytest.mark.unit


@pytest.fixture
def default_state() -> StopperState:
    """Create a default stopper state for testing."""
    return StopperState(
        iteration=5,
        best_score=0.5,
        stagnation_counter=0,
        total_evaluations=25,
        candidates_count=1,
        elapsed_seconds=30.0,
    )


class TestSignalStopperInitialization:
    """Tests for SignalStopper initialization."""

    def test_init_with_default_signals(self) -> None:
        """SignalStopper defaults to SIGINT and SIGTERM."""
        stopper = SignalStopper()

        assert signal.SIGINT in stopper.signals
        assert signal.SIGTERM in stopper.signals

    def test_init_with_custom_signals(self) -> None:
        """SignalStopper accepts custom signal list."""
        stopper = SignalStopper(signals=[signal.SIGINT])

        assert stopper.signals == (signal.SIGINT,)
        assert signal.SIGTERM not in stopper.signals

    def test_init_with_empty_signals(self) -> None:
        """SignalStopper accepts empty signal list."""
        stopper = SignalStopper(signals=[])

        assert stopper.signals == ()

    def test_init_stop_requested_is_false(self) -> None:
        """SignalStopper starts with stop_requested as False."""
        stopper = SignalStopper()

        assert stopper._stop_requested is False


class TestSignalStopperBehavior:
    """Tests for SignalStopper stopping behavior."""

    def test_returns_false_without_signal(self, default_state: StopperState) -> None:
        """Stopper returns False when no signal received."""
        stopper = SignalStopper()

        result = stopper(default_state)

        assert result is False

    def test_returns_true_after_signal_request(
        self, default_state: StopperState
    ) -> None:
        """Stopper returns True after stop is requested internally."""
        stopper = SignalStopper()
        stopper._stop_requested = True

        result = stopper(default_state)

        assert result is True

    def test_handle_signal_sets_stop_requested(self) -> None:
        """Internal signal handler sets stop_requested to True."""
        stopper = SignalStopper()

        stopper._handle_signal()

        assert stopper._stop_requested is True

    def test_sync_handler_sets_stop_requested(self) -> None:
        """Sync signal handler sets stop_requested to True."""
        stopper = SignalStopper()

        stopper._sync_handler(signal.SIGINT, None)

        assert stopper._stop_requested is True


class TestSignalStopperSetupCleanup:
    """Tests for SignalStopper setup and cleanup."""

    def test_setup_in_sync_context_stores_original_handlers(
        self, mocker: MockerFixture
    ) -> None:
        """Setup stores original signal handlers in sync context."""
        original_handler = mocker.Mock()
        mocker.patch("signal.signal", return_value=original_handler)

        stopper = SignalStopper(signals=[signal.SIGINT])
        stopper.setup()

        assert signal.SIGINT in stopper._original_handlers

    def test_cleanup_restores_original_handlers(self, mocker: MockerFixture) -> None:
        """Cleanup restores original signal handlers."""
        original_handler = mocker.Mock()
        mock_signal = mocker.patch("signal.signal", return_value=original_handler)

        stopper = SignalStopper(signals=[signal.SIGINT])
        stopper.setup()
        stopper.cleanup()

        # Verify signal.signal was called to restore
        assert mock_signal.call_count >= 2  # setup + cleanup
        assert stopper._original_handlers == {}

    def test_cleanup_clears_loop_reference(self) -> None:
        """Cleanup clears the event loop reference."""
        stopper = SignalStopper()
        loop = asyncio.new_event_loop()
        stopper._loop = loop

        try:
            stopper.cleanup()
        finally:
            loop.close()

        assert stopper._loop is None

    def test_setup_handles_unsupported_signals(self, mocker: MockerFixture) -> None:
        """Setup silently ignores unsupported signals."""
        mocker.patch("signal.signal", side_effect=OSError("Unsupported"))

        stopper = SignalStopper(signals=[signal.SIGINT])
        # Should not raise
        stopper.setup()

        assert stopper._original_handlers == {}


class TestSignalStopperAsyncContext:
    """Tests for SignalStopper async context manager."""

    @pytest.mark.asyncio
    async def test_async_context_manager_setup_called(
        self, mocker: MockerFixture
    ) -> None:
        """Async context manager calls setup on entry."""
        mock_setup = mocker.patch.object(SignalStopper, "setup")

        async with SignalStopper():
            mock_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup_called(
        self, mocker: MockerFixture
    ) -> None:
        """Async context manager calls cleanup on exit."""
        mock_cleanup = mocker.patch.object(SignalStopper, "cleanup")

        async with SignalStopper():
            pass

        mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup_on_exception(
        self, mocker: MockerFixture
    ) -> None:
        """Async context manager calls cleanup even on exception."""
        mock_cleanup = mocker.patch.object(SignalStopper, "cleanup")

        with pytest.raises(ValueError):
            async with SignalStopper():
                raise ValueError("Test error")

        mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager_returns_self(self) -> None:
        """Async context manager returns stopper instance."""
        stopper = SignalStopper()

        async with stopper as s:
            assert s is stopper


class TestSignalStopperSyncContext:
    """Tests for SignalStopper sync context manager."""

    def test_sync_context_manager_setup_called(self, mocker: MockerFixture) -> None:
        """Sync context manager calls setup on entry."""
        mock_setup = mocker.patch.object(SignalStopper, "setup")

        with SignalStopper():
            mock_setup.assert_called_once()

    def test_sync_context_manager_cleanup_called(self, mocker: MockerFixture) -> None:
        """Sync context manager calls cleanup on exit."""
        mock_cleanup = mocker.patch.object(SignalStopper, "cleanup")

        with SignalStopper():
            pass

        mock_cleanup.assert_called_once()

    def test_sync_context_manager_cleanup_on_exception(
        self, mocker: MockerFixture
    ) -> None:
        """Sync context manager calls cleanup even on exception."""
        mock_cleanup = mocker.patch.object(SignalStopper, "cleanup")

        with pytest.raises(ValueError), SignalStopper():
            raise ValueError("Test error")

        mock_cleanup.assert_called_once()

    def test_sync_context_manager_returns_self(self) -> None:
        """Sync context manager returns stopper instance."""
        stopper = SignalStopper()

        with stopper as s:
            assert s is stopper


class TestSignalStopperProtocolCompliance:
    """Tests verifying SignalStopper satisfies StopperProtocol."""

    def test_satisfies_stopper_protocol(self) -> None:
        """SignalStopper instance satisfies StopperProtocol."""
        stopper = SignalStopper()

        assert isinstance(stopper, StopperProtocol)

    def test_call_returns_bool(self, default_state: StopperState) -> None:
        """SignalStopper __call__ returns a boolean value."""
        stopper = SignalStopper()

        result = stopper(default_state)

        assert isinstance(result, bool)


class TestSignalStopperSignalHandling:
    """Tests for actual signal handling integration."""

    def test_setup_in_sync_registers_handler(self, mocker: MockerFixture) -> None:
        """Setup registers signal handler in sync context."""
        mock_signal = mocker.patch("signal.signal")

        stopper = SignalStopper(signals=[signal.SIGINT])
        stopper.setup()

        # Verify signal was called with SIGINT and our handler
        mock_signal.assert_called()
        call_args = mock_signal.call_args_list
        assert any(call[0][0] == signal.SIGINT for call in call_args)

    @pytest.mark.asyncio
    async def test_setup_in_async_uses_loop_handler(
        self, mocker: MockerFixture
    ) -> None:
        """Setup uses asyncio signal handling in async context."""
        loop = asyncio.get_running_loop()
        mock_add_handler = mocker.patch.object(loop, "add_signal_handler")

        stopper = SignalStopper(signals=[signal.SIGINT])
        stopper.setup()

        mock_add_handler.assert_called()

    @pytest.mark.asyncio
    async def test_cleanup_in_async_removes_handler(
        self, mocker: MockerFixture
    ) -> None:
        """Cleanup removes asyncio signal handler."""
        loop = asyncio.get_running_loop()
        mocker.patch.object(loop, "add_signal_handler")
        mock_remove_handler = mocker.patch.object(loop, "remove_signal_handler")

        stopper = SignalStopper(signals=[signal.SIGINT])
        stopper.setup()
        stopper.cleanup()

        mock_remove_handler.assert_called()


class TestSignalStopperEdgeCases:
    """Tests for edge cases and platform considerations."""

    def test_multiple_signals_all_registered(self, mocker: MockerFixture) -> None:
        """All provided signals are registered."""
        mock_signal = mocker.patch("signal.signal")

        stopper = SignalStopper(signals=[signal.SIGINT, signal.SIGTERM])
        stopper.setup()

        registered_signals = [call[0][0] for call in mock_signal.call_args_list]
        assert signal.SIGINT in registered_signals
        assert signal.SIGTERM in registered_signals

    def test_state_is_not_used(self) -> None:
        """Stopper ignores state contents and only checks signal flag."""
        stopper = SignalStopper()

        # Different states should all return False without signal
        states = [
            StopperState(0, 0.0, 0, 0, 0, 0.0),
            StopperState(100, 0.99, 50, 1000, 10, 3600.0),
            StopperState(1, -1.0, 1, 1, 1, 1.0),
        ]

        for state in states:
            assert stopper(state) is False

        # After signal, all states should return True
        stopper._stop_requested = True
        for state in states:
            assert stopper(state) is True

    def test_cleanup_idempotent(self, mocker: MockerFixture) -> None:
        """Cleanup can be called multiple times safely."""
        mocker.patch("signal.signal")
        stopper = SignalStopper()
        stopper.setup()

        # Multiple cleanups should not raise
        stopper.cleanup()
        stopper.cleanup()
        stopper.cleanup()

        assert stopper._original_handlers == {}
        assert stopper._loop is None
