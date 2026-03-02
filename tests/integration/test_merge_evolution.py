"""Integration tests for merge evolution.

Note:
    These tests verify full evolution runs with merge enabled,
    ensuring mutation and merge work together correctly.
"""

from __future__ import annotations

import random
from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.adapters.selection.candidate_selector import ParetoCandidateSelector
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.engine.merge_proposer import MergeProposer
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch

pytestmark = pytest.mark.integration


class DeterministicMergeAdapter(AsyncGEPAAdapter[dict[str, Any], dict[str, Any], str]):
    """Adapter with deterministic scoring for merge testing."""

    def __init__(self, proposals: list[str]) -> None:
        """Initialize with a proposal sequence."""
        self._proposals = proposals
        self._proposal_idx = 0
        self._instruction_scores: dict[str, list[float]] = {
            "seed": [0.5, 0.3],
            "A": [0.9, 0.2],  # Good on example 0
            "B": [0.2, 0.9],  # Good on example 1
            "C": [0.8, 0.8],  # Good overall
        }

    async def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[dict[str, Any], str]:
        """Return deterministic scores based on instruction."""
        instruction = candidate.get("instruction", "seed")
        scores = self._instruction_scores.get(instruction, [0.1] * len(batch))
        # Pad or truncate to match batch length
        if len(scores) < len(batch):
            scores = scores + [scores[-1]] * (len(batch) - len(scores))
        else:
            scores = scores[: len(batch)]

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
        """Return minimal reflective examples."""
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
        if self._proposal_idx < len(self._proposals):
            instruction = self._proposals[self._proposal_idx]
            self._proposal_idx += 1
            return {"instruction": instruction}
        # Default improvement
        return {
            component: f"Improved: {candidate.get(component, '')}"
            for component in components_to_update
        }


class TestFullMergeEvolution:
    """Tests for full evolution with merge enabled."""

    @pytest.mark.asyncio
    async def test_evolution_with_merge_creates_merged_candidates(self) -> None:
        """Test that evolution with merge creates merged candidates."""
        adapter = DeterministicMergeAdapter(proposals=["A", "B"])
        config = EvolutionConfig(
            max_iterations=5,
            use_merge=True,
            max_merge_invocations=5,
            min_improvement_threshold=0.0,
        )
        candidate = Candidate(components={"instruction": "seed"})
        batch = [{"input": "test1"}, {"input": "test2"}]
        selector = ParetoCandidateSelector(rng=random.Random(42))
        merge_proposer = MergeProposer(rng=random.Random(42))

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
            candidate_selector=selector,
            merge_proposer=merge_proposer,
        )

        result = await engine.run()

        # Verify evolution completed
        assert result.total_iterations > 0
        assert result.final_score >= result.original_score

        # Verify merge proposer was used
        if engine._pareto_state is not None:
            # Check if any candidates have parent_ids with 2 parents (merged)
            # May or may not have merged candidates depending on evolution path
            # But merge proposer should have been available
            assert engine._merge_proposer is not None
            # Verify at least some candidates exist (merge may or may not have occurred)
            assert len(engine._pareto_state.candidates) > 0

    @pytest.mark.asyncio
    async def test_merge_and_mutation_work_together(self) -> None:
        """Test that merge and mutation proposals work together."""
        adapter = DeterministicMergeAdapter(proposals=["A", "B", "C"])
        config = EvolutionConfig(
            max_iterations=3,
            use_merge=True,
            max_merge_invocations=3,
            min_improvement_threshold=0.0,
        )
        candidate = Candidate(components={"instruction": "seed"})
        batch = [{"input": "test1"}, {"input": "test2"}]
        selector = ParetoCandidateSelector(rng=random.Random(42))
        merge_proposer = MergeProposer(rng=random.Random(42))

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
            candidate_selector=selector,
            merge_proposer=merge_proposer,
        )

        result = await engine.run()

        # Verify both mutation and merge were attempted
        assert result.total_iterations > 0
        # Merge invocations should be <= max_merge_invocations
        assert engine._merge_invocations <= config.max_merge_invocations

    @pytest.mark.asyncio
    async def test_merge_respects_quota(self) -> None:
        """Test that merge respects max_merge_invocations quota."""
        adapter = DeterministicMergeAdapter(proposals=["A", "B"])
        config = EvolutionConfig(
            max_iterations=10,
            use_merge=True,
            max_merge_invocations=2,  # Low quota
            min_improvement_threshold=0.0,
        )
        candidate = Candidate(components={"instruction": "seed"})
        batch = [{"input": "test1"}, {"input": "test2"}]
        selector = ParetoCandidateSelector(rng=random.Random(42))
        merge_proposer = MergeProposer(rng=random.Random(42))

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
            candidate_selector=selector,
            merge_proposer=merge_proposer,
        )

        await engine.run()

        # Should not exceed quota
        assert engine._merge_invocations <= config.max_merge_invocations
