"""Integration tests for objective_scores passthrough end-to-end.

Note:
    Tests verify complete flow from adapter evaluation to final result,
    ensuring objective_scores are correctly passed through the engine.
    Proposals carry a module-wide sequence number so none repeats an
    already scored candidate, which the engine would skip without
    evaluating.
"""

from __future__ import annotations

import itertools
from typing import Any

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.integration

_PROPOSAL_NUMBERS = itertools.count(1)


async def _propose_distinct(
    candidate: dict[str, str], reflective_dataset: Any, components: list[str]
) -> dict[str, str]:
    """Return a proposal no earlier call returned.

    Args:
        candidate: Parent component texts.
        reflective_dataset: Unused.
        components: Components to propose updates for.

    Returns:
        Each component's parent text with a run-wide sequence number.
    """
    number = next(_PROPOSAL_NUMBERS)
    return {comp: f"Improved {number}: {candidate[comp]}" for comp in components}


class TestFullEvolutionWithObjectiveScores:
    """Integration tests for full evolution with objective_scores."""

    @pytest.mark.asyncio
    async def test_full_evolution_with_objective_scores(self) -> None:
        """Full evolution with objective_scores passes through correctly."""
        # Baseline: 2 scores (reflection + scoring)
        # 2 iterations: 2 scores each (reflection + scoring)
        # Total: 2 + (2*2) = 6 scores
        adapter = create_mock_adapter(
            custom_propose=_propose_distinct,
            scores=[0.5, 0.5, 0.6, 0.6, 0.7, 0.7],
            objective_scores={"accuracy": 0.9, "latency": 0.8},
        )
        config = EvolutionConfig(max_iterations=2)
        engine = AsyncGEPAEngine(
            adapter=adapter,
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
        adapter = create_mock_adapter(
            custom_propose=_propose_distinct,
            scores=[0.5, 0.5, 0.6, 0.6, 0.7, 0.7],
            objective_scores=None,
        )
        config = EvolutionConfig(max_iterations=2)
        engine = AsyncGEPAEngine(
            adapter=adapter,
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
        adapter = create_mock_adapter(
            custom_propose=_propose_distinct,
            scores=[0.5, 0.5, 0.55, 0.55, 0.6, 0.6, 0.65, 0.65],
            objective_scores={"accuracy": 0.95, "cost": 0.7},
        )
        config = EvolutionConfig(max_iterations=3)
        engine = AsyncGEPAEngine(
            adapter=adapter,
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
