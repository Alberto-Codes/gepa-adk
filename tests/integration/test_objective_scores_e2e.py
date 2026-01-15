"""Integration tests for objective_scores passthrough end-to-end.

Note:
    Tests verify complete flow from adapter evaluation to final result,
    ensuring objective_scores are correctly passed through the engine.
"""

from __future__ import annotations

from typing import Any

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch

pytestmark = pytest.mark.integration


class MockAdapterWithObjectiveScores:
    """Mock adapter that returns objective_scores for integration testing."""

    def __init__(
        self,
        scores: list[float],
        objective_scores: dict[str, float] | None = None,
    ) -> None:
        """Initialize mock adapter.

        Args:
            scores: List of scores to return sequentially.
            objective_scores: Objective scores dict to return for each example.
        """
        self._scores = iter(scores)
        self._objective_scores = objective_scores or {"accuracy": 0.9, "latency": 0.8}

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate candidate and return results with objective_scores."""
        score = next(self._scores, 0.5)
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
            objective_scores=[self._objective_scores] * len(batch),
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Build mock reflective dataset."""
        return {comp: [] for comp in components_to_update}

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: dict[str, list[dict[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Generate mock text proposals."""
        return {comp: f"Improved: {candidate[comp]}" for comp in components_to_update}


class MockAdapterWithoutObjectiveScores:
    """Mock adapter that does not return objective_scores."""

    def __init__(self, scores: list[float]) -> None:
        """Initialize mock adapter."""
        self._scores = iter(scores)

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate candidate and return results without objective_scores."""
        score = next(self._scores, 0.5)
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
            objective_scores=None,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Build mock reflective dataset."""
        return {comp: [] for comp in components_to_update}

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: dict[str, list[dict[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Generate mock text proposals."""
        return {comp: f"Improved: {candidate[comp]}" for comp in components_to_update}


class TestFullEvolutionWithObjectiveScores:
    """Integration tests for full evolution with objective_scores."""

    @pytest.mark.asyncio
    async def test_full_evolution_with_objective_scores(self) -> None:
        """Full evolution with objective_scores passes through correctly."""
        # Baseline: 2 scores (reflection + scoring)
        # 2 iterations: 2 scores each (reflection + scoring)
        # Total: 2 + (2*2) = 6 scores
        adapter = MockAdapterWithObjectiveScores(
            scores=[0.5, 0.5, 0.6, 0.6, 0.7, 0.7],
            objective_scores={"accuracy": 0.9, "latency": 0.8},
        )
        config = EvolutionConfig(max_iterations=2)
        engine = AsyncGEPAEngine(
            adapter=adapter,  # type: ignore[arg-type]
            config=config,
            initial_candidate=Candidate(components={"instruction": "Be helpful"}),
            batch=[{"input": "Hello", "expected": "Hi"}],
        )

        result = await engine.run()

        # Verify result has objective_scores
        assert result.objective_scores is not None
        assert result.objective_scores == [{"accuracy": 0.9, "latency": 0.8}]

        # Verify all iteration records have objective_scores
        assert len(result.iteration_history) == 2
        for record in result.iteration_history:
            assert record.objective_scores is not None
            assert record.objective_scores == [{"accuracy": 0.9, "latency": 0.8}]

        # Verify evolution completed successfully
        assert result.total_iterations == 2
        assert result.final_score > result.original_score

    @pytest.mark.asyncio
    async def test_full_evolution_without_objective_scores(self) -> None:
        """Full evolution without objective_scores completes successfully."""
        # Baseline: 2 scores (reflection + scoring)
        # 2 iterations: 2 scores each (reflection + scoring)
        # Total: 2 + (2*2) = 6 scores
        adapter = MockAdapterWithoutObjectiveScores(
            scores=[0.5, 0.5, 0.6, 0.6, 0.7, 0.7]
        )
        config = EvolutionConfig(max_iterations=2)
        engine = AsyncGEPAEngine(
            adapter=adapter,  # type: ignore[arg-type]
            config=config,
            initial_candidate=Candidate(components={"instruction": "Be helpful"}),
            batch=[{"input": "Hello", "expected": "Hi"}],
        )

        result = await engine.run()

        # Verify result has None objective_scores
        assert result.objective_scores is None

        # Verify all iteration records have None objective_scores
        assert len(result.iteration_history) == 2
        for record in result.iteration_history:
            assert record.objective_scores is None

        # Verify evolution completed successfully
        assert result.total_iterations == 2
        assert result.final_score > result.original_score

    @pytest.mark.asyncio
    async def test_objective_scores_persist_through_iterations(self) -> None:
        """Objective scores persist correctly through multiple iterations."""
        adapter = MockAdapterWithObjectiveScores(
            scores=[0.5, 0.5, 0.55, 0.55, 0.6, 0.6, 0.65, 0.65],
            objective_scores={"accuracy": 0.95, "cost": 0.7},
        )
        config = EvolutionConfig(max_iterations=3)
        engine = AsyncGEPAEngine(
            adapter=adapter,  # type: ignore[arg-type]
            config=config,
            initial_candidate=Candidate(components={"instruction": "Be helpful"}),
            batch=[{"input": "Hello", "expected": "Hi"}],
        )

        result = await engine.run()

        # Verify result has objective_scores from best candidate
        assert result.objective_scores == [{"accuracy": 0.95, "cost": 0.7}]

        # Verify iteration history tracks objective_scores for each iteration
        assert len(result.iteration_history) == 3
        for i, record in enumerate(result.iteration_history):
            assert record.objective_scores == [{"accuracy": 0.95, "cost": 0.7}]
            assert record.iteration_number == i + 1
