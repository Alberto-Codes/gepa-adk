"""Contract tests for trainset/valset separation behavior.

Note:
    Tests dataset split expectations for reflection versus scoring.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch

pytestmark = pytest.mark.contract


class RecordingAdapter(AsyncGEPAAdapter[dict[str, Any], dict[str, Any], str]):
    """Adapter that records dataset usage for reflection vs scoring.

    Note:
        Assists verification of dataset selection paths.
    """

    def __init__(
        self,
        trainset: list[dict[str, Any]],
        valset: list[dict[str, Any]],
    ) -> None:
        """Initialize adapter with trainset and valset references.

        Note:
            Captures dataset identities for verification in contract tests.
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
        """Evaluate candidates while recording dataset usage.

        Note:
            Outputs constant scores to keep assertions focused on routing.
        """
        scores = [0.5 for _ in batch]
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


class TestTrainValContract:
    """Contract tests for dataset split behavior."""

    @pytest.mark.asyncio
    async def test_reflection_uses_trainset_scoring_uses_valset(
        self,
        trainset_samples: list[dict[str, str]],
        valset_samples: list[dict[str, str]],
    ) -> None:
        """Trainset should drive reflection; valset should drive scoring.

        Note:
            Separates trace capture from scoring dataset usage.
        """
        adapter = RecordingAdapter(trainset_samples, valset_samples)
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

        await engine.run()

        trace_calls = [call for call in adapter.calls if call["capture_traces"]]
        scoring_calls = [call for call in adapter.calls if not call["capture_traces"]]
        assert trace_calls and scoring_calls
        assert all(call["batch"] is trainset_samples for call in trace_calls)
        assert all(call["batch"] is valset_samples for call in scoring_calls)
