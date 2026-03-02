"""Integration tests for AsyncGEPAEngine failure scenarios.

These tests validate that the engine handles mid-evolution failures gracefully
and returns partial evolved_components where appropriate.
"""

from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch

pytestmark = pytest.mark.integration


class FailingAdapter:
    """Adapter that fails after a specified number of iterations."""

    def __init__(
        self,
        fail_after: int,
        scores: list[float],
        error_message: str = "Simulated adapter failure",
    ) -> None:
        """Initialize with failure configuration.

        Args:
            fail_after: Number of successful evaluations before failing.
            scores: Scores to return for successful evaluations.
            error_message: Error message to raise on failure.
        """
        self._fail_after = fail_after
        self._scores = iter(scores)
        self._call_count = 0
        self._error_message = error_message

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate candidate, failing after configured iterations."""
        self._call_count += 1

        if self._call_count > self._fail_after:
            raise RuntimeError(self._error_message)

        score = next(self._scores, 0.5)
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
        return {comp: f"Improved: {candidate[comp]}" for comp in components_to_update}


class TestMidEvolutionFailure:
    """Test mid-evolution failure scenarios with partial evolved_components."""

    @pytest.mark.asyncio
    async def test_adapter_failure_propagates(self) -> None:
        """Test that adapter failures propagate as expected.

        When the adapter fails mid-evolution, the exception should propagate
        to the caller without catching (fail-fast behavior).
        """
        # Fail on 3rd evaluation (after baseline and first iteration)
        adapter = FailingAdapter(
            fail_after=2,
            scores=[0.5, 0.6],  # Baseline and first iteration
            error_message="Connection timeout",
        )
        config = EvolutionConfig(max_iterations=5)
        candidate = Candidate(components={"instruction": "Be helpful"}, generation=0)
        batch = [{"input": "test"}]

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        with pytest.raises(RuntimeError, match="Connection timeout"):
            await engine.run()

    @pytest.mark.asyncio
    async def test_baseline_failure_propagates(self) -> None:
        """Test that baseline evaluation failure propagates immediately.

        When the adapter fails during baseline evaluation, the exception
        should propagate without any evolution occurring.
        """
        # Fail immediately on first evaluation
        adapter = FailingAdapter(
            fail_after=0,
            scores=[],
            error_message="API rate limit exceeded",
        )
        config = EvolutionConfig(max_iterations=3)
        candidate = Candidate(components={"instruction": "Test"}, generation=0)
        batch = [{"input": "test"}]

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        with pytest.raises(RuntimeError, match="API rate limit exceeded"):
            await engine.run()

    @pytest.mark.asyncio
    async def test_completed_iterations_have_evolved_components(self) -> None:
        """Test that successfully completed iterations have valid evolved_components.

        This test verifies that when evolution completes successfully (even with
        limited iterations), the evolved_components dict is properly populated
        with all component values from the best candidate.
        """

        # Mock adapter that completes successfully
        class SuccessAdapter:
            def __init__(self) -> None:
                self._scores = iter([0.5, 0.5, 0.6, 0.6, 0.7, 0.7])

            async def evaluate(self, batch, candidate, capture_traces=False):
                score = next(self._scores, 0.5)
                return EvaluationBatch(
                    outputs=[None] * len(batch),
                    scores=[score] * len(batch),
                    trajectories=[{}] * len(batch) if capture_traces else None,
                )

            async def make_reflective_dataset(
                self, candidate, eval_batch, components_to_update
            ):
                return {comp: [] for comp in components_to_update}

            async def propose_new_texts(
                self, candidate, reflective_dataset, components_to_update
            ):
                return {
                    comp: f"Evolved: {candidate[comp]}" for comp in components_to_update
                }

        adapter = SuccessAdapter()
        config = EvolutionConfig(max_iterations=2)
        candidate = Candidate(
            components={
                "instruction": "Be helpful",
                "agent1_instruction": "Process data",
                "agent2_instruction": "Validate output",
            },
            generation=0,
        )
        batch = [{"input": "test"}]

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        result = await engine.run()

        # Verify evolved_components contains all component keys
        assert "instruction" in result.evolved_components
        assert "agent1_instruction" in result.evolved_components
        assert "agent2_instruction" in result.evolved_components

        # Verify at least one component was evolved
        assert any(
            "Evolved:" in value for value in result.evolved_components.values()
        ), "At least one component should be evolved"

    @pytest.mark.asyncio
    async def test_multi_component_evolution_tracks_all_components(self) -> None:
        """Test that multi-component evolution properly tracks all components.

        When evolving multiple components with round-robin selection,
        the final evolved_components dict should contain updates from
        all evolved iterations.
        """
        from gepa_adk.adapters.selection.component_selector import (
            RoundRobinComponentSelector,
        )

        class TrackingAdapter:
            def __init__(self) -> None:
                self._scores = iter(
                    [0.5, 0.5, 0.55, 0.55, 0.6, 0.6, 0.65, 0.65, 0.7, 0.7]
                )
                self._proposals_made: list[str] = []

            async def evaluate(self, batch, candidate, capture_traces=False):
                score = next(self._scores, 0.5)
                return EvaluationBatch(
                    outputs=[None] * len(batch),
                    scores=[score] * len(batch),
                    trajectories=[{}] * len(batch) if capture_traces else None,
                )

            async def make_reflective_dataset(
                self, candidate, eval_batch, components_to_update
            ):
                return {comp: [] for comp in components_to_update}

            async def propose_new_texts(
                self, candidate, reflective_dataset, components_to_update
            ):
                self._proposals_made.extend(components_to_update)
                return {
                    comp: f"[v{len(self._proposals_made)}] {candidate[comp]}"
                    for comp in components_to_update
                }

        adapter = TrackingAdapter()
        config = EvolutionConfig(max_iterations=4, min_improvement_threshold=0.0)
        candidate = Candidate(
            components={
                "instruction": "Primary",  # Required by engine
                "gen1_instruction": "Generator 1",
                "gen2_instruction": "Generator 2",
            },
            generation=0,
        )
        batch = [{"input": "test"}]
        component_selector = RoundRobinComponentSelector()

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
            component_selector=component_selector,
        )

        result = await engine.run()

        # Verify both agent components were evolved
        assert "gen1_instruction" in result.evolved_components
        assert "gen2_instruction" in result.evolved_components

        # Verify iteration history tracks the correct evolved components
        evolved_in_history = [r.evolved_component for r in result.iteration_history]
        assert "gen1_instruction" in evolved_in_history
        assert "gen2_instruction" in evolved_in_history
