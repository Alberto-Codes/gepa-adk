"""Integration tests for Pareto frontier selection in AsyncGEPAEngine."""

from __future__ import annotations

import random
from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.adapters.candidate_selector import (
    CurrentBestCandidateSelector,
    ParetoCandidateSelector,
)
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.domain.state import ParetoState
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch
from gepa_adk.ports.selector import CandidateSelectorProtocol

pytestmark = pytest.mark.integration


class RecordingSelector(CandidateSelectorProtocol):
    """Selector wrapper that records selections and best indices."""

    def __init__(self, selector: CandidateSelectorProtocol) -> None:
        """Initialize the recording selector wrapper."""
        self._selector = selector
        self.selections: list[int] = []
        self.best_indices: list[int | None] = []

    async def select_candidate(self, state: ParetoState) -> int:
        """Select a candidate and record selection metadata."""
        selected = await self._selector.select_candidate(state)
        self.selections.append(selected)
        self.best_indices.append(state.best_average_idx)
        return selected


class DeterministicAdapter(AsyncGEPAAdapter[dict[str, Any], dict[str, Any], str]):
    """Adapter with deterministic scoring and proposal sequence."""

    def __init__(self, proposals: list[str]) -> None:
        """Initialize with a proposal sequence."""
        self._proposals = proposals
        self._proposal_idx = 0

    async def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[dict[str, Any], str]:
        """Return deterministic scores based on instruction text."""
        instruction = candidate["instruction"]
        score_map = {
            "seed": [0.5, 0.5, 0.5],
            "A": [0.9, 0.2, 0.2],
            "B": [0.2, 0.9, 0.2],
            "C": [0.2, 0.2, 0.9],
            "D": [0.8, 0.8, 0.8],
        }
        scores = score_map.get(instruction, [0.1 for _ in batch])
        outputs = [instruction for _ in batch]
        trajectories = (
            [{"instruction": instruction, "index": idx} for idx in range(len(batch))]
            if capture_traces
            else None
        )
        return EvaluationBatch(
            outputs=outputs, scores=scores, trajectories=trajectories
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[dict[str, Any], str],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Return minimal reflective examples per component."""
        return {
            component: [{"candidate": candidate, "scores": eval_batch.scores}]
            for component in components_to_update
        }

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Return the next instruction from the proposal sequence."""
        instruction = self._proposals[self._proposal_idx % len(self._proposals)]
        self._proposal_idx += 1
        return {"instruction": instruction}


async def _run_engine(
    selector: CandidateSelectorProtocol,
) -> tuple[AsyncGEPAEngine[dict[str, Any], dict[str, Any], str], RecordingSelector]:
    trainset = [{"input": "x"}, {"input": "y"}, {"input": "z"}]
    adapter = DeterministicAdapter(proposals=["A", "B", "C", "D", "A", "B", "C", "D"])
    recording_selector = RecordingSelector(selector)
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(max_iterations=8, patience=0),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        candidate_selector=recording_selector,
    )
    await engine.run()
    return engine, recording_selector


@pytest.mark.asyncio
async def test_pareto_evolution_discovers_specialists_and_explores() -> None:
    """Pareto selection keeps specialists and explores non-best candidates."""
    engine, recording = await _run_engine(
        ParetoCandidateSelector(rng=random.Random(42))
    )

    pareto_state = engine._pareto_state
    assert pareto_state is not None
    assert len(pareto_state.frontier.get_non_dominated()) >= 2

    non_best = sum(
        1
        for selected, best in zip(recording.selections, recording.best_indices)
        if best is not None and selected != best
    )
    exploration_rate = non_best / len(recording.selections)
    assert exploration_rate >= 0.3


@pytest.mark.asyncio
async def test_selector_switching_respects_greedy_behavior() -> None:
    """Greedy selector always returns the best-average candidate."""
    engine, recording = await _run_engine(CurrentBestCandidateSelector())

    assert engine._pareto_state is not None
    for selected, best in zip(recording.selections, recording.best_indices):
        assert best is not None
        assert selected == best
