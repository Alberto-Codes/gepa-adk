"""Acceptance tests for evaluation reuse when the valset is the trainset.

When no valset is given, or the valset is the same list object as the
trainset, the engine must evaluate each candidate once and use that batch
for both reflection and scoring. A distinct valset keeps two evaluations.

Notes:
    The adapter is the configurable mock from ``tests/fixtures/adapters.py``
    and records every evaluate() call. A stop callback records the
    ``total_evaluations`` the engine reports to stoppers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.domain.stopper import StopperState
from gepa_adk.engine import AsyncGEPAEngine
from tests.fixtures.adapters import ConfigurableMockAdapter, create_mock_adapter

pytestmark = pytest.mark.unit


async def _propose_improved(
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components: list[str],
) -> dict[str, str]:
    """Return a proposal that differs from the parent so it gets evaluated.

    Args:
        candidate: Parent component texts.
        reflective_dataset: Reflection examples (unused).
        components: Components to update (unused).

    Returns:
        The parent's instruction with a trailing "!" appended.
    """
    return {"instruction": candidate["instruction"] + "!"}


class _Recorder:
    """Stop callback that records the evaluation count it is shown.

    Attributes:
        seen (list[int]): ``total_evaluations`` values observed, one per call.
    """

    def __init__(self) -> None:
        """Start with no observations."""
        self.seen: list[int] = []

    def __call__(self, state: StopperState) -> bool:
        """Record total_evaluations and never stop.

        Args:
            state: Snapshot of engine progress.

        Returns:
            False, so the engine runs to max_iterations.
        """
        self.seen.append(state.total_evaluations)
        return False


async def _run(
    trainset: list[dict[str, str]],
    valset: list[dict[str, str]] | None,
) -> tuple[ConfigurableMockAdapter, _Recorder]:
    adapter = create_mock_adapter(default_score=0.5, custom_propose=_propose_improved)
    recorder = _Recorder()
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=2,
            patience=0,
            min_improvement_threshold=0.0,
            stop_callbacks=[recorder],
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        valset=valset,
    )
    await engine.run()
    return adapter, recorder


class TestDefaultedValsetReusesTrainsetBatch:
    """One evaluation per candidate when valset is absent or is the trainset."""

    @pytest.mark.asyncio
    async def test_no_valset_evaluates_each_candidate_once(
        self, trainset_samples: list[dict[str, str]]
    ) -> None:
        """Baseline plus two proposals is three evaluate() calls, not six."""
        adapter, recorder = await _run(trainset_samples, None)

        assert len(adapter.evaluate_calls) == 3
        assert all(batch is trainset_samples for batch, _, _ in adapter.evaluate_calls)
        assert all(capture for _, _, capture in adapter.evaluate_calls)
        n = len(trainset_samples)
        assert recorder.seen == [n, 2 * n]

    @pytest.mark.asyncio
    async def test_same_object_valset_evaluates_each_candidate_once(
        self, trainset_samples: list[dict[str, str]]
    ) -> None:
        """Passing the trainset list itself as valset is treated as defaulted."""
        adapter, recorder = await _run(trainset_samples, trainset_samples)

        assert len(adapter.evaluate_calls) == 3
        n = len(trainset_samples)
        assert recorder.seen == [n, 2 * n]

    @pytest.mark.asyncio
    async def test_distinct_valset_still_evaluates_twice(
        self,
        trainset_samples: list[dict[str, str]],
        valset_samples: list[dict[str, str]],
    ) -> None:
        """A separate valset keeps reflection and scoring evaluations apart."""
        adapter, recorder = await _run(trainset_samples, valset_samples)

        assert len(adapter.evaluate_calls) == 6
        scoring = [c for c in adapter.evaluate_calls if not c[2]]
        assert len(scoring) == 3
        assert all(batch is valset_samples for batch, _, _ in scoring)
        per_candidate = len(trainset_samples) + len(valset_samples)
        assert recorder.seen == [per_candidate, 2 * per_candidate]
