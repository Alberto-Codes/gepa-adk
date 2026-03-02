"""Integration tests for multi-component evolution."""

from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.adapters.selection.component_selector import (
    AllComponentSelector,
    RoundRobinComponentSelector,
)
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch

pytestmark = pytest.mark.integration


class MultiComponentMockAdapter(AsyncGEPAAdapter[dict[str, str], dict[str, Any], None]):
    """Mock adapter that supports multi-component updates."""

    def __init__(self, scores: list[float] | None = None) -> None:
        """Initialize mock adapter with predetermined scores."""
        self._scores = iter(scores) if scores else iter([0.5, 0.6, 0.7, 0.8, 0.9])
        self.proposed_components_history: list[list[str]] = []

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate candidate and return mock results."""
        score = next(self._scores, 0.5)
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Create empty reflective dataset."""
        return {comp: [] for comp in components_to_update}

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose new texts and record request."""
        # Record which components were requested for update
        self.proposed_components_history.append(components_to_update)

        return {comp: f"Improved: {candidate[comp]}" for comp in components_to_update}


class TestMultiComponentEvolution:
    """Integration tests for component selection strategies."""

    @pytest.mark.asyncio
    async def test_round_robin_cycling(self) -> None:
        """Test round-robin evolution cycles through components (T047)."""
        # Baseline: 2 scores (reflection + scoring)
        # 3 iterations: 2 scores each (reflection + scoring)
        # Total: 2 + (2*3) = 8 scores
        adapter = MultiComponentMockAdapter(
            scores=[0.5, 0.5, 0.6, 0.6, 0.7, 0.7, 0.8, 0.8]
        )
        # 3 components: instruction, comp1, comp2
        candidate = Candidate(
            components={"instruction": "base", "comp1": "v1", "comp2": "v2"},
            generation=0,
        )
        config = EvolutionConfig(max_iterations=3)
        selector = RoundRobinComponentSelector()

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=[{"input": "test"}],
            component_selector=selector,
        )

        await engine.run()

        # Verify history of proposed components
        history = adapter.proposed_components_history
        assert len(history) == 3
        # Should cycle through comp1, comp2 (instruction excluded)

        assert set(history[0]) == {"comp1"} or set(history[0]) == {"comp2"}
        assert len(history[0]) == 1

        # Check all components eventually touched if enough iterations
        all_touched = set()
        for comps in history:
            all_touched.update(comps)
        assert all_touched == {"comp1", "comp2"}

    @pytest.mark.asyncio
    async def test_all_components_evolution(self) -> None:
        """Test all-components evolution updates everything (T048)."""
        # Baseline: 2 scores (reflection + scoring)
        # 2 iterations: 2 scores each (reflection + scoring)
        # Total: 2 + (2*2) = 6 scores
        adapter = MultiComponentMockAdapter(scores=[0.5, 0.5, 0.6, 0.6, 0.7, 0.7])
        candidate = Candidate(
            components={"instruction": "base", "comp1": "v1", "comp2": "v2"},
            generation=0,
        )
        config = EvolutionConfig(max_iterations=2)
        selector = AllComponentSelector()

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=[{"input": "test"}],
            component_selector=selector,
        )

        await engine.run()

        history = adapter.proposed_components_history
        assert len(history) == 2
        # Each iteration should update ALL components (excluding instruction due to filter)
        for comps in history:
            assert set(comps) == {"comp1", "comp2"}

    @pytest.mark.asyncio
    async def test_backward_compatibility(self) -> None:
        """Test single component candidate behaves as before (T050)."""
        # Baseline: 2 scores (reflection + scoring)
        # 1 iteration: 2 scores (reflection + scoring)
        # Total: 2 + 2 = 4 scores
        adapter = MultiComponentMockAdapter(scores=[0.5, 0.5, 0.6, 0.6])
        candidate = Candidate(components={"instruction": "base"}, generation=0)
        config = EvolutionConfig(max_iterations=1)
        # Default selector (RoundRobin)

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=[{"input": "test"}],
        )

        await engine.run()

        history = adapter.proposed_components_history
        assert len(history) == 1
        assert history[0] == ["instruction"]
