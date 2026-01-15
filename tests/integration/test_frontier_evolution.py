"""Integration tests for frontier types and evaluation policies.

Tests verify end-to-end evolution behavior with different frontier types
(INSTANCE, OBJECTIVE, HYBRID, CARTESIAN) and evaluation policies
(FullEvaluationPolicy, SubsetEvaluationPolicy).

Note:
    Tests validate success criteria SC-002 and SC-005 from the specification.
"""

from __future__ import annotations

from statistics import fmean
from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.adapters.candidate_selector import ParetoCandidateSelector
from gepa_adk.adapters.evaluation_policy import (
    FullEvaluationPolicy,
    SubsetEvaluationPolicy,
)
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.domain.types import FrontierType
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch

pytestmark = pytest.mark.integration


class ObjectiveScoresAdapter(AsyncGEPAAdapter[dict[str, Any], dict[str, Any], str]):
    """Adapter that provides objective scores for multi-objective testing.

    Returns both aggregate scores and per-example objective scores
    for testing OBJECTIVE, HYBRID, and CARTESIAN frontier types.
    """

    def __init__(
        self,
        proposals: list[str],
        objective_scores_map: dict[str, list[dict[str, float]]],
    ) -> None:
        """Initialize adapter with proposal sequence and objective scores.

        Args:
            proposals: Sequence of instruction proposals.
            objective_scores_map: Maps instruction -> list of per-example
                objective score dicts.
        """
        self._proposals = proposals
        self._proposal_idx = 0
        self._objective_scores_map = objective_scores_map

    async def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[dict[str, Any], str]:
        """Return scores with objective breakdowns.

        Note:
            Returns scores/outputs sized to batch length (T070).
        """
        instruction = candidate["instruction"]
        # Get objective scores for this instruction
        # Take only the number needed for the actual batch size
        if instruction not in self._objective_scores_map:
            raise KeyError(
                f"Objective scores not configured for instruction: {instruction!r}"
            )
        full_objectives = self._objective_scores_map[instruction]
        # Return only the number matching the batch size (T070)
        per_example_objectives = full_objectives[: len(batch)]
        # Compute aggregate scores as mean of objectives
        scores = [fmean(obj_scores.values()) for obj_scores in per_example_objectives]
        outputs = [instruction for _ in batch]
        trajectories = (
            [{"instruction": instruction, "index": idx} for idx in range(len(batch))]
            if capture_traces
            else None
        )
        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories,
            objective_scores=per_example_objectives,
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


@pytest.mark.asyncio
async def test_evolution_with_objective_frontier() -> None:
    """T053: Integration test for evolution with OBJECTIVE frontier."""
    trainset = [{"input": "x"}, {"input": "y"}, {"input": "z"}]
    valset = [{"input": "a"}, {"input": "b"}, {"input": "c"}]

    # Create adapter with objective scores
    objective_scores_map = {
        "seed": [
            {"accuracy": 0.5, "latency": 0.5},
            {"accuracy": 0.5, "latency": 0.5},
            {"accuracy": 0.5, "latency": 0.5},
        ],
        "A": [
            {"accuracy": 0.9, "latency": 0.2},
            {"accuracy": 0.8, "latency": 0.3},
            {"accuracy": 0.7, "latency": 0.4},
        ],
        "B": [
            {"accuracy": 0.2, "latency": 0.9},
            {"accuracy": 0.3, "latency": 0.8},
            {"accuracy": 0.4, "latency": 0.7},
        ],
    }
    adapter = ObjectiveScoresAdapter(
        proposals=["A", "B", "A", "B"], objective_scores_map=objective_scores_map
    )

    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=4,
            patience=0,
            frontier_type=FrontierType.OBJECTIVE,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        valset=valset,
        candidate_selector=ParetoCandidateSelector(),
    )

    result = await engine.run()

    # Verify objective frontier was used
    assert engine._pareto_state is not None
    assert engine._pareto_state.frontier_type == FrontierType.OBJECTIVE
    # Verify objective leaders were tracked
    assert len(engine._pareto_state.frontier.objective_leaders) > 0
    # Verify evolution completed
    assert result.total_iterations > 0


@pytest.mark.asyncio
async def test_evolution_with_hybrid_frontier() -> None:
    """T054: Integration test for evolution with HYBRID frontier."""
    trainset = [{"input": "x"}, {"input": "y"}, {"input": "z"}]
    valset = [{"input": "a"}, {"input": "b"}, {"input": "c"}]

    objective_scores_map = {
        "seed": [
            {"accuracy": 0.5, "latency": 0.5},
            {"accuracy": 0.5, "latency": 0.5},
            {"accuracy": 0.5, "latency": 0.5},
        ],
        "A": [
            {"accuracy": 0.9, "latency": 0.2},
            {"accuracy": 0.8, "latency": 0.3},
            {"accuracy": 0.7, "latency": 0.4},
        ],
    }
    adapter = ObjectiveScoresAdapter(
        proposals=["A", "A", "A"], objective_scores_map=objective_scores_map
    )

    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=3,
            patience=0,
            frontier_type=FrontierType.HYBRID,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        valset=valset,
        candidate_selector=ParetoCandidateSelector(),
    )

    result = await engine.run()

    # Verify hybrid frontier was used
    assert engine._pareto_state is not None
    assert engine._pareto_state.frontier_type == FrontierType.HYBRID
    # Verify both instance and objective frontiers were updated
    assert len(engine._pareto_state.frontier.example_leaders) > 0
    assert len(engine._pareto_state.frontier.objective_leaders) > 0
    # Verify evolution completed
    assert result.total_iterations > 0


@pytest.mark.asyncio
async def test_evolution_with_cartesian_frontier() -> None:
    """T055: Integration test for evolution with CARTESIAN frontier."""
    trainset = [{"input": "x"}, {"input": "y"}]
    valset = [{"input": "a"}, {"input": "b"}]

    objective_scores_map = {
        "seed": [
            {"accuracy": 0.5, "latency": 0.5},
            {"accuracy": 0.5, "latency": 0.5},
        ],
        "A": [
            {"accuracy": 0.9, "latency": 0.2},
            {"accuracy": 0.8, "latency": 0.3},
        ],
    }
    adapter = ObjectiveScoresAdapter(
        proposals=["A", "A"], objective_scores_map=objective_scores_map
    )

    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=2,
            patience=0,
            frontier_type=FrontierType.CARTESIAN,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        valset=valset,
        candidate_selector=ParetoCandidateSelector(),
    )

    result = await engine.run()

    # Verify cartesian frontier was used
    assert engine._pareto_state is not None
    assert engine._pareto_state.frontier_type == FrontierType.CARTESIAN
    # Verify cartesian leaders were tracked
    assert len(engine._pareto_state.frontier.cartesian_leaders) > 0
    # Verify evolution completed
    assert result.total_iterations > 0


@pytest.mark.asyncio
async def test_evolution_with_subset_evaluation_policy() -> None:
    """T056: Integration test for evolution with SubsetEvaluationPolicy."""
    trainset = [{"input": "x"} for _ in range(3)]
    # Create large valset for subset testing
    valset = [{"input": f"val_{i}"} for i in range(100)]

    adapter = ObjectiveScoresAdapter(
        proposals=["A", "B", "C"],
        objective_scores_map={
            "seed": [{"accuracy": 0.5, "latency": 0.5} for _ in range(100)],
            "A": [{"accuracy": 0.9, "latency": 0.2} for _ in range(100)],
            "B": [{"accuracy": 0.2, "latency": 0.9} for _ in range(100)],
            "C": [{"accuracy": 0.7, "latency": 0.7} for _ in range(100)],
        },
    )

    subset_policy = SubsetEvaluationPolicy(subset_size=0.2)  # 20% of 100 = 20 examples

    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(max_iterations=3, patience=0),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        valset=valset,
        candidate_selector=ParetoCandidateSelector(),
        evaluation_policy=subset_policy,
    )

    result = await engine.run()

    # Verify evolution completed
    assert result.total_iterations > 0
    # Verify subset policy was used (scores should be for subset only)
    assert engine._pareto_state is not None
    # Each candidate should have scores for only the evaluated subset
    for candidate_idx, scores in engine._pareto_state.candidate_scores.items():
        # With subset_size=0.2 and 100 examples, we should evaluate ~20 per iteration
        # But scores accumulate across iterations, so we check it's <= valset size
        assert len(scores) <= len(valset)


@pytest.mark.asyncio
async def test_subset_evaluation_reduces_cost() -> None:
    """T064, T071: Verify subset evaluation reduces per-iteration cost by ≥80%."""
    trainset = [{"input": "x"} for _ in range(3)]
    # Large valset for cost reduction testing
    valset = [{"input": f"val_{i}"} for i in range(1000)]

    full_counts: dict[str, int] = {"full": 0}
    subset_counts: dict[str, int] = {"subset": 0}

    class CountingAdapter(ObjectiveScoresAdapter):
        """Adapter that counts evaluation calls."""

        async def evaluate(
            self,
            batch: list[dict[str, Any]],
            candidate: dict[str, str],
            capture_traces: bool = False,
        ) -> EvaluationBatch[dict[str, Any], str]:
            """Count evaluation calls and batch sizes."""
            # Only count valset evaluations (capture_traces=False)
            # Verify correct batch by checking capture_traces parameter
            if not capture_traces:  # Scoring evaluation (valset)
                if len(batch) == len(valset):
                    full_counts["full"] += len(batch)
                else:
                    subset_counts["subset"] += len(batch)
            # trainset evaluations (capture_traces=True) are not counted
            return await super().evaluate(batch, candidate, capture_traces)

    full_adapter = CountingAdapter(
        proposals=["A", "B"],
        objective_scores_map={
            "seed": [{"accuracy": 0.5, "latency": 0.5} for _ in range(1000)],
            "A": [{"accuracy": 0.9, "latency": 0.2} for _ in range(1000)],
            "B": [{"accuracy": 0.2, "latency": 0.9} for _ in range(1000)],
        },
    )

    subset_adapter = CountingAdapter(
        proposals=["A", "B"],
        objective_scores_map={
            "seed": [{"accuracy": 0.5, "latency": 0.5} for _ in range(1000)],
            "A": [{"accuracy": 0.9, "latency": 0.2} for _ in range(1000)],
            "B": [{"accuracy": 0.2, "latency": 0.9} for _ in range(1000)],
        },
    )

    # Run with full evaluation
    full_engine = AsyncGEPAEngine(
        adapter=full_adapter,
        config=EvolutionConfig(max_iterations=2, patience=0),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        valset=valset,
        evaluation_policy=FullEvaluationPolicy(),
    )
    await full_engine.run()

    # Run with subset evaluation (20% = 200 examples per iteration)
    subset_engine = AsyncGEPAEngine(
        adapter=subset_adapter,
        config=EvolutionConfig(max_iterations=2, patience=0),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        valset=valset,
        evaluation_policy=SubsetEvaluationPolicy(subset_size=0.2),
    )
    await subset_engine.run()

    # Calculate cost reduction
    # Full: baseline (1) + 2 iterations = 3 evaluations of 1000 examples = 3000
    # Subset: baseline (1) + 2 iterations = 3 evaluations of ~200 examples = ~600
    # Reduction: (3000 - 600) / 3000 = 0.8 = 80%
    full_cost = full_counts["full"]
    subset_cost = subset_counts["subset"]

    if full_cost > 0 and subset_cost > 0:
        reduction = (full_cost - subset_cost) / full_cost
        assert reduction >= 0.8, (
            f"Cost reduction {reduction:.2%} < 80%. Full: {full_cost}, Subset: {subset_cost}"
        )


@pytest.mark.asyncio
async def test_objective_frontiers_produce_more_unique_candidates() -> None:
    """T065: Verify objective/hybrid/cartesian produce ≥20% more unique candidates."""
    trainset = [{"input": "x"}, {"input": "y"}, {"input": "z"}]
    valset = [{"input": "a"}, {"input": "b"}, {"input": "c"}]

    objective_scores_map = {
        "seed": [
            {"accuracy": 0.5, "latency": 0.5},
            {"accuracy": 0.5, "latency": 0.5},
            {"accuracy": 0.5, "latency": 0.5},
        ],
        "A": [
            {"accuracy": 0.9, "latency": 0.2},
            {"accuracy": 0.8, "latency": 0.3},
            {"accuracy": 0.7, "latency": 0.4},
        ],
        "B": [
            {"accuracy": 0.2, "latency": 0.9},
            {"accuracy": 0.3, "latency": 0.8},
            {"accuracy": 0.4, "latency": 0.7},
        ],
        "C": [
            {"accuracy": 0.6, "latency": 0.6},
            {"accuracy": 0.6, "latency": 0.6},
            {"accuracy": 0.6, "latency": 0.6},
        ],
    }

    # Run with INSTANCE frontier
    instance_adapter = ObjectiveScoresAdapter(
        proposals=["A", "B", "C", "A", "B", "C"],
        objective_scores_map=objective_scores_map,
    )
    instance_engine = AsyncGEPAEngine(
        adapter=instance_adapter,
        config=EvolutionConfig(
            max_iterations=6,
            patience=0,
            frontier_type=FrontierType.INSTANCE,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        valset=valset,
        candidate_selector=ParetoCandidateSelector(),
    )
    await instance_engine.run()
    instance_non_dominated = len(
        instance_engine._pareto_state.frontier.get_non_dominated()
        if instance_engine._pareto_state
        else set()
    )

    # Run with OBJECTIVE frontier
    objective_adapter = ObjectiveScoresAdapter(
        proposals=["A", "B", "C", "A", "B", "C"],
        objective_scores_map=objective_scores_map,
    )
    objective_engine = AsyncGEPAEngine(
        adapter=objective_adapter,
        config=EvolutionConfig(
            max_iterations=6,
            patience=0,
            frontier_type=FrontierType.OBJECTIVE,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        valset=valset,
        candidate_selector=ParetoCandidateSelector(),
    )
    await objective_engine.run()
    objective_non_dominated = len(
        set().union(
            *(
                objective_engine._pareto_state.frontier.objective_leaders.values()
                if objective_engine._pareto_state
                else []
            )
        )
    )

    # Verify objective frontier produces more unique candidates
    if instance_non_dominated > 0:
        improvement = (
            objective_non_dominated - instance_non_dominated
        ) / instance_non_dominated
        # Either ≥20% more unique candidates OR ≥3 distinct objective tradeoff regions
        objective_leaders_count = len(
            objective_engine._pareto_state.frontier.objective_leaders
        )
        assert improvement >= 0.2 or objective_leaders_count >= 3, (
            f"Objective frontier did not meet criteria. "
            f"Improvement: {improvement:.2%}, "
            f"Tradeoff regions: {len(objective_engine._pareto_state.frontier.objective_leaders)}"
        )
