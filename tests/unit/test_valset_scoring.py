"""Unit tests for valset-aware scoring and defaults."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.adapters.candidate_selector import CurrentBestCandidateSelector
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch


class SplitScoringAdapter(AsyncGEPAAdapter[dict[str, Any], dict[str, Any], str]):
    """Adapter that scores trainset and valset differently for testing."""

    def __init__(
        self,
        trainset: list[dict[str, Any]],
        valset: list[dict[str, Any]],
        train_scores: dict[str, float],
        val_scores: dict[str, float],
        proposals: list[str],
    ) -> None:
        self._trainset = trainset
        self._valset = valset
        self._train_scores = train_scores
        self._val_scores = val_scores
        self._proposals = proposals
        self._proposal_idx = 0
        self.calls: list[dict[str, Any]] = []

    async def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[dict[str, Any], str]:
        instruction = candidate["instruction"]
        if batch is self._valset:
            score_value = self._val_scores[instruction]
        else:
            score_value = self._train_scores[instruction]
        scores = [score_value for _ in batch]
        trajectories = (
            [{"instruction": instruction} for _ in batch] if capture_traces else None
        )
        self.calls.append(
            {
                "batch": batch,
                "capture_traces": capture_traces,
                "instruction": instruction,
            }
        )
        return EvaluationBatch(
            outputs=[instruction for _ in batch],
            scores=scores,
            trajectories=trajectories,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[dict[str, Any], str],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
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
        instruction = self._proposals[self._proposal_idx % len(self._proposals)]
        self._proposal_idx += 1
        return {"instruction": instruction}


@pytest.mark.asyncio
async def test_acceptance_uses_valset_scores(
    trainset_samples: list[dict[str, str]],
    valset_samples: list[dict[str, str]],
) -> None:
    """Acceptance decisions should be based on valset scores."""
    adapter = SplitScoringAdapter(
        trainset=trainset_samples,
        valset=valset_samples,
        train_scores={"seed": 0.1, "improved": 0.1},
        val_scores={"seed": 0.2, "improved": 0.9},
        proposals=["improved"],
    )
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=1,
            patience=0,
            min_improvement_threshold=0.0,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset_samples,
        valset=valset_samples,
    )

    result = await engine.run()

    assert result.final_score == pytest.approx(0.9)
    assert result.valset_score == pytest.approx(0.9)
    assert result.trainset_score == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_valset_defaults_to_trainset(
    trainset_samples: list[dict[str, str]],
) -> None:
    """When valset is omitted, scoring should use trainset."""
    adapter = SplitScoringAdapter(
        trainset=trainset_samples,
        valset=trainset_samples,
        train_scores={"seed": 0.3, "improved": 0.6},
        val_scores={"seed": 0.3, "improved": 0.6},
        proposals=["improved"],
    )
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=1,
            patience=0,
            min_improvement_threshold=0.0,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset_samples,
    )

    await engine.run()

    scoring_calls = [call for call in adapter.calls if not call["capture_traces"]]
    assert scoring_calls
    assert all(call["batch"] is trainset_samples for call in scoring_calls)


@pytest.mark.asyncio
async def test_pareto_scores_use_valset(
    trainset_samples: list[dict[str, str]],
    valset_samples: list[dict[str, str]],
) -> None:
    """Pareto state should be populated with valset scores."""
    adapter = SplitScoringAdapter(
        trainset=trainset_samples,
        valset=valset_samples,
        train_scores={"seed": 0.1, "improved": 0.1},
        val_scores={"seed": 0.8, "improved": 0.9},
        proposals=["improved"],
    )
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=1,
            patience=0,
            min_improvement_threshold=0.0,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset_samples,
        valset=valset_samples,
        candidate_selector=CurrentBestCandidateSelector(),
    )

    await engine.run()

    pareto_state = engine._pareto_state
    assert pareto_state is not None
    scores = pareto_state.candidate_scores.get(0)
    assert scores is not None
    assert list(scores.values()) == [0.8 for _ in valset_samples]
