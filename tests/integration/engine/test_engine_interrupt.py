"""Integration tests for AsyncGEPAEngine interrupt handling.

These tests validate that the engine handles KeyboardInterrupt and
asyncio.CancelledError gracefully, returning partial EvolutionResult
objects with appropriate StopReason values.

Attributes:
    InterruptingAdapter (class): Mock adapter that raises interrupts
        after a configurable number of successful evaluations.
"""

from __future__ import annotations

import asyncio
from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig, EvolutionResult
from gepa_adk.domain.types import StopReason
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch

pytestmark = pytest.mark.integration


class InterruptingAdapter:
    """Adapter that raises an interrupt after a configured number of evaluations.

    Args:
        interrupt_after: Number of successful evaluations before raising.
        interrupt_type: Exception type to raise (KeyboardInterrupt or
            asyncio.CancelledError).
    """

    def __init__(
        self,
        interrupt_after: int,
        interrupt_type: type = KeyboardInterrupt,
    ) -> None:
        """Initialize with interrupt configuration.

        Args:
            interrupt_after: Number of successful evaluations before raising.
            interrupt_type: Exception type to raise on the next evaluate call.
        """
        self._interrupt_after = interrupt_after
        self._interrupt_type = interrupt_type
        self._call_count = 0

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate candidate, raising interrupt after configured count."""
        self._call_count += 1

        if self._call_count > self._interrupt_after:
            raise self._interrupt_type()

        score = 0.5 + 0.05 * self._call_count
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build mock reflective dataset."""
        return {comp: [] for comp in components_to_update}

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Generate mock text proposals."""
        return {
            comp: f"Evolved iteration {self._call_count}"
            for comp in components_to_update
        }


class TestKeyboardInterruptPartialResult:
    """Test KeyboardInterrupt produces partial EvolutionResult."""

    @staticmethod
    async def _run_interrupted_engine(
        interrupt_after: int = 8,
    ) -> EvolutionResult:
        """Run engine that interrupts after configured eval count.

        Args:
            interrupt_after: Number of successful evaluations before raising.
                Default 8 = 2 baseline + 3*2 iteration evals (3 iterations).

        Returns:
            Partial EvolutionResult from the interrupted run.
        """
        adapter = InterruptingAdapter(interrupt_after=interrupt_after)
        config = EvolutionConfig(max_iterations=10)
        candidate = Candidate(components={"instruction": "Be helpful"}, generation=0)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=[{"input": "test"}],
        )
        return await engine.run()

    async def test_interrupt_returns_partial_result(self) -> None:
        """Interrupt after 3 successful iterations returns EvolutionResult."""
        result = await self._run_interrupted_engine()

        assert isinstance(result, EvolutionResult)
        assert result.stop_reason == StopReason.KEYBOARD_INTERRUPT
        assert len(result.iteration_history) >= 1

    async def test_interrupt_preserves_best_components(self) -> None:
        """Interrupt preserves evolved_components from best candidate."""
        result = await self._run_interrupted_engine()

        assert result.evolved_components is not None
        assert "instruction" in result.evolved_components

    async def test_interrupt_preserves_iteration_history(self) -> None:
        """Interrupt preserves valid iteration records in history."""
        result = await self._run_interrupted_engine()

        for record in result.iteration_history:
            assert record.score is not None
            assert record.evolved_component is not None

    async def test_interrupt_total_iterations_matches_history(self) -> None:
        """Interrupt total_iterations is consistent with iteration_history."""
        result = await self._run_interrupted_engine()

        assert result.total_iterations >= len(result.iteration_history)

    async def test_interrupt_serialization_round_trip(self) -> None:
        """Interrupt result serializes and deserializes correctly."""
        result = await self._run_interrupted_engine()

        d = result.to_dict()
        assert d["stop_reason"] == "keyboard_interrupt"

        restored = EvolutionResult.from_dict(d)
        assert restored.stop_reason == StopReason.KEYBOARD_INTERRUPT
        assert restored.evolved_components == result.evolved_components
        assert len(restored.iteration_history) == len(result.iteration_history)

    async def test_interrupt_scores_consistent(self) -> None:
        """Interrupt result has consistent original and final scores."""
        result = await self._run_interrupted_engine()

        assert result.original_score is not None
        assert result.final_score is not None
        assert result.final_score >= result.original_score


class TestCancelledErrorPartialResult:
    """Test asyncio.CancelledError produces partial EvolutionResult."""

    async def test_cancelled_returns_partial_result(self) -> None:
        """CancelledError after iterations returns result with CANCELLED reason."""
        adapter = InterruptingAdapter(
            interrupt_after=8,
            interrupt_type=asyncio.CancelledError,
        )
        config = EvolutionConfig(max_iterations=10)
        candidate = Candidate(components={"instruction": "Be helpful"}, generation=0)
        batch = [{"input": "test"}]

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        result = await engine.run()

        assert isinstance(result, EvolutionResult)
        assert result.stop_reason == StopReason.CANCELLED

    async def test_cancelled_serialization_round_trip(self) -> None:
        """CancelledError result serialization preserves stop_reason."""
        adapter = InterruptingAdapter(
            interrupt_after=8,
            interrupt_type=asyncio.CancelledError,
        )
        config = EvolutionConfig(max_iterations=10)
        candidate = Candidate(components={"instruction": "Be helpful"}, generation=0)
        batch = [{"input": "test"}]

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        result = await engine.run()

        d = result.to_dict()
        assert d["stop_reason"] == "cancelled"

        restored = EvolutionResult.from_dict(d)
        assert restored.stop_reason == StopReason.CANCELLED


class TestInterruptEdgeCases:
    """Test edge cases for interrupt handling."""

    async def test_interrupt_before_baseline_raises(self) -> None:
        """Interrupt before baseline completes re-raises the exception."""
        adapter = InterruptingAdapter(interrupt_after=0)
        config = EvolutionConfig(max_iterations=5)
        candidate = Candidate(components={"instruction": "Be helpful"}, generation=0)
        batch = [{"input": "test"}]

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        with pytest.raises(KeyboardInterrupt):
            await engine.run()

    async def test_interrupt_mid_iteration_excludes_incomplete(self) -> None:
        """Interrupt mid-iteration excludes the incomplete iteration record."""
        # 2 baseline evals + 2 evals for iteration 1 + 2 for iteration 2 = 6
        # Then interrupt on 7th eval (during iteration 3 train eval)
        # So we should see exactly 2 complete iteration records
        adapter = InterruptingAdapter(interrupt_after=6)
        config = EvolutionConfig(max_iterations=10)
        candidate = Candidate(components={"instruction": "Be helpful"}, generation=0)
        batch = [{"input": "test"}]

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        result = await engine.run()

        assert isinstance(result, EvolutionResult)
        assert result.stop_reason == StopReason.KEYBOARD_INTERRUPT
        # Exactly 2 complete iterations before the interrupt mid-iteration 3
        assert len(result.iteration_history) == 2
        # The incomplete iteration should not appear in history
        for record in result.iteration_history:
            assert record.score is not None

    async def test_stateless_retry_after_interrupt(self) -> None:
        """After interrupt, a new engine instance runs successfully."""
        # First run: interrupt
        adapter1 = InterruptingAdapter(interrupt_after=4)
        config = EvolutionConfig(max_iterations=5)
        candidate = Candidate(components={"instruction": "Be helpful"}, generation=0)
        batch = [{"input": "test"}]

        engine1 = AsyncGEPAEngine(
            adapter=adapter1,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        result1 = await engine1.run()
        assert result1.stop_reason == StopReason.KEYBOARD_INTERRUPT

        # Second run: complete successfully (large interrupt_after)
        adapter2 = InterruptingAdapter(interrupt_after=100)
        engine2 = AsyncGEPAEngine(
            adapter=adapter2,
            config=EvolutionConfig(max_iterations=2),
            initial_candidate=candidate,
            batch=batch,
        )

        result2 = await engine2.run()
        assert result2.stop_reason == StopReason.MAX_ITERATIONS

    async def test_stopper_cleanup_on_interrupt(self) -> None:
        """Stopper teardown runs even when interrupt occurs."""

        class TrackingStopper:
            """Stopper that tracks setup/teardown calls."""

            def __init__(self) -> None:
                """Initialize tracking state."""
                self.setup_called = False
                self.teardown_called = False

            def setup(self) -> None:
                """Record setup call."""
                self.setup_called = True

            def __call__(self, state: object) -> bool:
                """Never stop."""
                return False

            def cleanup(self) -> None:
                """Record cleanup call."""
                self.teardown_called = True

        stopper = TrackingStopper()
        adapter = InterruptingAdapter(interrupt_after=4)
        config = EvolutionConfig(max_iterations=10, stop_callbacks=[stopper])
        candidate = Candidate(components={"instruction": "Be helpful"}, generation=0)
        batch = [{"input": "test"}]

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        result = await engine.run()

        assert result.stop_reason == StopReason.KEYBOARD_INTERRUPT
        assert stopper.setup_called
        assert stopper.teardown_called


__all__ = ["InterruptingAdapter"]
