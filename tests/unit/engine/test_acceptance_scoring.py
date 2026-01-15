"""Unit tests for acceptance scoring aggregation.

Note:
    Tests sum vs mean aggregation for acceptance decisions and validation
    of empty/non-finite score handling.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.domain.exceptions import InvalidScoreListError
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch

pytestmark = pytest.mark.unit


class DeterministicScoreAdapter(AsyncGEPAAdapter[dict[str, Any], dict[str, Any], str]):
    """Adapter that returns configurable deterministic scores."""

    def __init__(
        self,
        baseline_scores: list[float],
        proposal_scores: list[float],
    ) -> None:
        """Initialize adapter with deterministic scores.

        Args:
            baseline_scores: Scores for baseline evaluation.
            proposal_scores: Scores for proposal evaluation.
        """
        self._baseline_scores = baseline_scores
        self._proposal_scores = proposal_scores
        self._call_count = 0

    async def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[dict[str, Any], str]:
        """Evaluate candidate with deterministic scores."""
        self._call_count += 1

        # Calls 1-2 are baseline (reflection + scoring)
        # Calls 3+ are proposals
        if self._call_count <= 2:
            scores = self._baseline_scores
        else:
            scores = self._proposal_scores

        # If scores list is empty and this is a scoring call (not reflection),
        # return empty list to test empty score validation
        # For reflection calls, always return valid scores to avoid division by zero
        if not scores and not capture_traces:
            batch_scores = []
        elif not scores:
            # For reflection with empty scores, use a default to avoid division by zero
            batch_scores = [0.5] * len(batch)
        else:
            batch_scores = scores[: len(batch)]
            # Repeat last score if needed
            while len(batch_scores) < len(batch):
                batch_scores.append(scores[-1])

        return EvaluationBatch(
            outputs=[candidate["instruction"] for _ in batch],
            scores=batch_scores,
            trajectories=(
                [{"instruction": candidate["instruction"]} for _ in batch]
                if capture_traces
                else None
            ),
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[dict[str, Any], str],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build minimal reflective dataset."""
        return {
            component: [{"scores": eval_batch.scores}]
            for component in components_to_update
        }

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose improved instruction."""
        return {"instruction": "improved"}


class TestSumBasedAcceptance:
    """Test sum-based acceptance aggregation (User Story 1)."""

    @pytest.mark.asyncio
    async def test_sum_aggregation_accepts_higher_sum(
        self,
        trainset_samples: list[dict[str, str]],
    ) -> None:
        """Sum-based acceptance should accept proposals with higher sum."""
        # Baseline: [0.1, 0.2, 0.3] = sum 0.6
        # Proposal: [0.2, 0.3, 0.4] = sum 0.9 (should be accepted)
        adapter = DeterministicScoreAdapter(
            baseline_scores=[0.1, 0.2, 0.3],
            proposal_scores=[0.2, 0.3, 0.4],
        )
        config = EvolutionConfig(
            max_iterations=1,
            patience=0,
            min_improvement_threshold=0.0,
            acceptance_metric="sum",
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=trainset_samples[:3],  # Use 3 examples
        )

        result = await engine.run()

        # Proposal sum (0.9) > baseline sum (0.6), so should be accepted
        assert result.final_score > result.original_score
        assert result.iteration_history[0].accepted is True

    @pytest.mark.asyncio
    async def test_sum_aggregation_rejects_lower_sum(
        self,
        trainset_samples: list[dict[str, str]],
    ) -> None:
        """Sum-based acceptance should reject proposals with lower sum."""
        # Baseline: [0.3, 0.4, 0.5] = sum 1.2
        # Proposal: [0.1, 0.2, 0.3] = sum 0.6 (should be rejected)
        adapter = DeterministicScoreAdapter(
            baseline_scores=[0.3, 0.4, 0.5],
            proposal_scores=[0.1, 0.2, 0.3],
        )
        config = EvolutionConfig(
            max_iterations=1,
            patience=0,
            min_improvement_threshold=0.0,
            acceptance_metric="sum",
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=trainset_samples[:3],
        )

        result = await engine.run()

        # Proposal sum (0.6) < baseline sum (1.2), so should be rejected
        assert result.final_score == result.original_score
        assert result.iteration_history[0].accepted is False


class TestEmptyNonFiniteScoreHandling:
    """Test handling of empty or non-finite scores."""

    @pytest.mark.asyncio
    async def test_empty_scores_raises_error(
        self,
        trainset_samples: list[dict[str, str]],
    ) -> None:
        """Empty score list should raise InvalidScoreListError."""
        adapter = DeterministicScoreAdapter(
            baseline_scores=[0.5, 0.6, 0.7],
            proposal_scores=[],  # Empty scores
        )
        config = EvolutionConfig(
            max_iterations=1,
            patience=0,
            acceptance_metric="sum",
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=trainset_samples[:3],
        )

        with pytest.raises(InvalidScoreListError) as exc_info:
            await engine.run()
        assert exc_info.value.reason == "empty"

    @pytest.mark.asyncio
    async def test_nan_scores_raises_error(
        self,
        trainset_samples: list[dict[str, str]],
    ) -> None:
        """NaN scores should raise InvalidScoreListError."""
        adapter = DeterministicScoreAdapter(
            baseline_scores=[0.5, 0.6, 0.7],
            proposal_scores=[0.5, math.nan, 0.7],
        )
        config = EvolutionConfig(
            max_iterations=1,
            patience=0,
            acceptance_metric="sum",
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=trainset_samples[:3],
        )

        with pytest.raises(InvalidScoreListError) as exc_info:
            await engine.run()
        assert exc_info.value.reason == "non-finite"

    @pytest.mark.asyncio
    async def test_inf_scores_raises_error(
        self,
        trainset_samples: list[dict[str, str]],
    ) -> None:
        """Inf scores should raise InvalidScoreListError."""
        adapter = DeterministicScoreAdapter(
            baseline_scores=[0.5, 0.6, 0.7],
            proposal_scores=[0.5, math.inf, 0.7],
        )
        config = EvolutionConfig(
            max_iterations=1,
            patience=0,
            acceptance_metric="sum",
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=trainset_samples[:3],
        )

        with pytest.raises(InvalidScoreListError) as exc_info:
            await engine.run()
        assert exc_info.value.reason == "non-finite"


class TestValsetMeanTracking:
    """Test valset mean tracking (User Story 2)."""

    @pytest.mark.asyncio
    async def test_valset_mean_tracked_separately(
        self,
        trainset_samples: list[dict[str, str]],
        valset_samples: list[dict[str, str]],
    ) -> None:
        """Valset mean should be tracked separately from acceptance score."""
        # Baseline: [0.1, 0.2, 0.3] = sum 0.6, mean 0.2
        # Proposal: [0.2, 0.3, 0.4] = sum 0.9, mean 0.3
        adapter = DeterministicScoreAdapter(
            baseline_scores=[0.1, 0.2, 0.3],
            proposal_scores=[0.2, 0.3, 0.4],
        )
        config = EvolutionConfig(
            max_iterations=1,
            patience=0,
            min_improvement_threshold=0.0,
            acceptance_metric="sum",
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=trainset_samples[:3],
            valset=valset_samples[:3],
        )

        result = await engine.run()

        # final_score should be sum-based (0.9)
        assert result.final_score == 0.9
        # valset_score should be mean-based (0.3)
        assert result.valset_score == pytest.approx(0.3)
        assert result.iteration_history[0].accepted is True


class TestMeanBasedAcceptance:
    """Test mean-based acceptance (User Story 3 - backward compatibility)."""

    @pytest.mark.asyncio
    async def test_mean_aggregation_accepts_higher_mean(
        self,
        trainset_samples: list[dict[str, str]],
    ) -> None:
        """Mean-based acceptance should accept proposals with higher mean."""
        # Baseline: [0.1, 0.2, 0.3] = mean 0.2
        # Proposal: [0.2, 0.3, 0.4] = mean 0.3 (should be accepted)
        adapter = DeterministicScoreAdapter(
            baseline_scores=[0.1, 0.2, 0.3],
            proposal_scores=[0.2, 0.3, 0.4],
        )
        config = EvolutionConfig(
            max_iterations=1,
            patience=0,
            min_improvement_threshold=0.0,
            acceptance_metric="mean",
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=trainset_samples[:3],
        )

        result = await engine.run()

        # Proposal mean (0.3) > baseline mean (0.2), so should be accepted
        assert result.final_score > result.original_score
        assert result.final_score == pytest.approx(0.3)
        assert result.iteration_history[0].accepted is True

    @pytest.mark.asyncio
    async def test_mean_aggregation_rejects_lower_mean(
        self,
        trainset_samples: list[dict[str, str]],
    ) -> None:
        """Mean-based acceptance should reject proposals with lower mean."""
        # Baseline: [0.3, 0.4, 0.5] = mean 0.4
        # Proposal: [0.1, 0.2, 0.3] = mean 0.2 (should be rejected)
        adapter = DeterministicScoreAdapter(
            baseline_scores=[0.3, 0.4, 0.5],
            proposal_scores=[0.1, 0.2, 0.3],
        )
        config = EvolutionConfig(
            max_iterations=1,
            patience=0,
            min_improvement_threshold=0.0,
            acceptance_metric="mean",
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=trainset_samples[:3],
        )

        result = await engine.run()

        # Proposal mean (0.2) < baseline mean (0.4), so should be rejected
        assert result.final_score == result.original_score
        assert result.final_score == pytest.approx(0.4)
        assert result.iteration_history[0].accepted is False
