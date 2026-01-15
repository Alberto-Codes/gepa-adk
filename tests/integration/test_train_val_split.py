"""Integration test for train/val split in AsyncGEPAEngine.

Note:
    Tests end-to-end dataset separation across reflection and scoring.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch

pytestmark = pytest.mark.integration


class SplitAdapter(AsyncGEPAAdapter[dict[str, Any], dict[str, Any], str]):
    """Adapter that returns distinct scores for trainset vs valset.

    Note:
        Aids integration validation of scoring dataset selection.
    """

    def __init__(
        self,
        trainset: list[dict[str, Any]],
        valset: list[dict[str, Any]],
    ) -> None:
        """Initialize adapter with explicit trainset and valset references.

        Note:
            Captures dataset identities for call tracking in assertions.
        """
        self._trainset = trainset
        self._valset = valset
        self.calls: list[dict[str, Any]] = []

    async def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[dict[str, Any], str]:
        """Evaluate candidates with dataset-specific score values.

        Note:
            Outputs higher scores on valset to expose scoring paths.
        """
        if batch is self._valset:
            scores = [0.9 for _ in batch]
        else:
            scores = [0.2 for _ in batch]
        trajectories = (
            [{"instruction": candidate["instruction"]} for _ in batch]
            if capture_traces
            else None
        )
        self.calls.append({"batch": batch, "capture_traces": capture_traces})
        return EvaluationBatch(
            outputs=[candidate["instruction"] for _ in batch],
            scores=scores,
            trajectories=trajectories,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[dict[str, Any], str],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build minimal reflective datasets for components.

        Note:
            Outputs compact reflection data for test assertions.
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
        """Propose a deterministic instruction update.

        Note:
            Outputs a consistent improvement for integration coverage.
        """
        return {"instruction": "improved"}


@pytest.mark.asyncio
async def test_engine_scores_on_valset(
    trainset_samples: list[dict[str, str]],
    valset_samples: list[dict[str, str]],
) -> None:
    """Engine should use valset scores for acceptance and results.

    Note:
        Separates trainset trace calls from valset scoring calls.
    """
    adapter = SplitAdapter(trainset_samples, valset_samples)
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

    # With default sum aggregation: 4 valset samples * 0.9 = 3.6
    assert result.final_score == pytest.approx(3.6)
    # valset_score is always mean-based for reporting
    assert result.valset_score == pytest.approx(0.9)
    assert result.trainset_score == pytest.approx(0.2)

    trace_batches = [call["batch"] for call in adapter.calls if call["capture_traces"]]
    score_batches = [
        call["batch"] for call in adapter.calls if not call["capture_traces"]
    ]
    assert trace_batches and score_batches
    assert all(batch is trainset_samples for batch in trace_batches)
    assert all(batch is valset_samples for batch in score_batches)


@pytest.mark.asyncio
async def test_engine_defaults_valset_to_trainset(
    trainset_samples: list[dict[str, str]],
) -> None:
    """Engine should reuse trainset for scoring when valset is omitted.

    Note:
        Shares trainset for scoring when no validation set is provided.
    """
    adapter = SplitAdapter(trainset_samples, trainset_samples)
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

    score_batches = [
        call["batch"] for call in adapter.calls if not call["capture_traces"]
    ]
    assert score_batches
    assert all(batch is trainset_samples for batch in score_batches)
