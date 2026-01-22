"""Integration tests for stopper integration in AsyncGEPAEngine.

Tests verify that real stopper implementations work correctly with the
evolution engine, including lifecycle management for SignalStopper.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from gepa_adk.adapters.stoppers.timeout import TimeoutStopper
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.domain.stopper import StopperState
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from tests.fixtures.adapters import MockAdapter


@pytest.fixture
def mock_adapter() -> MockAdapter:
    """Provide a mock adapter for tests."""
    return MockAdapter()


class MockLifecycleStopper:
    """Mock stopper with setup() and cleanup() for lifecycle testing."""

    def __init__(self, return_value: bool = False) -> None:
        """Initialize mock lifecycle stopper.

        Args:
            return_value: Value to return when called.
        """
        self.setup_called = False
        self.cleanup_called = False
        self.return_value = return_value
        self.call_count = 0

    def setup(self) -> None:
        """Record that setup was called."""
        self.setup_called = True

    def cleanup(self) -> None:
        """Record that cleanup was called."""
        self.cleanup_called = True

    def __call__(self, state: StopperState) -> bool:
        """Evaluate stop condition and track calls."""
        self.call_count += 1
        return self.return_value


class RaisingLifecycleStopper:
    """Stopper that raises exception in cleanup for error handling test."""

    def __init__(self) -> None:
        """Initialize raising lifecycle stopper."""
        self.setup_called = False
        self.cleanup_called = False

    def setup(self) -> None:
        """Record that setup was called."""
        self.setup_called = True

    def cleanup(self) -> None:
        """Record that cleanup was called, then raise error."""
        self.cleanup_called = True
        raise RuntimeError("Cleanup error")

    def __call__(self, state: StopperState) -> bool:
        """Always return False (never stops)."""
        return False


class TestTimeoutStopper:
    """Integration tests for TimeoutStopper with AsyncGEPAEngine."""

    @pytest.mark.asyncio
    async def test_timeout_stopper_triggers_after_elapsed_time(
        self, mock_adapter: MockAdapter
    ) -> None:
        """T014: TimeoutStopper triggers after elapsed time.

        Given TimeoutStopper(0.01) in stop_callbacks (10ms)
        And a slow adapter that takes ~5ms per evaluation
        When evolution runs
        Then evolution stops when elapsed_seconds >= 0.01
        """
        import asyncio

        # Create a slow adapter that introduces delay
        original_evaluate = mock_adapter.evaluate

        async def slow_evaluate(*args, **kwargs):
            await asyncio.sleep(0.005)  # 5ms per evaluation
            return await original_evaluate(*args, **kwargs)

        mock_adapter.evaluate = slow_evaluate  # type: ignore[method-assign]

        # Use a short timeout that will trigger after a few evaluations
        timeout_stopper = TimeoutStopper(timeout_seconds=0.01)

        config = EvolutionConfig(
            max_iterations=1000,  # High limit
            patience=0,
            stop_callbacks=[timeout_stopper],
        )

        initial_candidate = Candidate(
            components={"instruction": "Be helpful"}, generation=0
        )
        batch = [{"input": "Hello", "expected": "Hi"}]

        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=initial_candidate,
            batch=batch,
        )

        start = time.monotonic()
        result = await engine.run()
        elapsed = time.monotonic() - start

        # Should stop before max_iterations due to timeout
        assert result.total_iterations < 1000

        # Elapsed time should be around or slightly above the timeout
        assert elapsed >= 0.008  # Allow slight variance


class TestSignalStopperLifecycle:
    """Integration tests for SignalStopper lifecycle management (US3)."""

    @pytest.mark.asyncio
    async def test_lifecycle_setup_called_before_loop(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """T020: SignalStopper setup() called before loop.

        Given a stopper with setup() method in stop_callbacks
        When evolution runs
        Then setup() is called before the evolution loop begins
        """
        lifecycle_stopper = MockLifecycleStopper(return_value=False)

        config = EvolutionConfig(
            max_iterations=2,
            patience=0,
            stop_callbacks=[lifecycle_stopper],
        )

        initial_candidate = Candidate(
            components={"instruction": "Be helpful"}, generation=0
        )
        batch = [{"input": "Hello", "expected": "Hi"}]

        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=initial_candidate,
            batch=batch,
        )

        await engine.run()

        # setup() should have been called
        assert lifecycle_stopper.setup_called

    @pytest.mark.asyncio
    async def test_lifecycle_cleanup_called_after_loop(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """T021: SignalStopper cleanup() called after loop.

        Given a stopper with cleanup() method in stop_callbacks
        When evolution runs and completes normally
        Then cleanup() is called after the loop completes
        """
        lifecycle_stopper = MockLifecycleStopper(return_value=False)

        config = EvolutionConfig(
            max_iterations=2,
            patience=0,
            stop_callbacks=[lifecycle_stopper],
        )

        initial_candidate = Candidate(
            components={"instruction": "Be helpful"}, generation=0
        )
        batch = [{"input": "Hello", "expected": "Hi"}]

        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=initial_candidate,
            batch=batch,
        )

        await engine.run()

        # cleanup() should have been called
        assert lifecycle_stopper.cleanup_called

    @pytest.mark.asyncio
    async def test_lifecycle_cleanup_called_on_exception(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """T022: cleanup() called even on exception.

        Given a stopper with cleanup() method in stop_callbacks
        And evolution encounters an exception during loop
        When exception is caught
        Then cleanup() was still called
        """
        lifecycle_stopper = MockLifecycleStopper(return_value=False)

        # Make the adapter raise an exception during evaluation
        mock_adapter.evaluate = MagicMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("Test exception")
        )

        config = EvolutionConfig(
            max_iterations=2,
            patience=0,
            stop_callbacks=[lifecycle_stopper],
        )

        initial_candidate = Candidate(
            components={"instruction": "Be helpful"}, generation=0
        )
        batch = [{"input": "Hello", "expected": "Hi"}]

        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=initial_candidate,
            batch=batch,
        )

        with pytest.raises(RuntimeError, match="Test exception"):
            await engine.run()

        # cleanup() should still have been called even on exception
        assert lifecycle_stopper.cleanup_called

    @pytest.mark.asyncio
    async def test_cleanup_called_in_reverse_order(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """Test cleanup is called in reverse order of setup.

        Given multiple stoppers with lifecycle methods
        When evolution runs
        Then cleanup() is called in reverse order of setup()
        """
        call_order: list[str] = []

        class TrackedStopper1:
            def setup(self) -> None:
                call_order.append("setup_1")

            def cleanup(self) -> None:
                call_order.append("cleanup_1")

            def __call__(self, state: StopperState) -> bool:
                return False

        class TrackedStopper2:
            def setup(self) -> None:
                call_order.append("setup_2")

            def cleanup(self) -> None:
                call_order.append("cleanup_2")

            def __call__(self, state: StopperState) -> bool:
                return False

        stopper1 = TrackedStopper1()
        stopper2 = TrackedStopper2()

        config = EvolutionConfig(
            max_iterations=1,
            patience=0,
            stop_callbacks=[stopper1, stopper2],
        )

        initial_candidate = Candidate(
            components={"instruction": "Be helpful"}, generation=0
        )
        batch = [{"input": "Hello", "expected": "Hi"}]

        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=initial_candidate,
            batch=batch,
        )

        await engine.run()

        # Verify setup order: 1, 2
        # Verify cleanup order: 2, 1 (reverse)
        assert call_order == ["setup_1", "setup_2", "cleanup_2", "cleanup_1"]


class TestStopperLogging:
    """Integration tests for stopper trigger logging (US4)."""

    @pytest.mark.asyncio
    async def test_first_stopper_to_trigger_is_logged(
        self, mock_adapter: MockAdapter, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T029: First stopper to trigger is logged.

        Given stop_callbacks contains multiple stoppers
        When one stopper returns True
        Then the triggering stopper's class name is logged
        """

        class NamedStopper:
            def __call__(self, state: StopperState) -> bool:
                return True

        named_stopper = NamedStopper()

        config = EvolutionConfig(
            max_iterations=100,
            patience=0,
            stop_callbacks=[named_stopper],
        )

        initial_candidate = Candidate(
            components={"instruction": "Be helpful"}, generation=0
        )
        batch = [{"input": "Hello", "expected": "Hi"}]

        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=initial_candidate,
            batch=batch,
        )

        await engine.run()

        # Check that the stopper trigger was logged (structlog outputs to stdout)
        captured = capsys.readouterr()
        assert "stopper.triggered" in captured.out
        assert "NamedStopper" in captured.out
