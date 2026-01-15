"""Contract tests for acceptance scoring configuration and behavior.

Note:
    Tests acceptance_metric configuration validation and aggregation behavior.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch

pytestmark = pytest.mark.contract


class AcceptanceScoringAdapter(AsyncGEPAAdapter[dict[str, Any], dict[str, Any], str]):
    """Adapter that returns deterministic scores for acceptance testing.

    Note:
        Provides predictable scores to verify acceptance aggregation behavior.
    """

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
        """Evaluate candidates with deterministic scores.

        Note:
            Returns baseline scores for first two calls (reflection + scoring),
            then proposal scores for subsequent calls.
        """
        self._call_count += 1

        # First two calls are baseline (reflection + scoring)
        # Subsequent calls are proposals
        if self._call_count <= 2:
            scores = self._baseline_scores
        else:
            scores = self._proposal_scores

        # Use only as many scores as batch size, repeat last if needed
        batch_scores = scores[: len(batch)]
        while len(batch_scores) < len(batch):
            batch_scores.append(scores[-1] if scores else 0.5)

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
        """Build minimal reflective datasets for components.

        Note:
            Outputs compact reflection data for contract validation.
        """
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
        """Propose a deterministic instruction update for tests.

        Note:
            Outputs a consistent proposal to drive acceptance flow.
        """
        return {"instruction": "improved"}


class TestAcceptanceScoringContract:
    """Contract tests for acceptance scoring configuration."""

    def test_acceptance_metric_defaults_to_sum(self) -> None:
        """acceptance_metric should default to 'sum'."""
        config = EvolutionConfig()
        assert config.acceptance_metric == "sum"

    def test_acceptance_metric_accepts_sum(self) -> None:
        """acceptance_metric should accept 'sum' value."""
        config = EvolutionConfig(acceptance_metric="sum")
        assert config.acceptance_metric == "sum"

    def test_acceptance_metric_accepts_mean(self) -> None:
        """acceptance_metric should accept 'mean' value."""
        config = EvolutionConfig(acceptance_metric="mean")
        assert config.acceptance_metric == "mean"

    def test_acceptance_metric_rejects_invalid_value(self) -> None:
        """acceptance_metric should reject invalid values."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(acceptance_metric="invalid")  # type: ignore[arg-type]
        assert exc_info.value.field == "acceptance_metric"
        assert exc_info.value.constraint == "sum|mean"

    @pytest.mark.asyncio
    async def test_acceptance_metric_sum_aggregates_scores(
        self,
        trainset_samples: list[dict[str, str]],
    ) -> None:
        """acceptance_metric='sum' should use sum aggregation for acceptance."""
        # Baseline: [0.1, 0.2, 0.3] = sum 0.6
        # Proposal: [0.2, 0.3, 0.4] = sum 0.9
        adapter = AcceptanceScoringAdapter(
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
        )

        result = await engine.run()

        # With sum aggregation, proposal (sum=0.9) > baseline (sum=0.6) should be accepted
        assert result.iteration_history[0].accepted is True
