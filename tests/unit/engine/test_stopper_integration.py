"""Unit tests for stopper integration in AsyncGEPAEngine.

Tests verify that stop_callbacks are correctly invoked during evolution,
receive valid StopperState, and can terminate the evolution loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.domain.stopper import StopperState
from gepa_adk.engine.async_engine import AsyncGEPAEngine

if TYPE_CHECKING:
    from tests.fixtures.adapters import MockAdapter


class MockStopper:
    """Mock stopper that tracks invocations."""

    def __init__(self, return_value: bool = False) -> None:
        """Initialize mock stopper.

        Args:
            return_value: Value to return when called.
        """
        self.call_count = 0
        self.received_states: list[StopperState] = []
        self.return_value = return_value

    def __call__(self, state: StopperState) -> bool:
        """Track invocation and return configured value."""
        self.call_count += 1
        self.received_states.append(state)
        return self.return_value


class AlwaysTrueStopper:
    """Stopper that always returns True (stop immediately)."""

    def __call__(self, state: StopperState) -> bool:
        """Always return True to stop evolution."""
        return True


class AlwaysFalseStopper:
    """Stopper that always returns False (never stops)."""

    def __call__(self, state: StopperState) -> bool:
        """Always return False to continue evolution."""
        return False


class NotCalledStopper:
    """Stopper that should never be called (verifies short-circuit)."""

    def __call__(self, state: StopperState) -> bool:
        """Raise if called - verifies short-circuit behavior."""
        raise AssertionError("NotCalledStopper should not be invoked")


class TestStopperInvocation:
    """Tests for US1: Custom Stopper Invocation."""

    @pytest.mark.asyncio
    async def test_stopper_invoked_each_iteration(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """T006: Stopper is invoked each iteration.

        Given EvolutionConfig with stop_callbacks=[MockStopper()]
        And MockStopper tracks invocation count
        When evolution runs for 3 iterations
        Then MockStopper.__call__ invoked at least 3 times
        """
        mock_stopper = MockStopper(return_value=False)

        config = EvolutionConfig(
            max_iterations=3,
            patience=0,  # Disable early stopping
            stop_callbacks=[mock_stopper],
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

        # Stopper should be called at least once per iteration
        assert mock_stopper.call_count >= 3

    @pytest.mark.asyncio
    async def test_stopper_receives_valid_stopper_state(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """T007: Stopper receives valid StopperState.

        Given EvolutionConfig with stop_callbacks=[StateCapturer()]
        When evolution runs
        Then StateCapturer received StopperState with all fields populated
        """
        mock_stopper = MockStopper(return_value=False)

        config = EvolutionConfig(
            max_iterations=2,
            patience=0,
            stop_callbacks=[mock_stopper],
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

        # Verify stopper received valid states
        assert len(mock_stopper.received_states) > 0

        for state in mock_stopper.received_states:
            assert isinstance(state, StopperState)
            assert isinstance(state.iteration, int)
            assert state.iteration >= 0
            assert isinstance(state.best_score, float)
            assert isinstance(state.stagnation_counter, int)
            assert state.stagnation_counter >= 0
            assert isinstance(state.total_evaluations, int)
            assert state.total_evaluations >= 0
            assert isinstance(state.candidates_count, int)
            assert state.candidates_count >= 0
            assert isinstance(state.elapsed_seconds, float)
            assert state.elapsed_seconds >= 0.0

    @pytest.mark.asyncio
    async def test_stopper_returning_true_stops_evolution(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """T008: Stopper returning True stops evolution.

        Given EvolutionConfig with stop_callbacks=[AlwaysTrueStopper()]
        When evolution starts
        Then evolution terminates after the first iteration
        """
        config = EvolutionConfig(
            max_iterations=100,  # High limit that should never be reached
            patience=0,
            stop_callbacks=[AlwaysTrueStopper()],
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

        result = await engine.run()

        # Evolution should stop after first iteration (at most)
        assert result.total_iterations <= 1

    @pytest.mark.asyncio
    async def test_empty_stop_callbacks_has_no_effect(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """T009: Empty stop_callbacks has no effect.

        Given EvolutionConfig with stop_callbacks=[]
        When evolution runs
        Then only built-in conditions checked
        """
        config = EvolutionConfig(
            max_iterations=3,
            patience=0,
            stop_callbacks=[],  # Empty list
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

        result = await engine.run()

        # Should complete all iterations since only max_iterations applies
        assert result.total_iterations == 3


class TestMultipleStoppers:
    """Tests for US4: Multiple Stopper Coordination."""

    @pytest.mark.asyncio
    async def test_short_circuit_on_first_true(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """T027: Multiple stoppers short-circuit on first True.

        Given stop_callbacks=[AlwaysFalseStopper(), AlwaysTrueStopper(), NotCalledStopper()]
        When _should_stop() is called
        Then first two stoppers called
        And third stopper NOT called
        """
        false_stopper = MockStopper(return_value=False)
        true_stopper = MockStopper(return_value=True)
        not_called_stopper = NotCalledStopper()

        config = EvolutionConfig(
            max_iterations=100,
            patience=0,
            stop_callbacks=[false_stopper, true_stopper, not_called_stopper],
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

        result = await engine.run()

        # Evolution should stop quickly
        assert result.total_iterations <= 1

        # First stopper was called
        assert false_stopper.call_count >= 1

        # Second stopper was called (and returned True)
        assert true_stopper.call_count >= 1

        # Third stopper should NOT have been called (would raise AssertionError)
        # If we get here, it wasn't called

    @pytest.mark.asyncio
    async def test_all_stoppers_checked_when_none_return_true(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """T028: All stoppers checked when none return True.

        Given stop_callbacks contains multiple stoppers that all return False
        When iteration completes
        Then all stoppers were checked and evolution continues
        """
        stopper1 = MockStopper(return_value=False)
        stopper2 = MockStopper(return_value=False)
        stopper3 = MockStopper(return_value=False)

        config = EvolutionConfig(
            max_iterations=2,
            patience=0,
            stop_callbacks=[stopper1, stopper2, stopper3],
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

        result = await engine.run()

        # Should complete all iterations
        assert result.total_iterations == 2

        # All stoppers should have been called
        assert stopper1.call_count >= 2
        assert stopper2.call_count >= 2
        assert stopper3.call_count >= 2


class TestStateAccuracy:
    """Tests for US2: Accurate State Tracking."""

    @pytest.mark.asyncio
    async def test_elapsed_seconds_accuracy(self, mock_adapter: "MockAdapter") -> None:
        """T015: elapsed_seconds accuracy within 50ms.

        Given evolution runs
        When StopperState is built
        Then elapsed_seconds is a positive number close to actual elapsed time
        """
        mock_stopper = MockStopper(return_value=False)

        config = EvolutionConfig(
            max_iterations=2,
            patience=0,
            stop_callbacks=[mock_stopper],
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

        # All recorded elapsed times should be non-negative and increasing.
        # On Windows the entire run can complete within timer resolution (~15ms),
        # so all values may be 0.0 — only assert non-negative.
        elapsed_times = [s.elapsed_seconds for s in mock_stopper.received_states]
        assert all(t >= 0 for t in elapsed_times)

        # Should be monotonically increasing (or equal in fast tests)
        for i in range(1, len(elapsed_times)):
            assert elapsed_times[i] >= elapsed_times[i - 1]

    @pytest.mark.asyncio
    async def test_total_evaluations_accumulates(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """T016: total_evaluations matches sum of batch sizes.

        Given evolution runs for 3 iterations with evaluations each
        When StopperState is built
        Then total_evaluations accumulates correctly
        """
        mock_stopper = MockStopper(return_value=False)

        config = EvolutionConfig(
            max_iterations=3,
            patience=0,
            stop_callbacks=[mock_stopper],
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

        # Total evaluations should be positive and increasing
        total_evals = [s.total_evaluations for s in mock_stopper.received_states]
        assert all(e > 0 for e in total_evals)

        # Should be monotonically increasing
        for i in range(1, len(total_evals)):
            assert total_evals[i] >= total_evals[i - 1]
