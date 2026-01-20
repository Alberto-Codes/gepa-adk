"""Contract tests for AsyncGEPAEngine protocol compliance."""

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig, EvolutionResult
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch

pytestmark = pytest.mark.contract


class MockAdapter:
    """Simple mock adapter for contract testing."""

    def __init__(self, scores: list[float]) -> None:
        """Initialize with predetermined scores."""
        self._scores = iter(scores)

    async def evaluate(self, batch, candidate, capture_traces=False):
        """Return mock evaluation batch."""
        score = next(self._scores, 0.5)
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
        )

    async def make_reflective_dataset(
        self, candidate, eval_batch, components_to_update
    ):
        """Return empty reflective dataset."""
        return {comp: [] for comp in components_to_update}

    async def propose_new_texts(
        self, candidate, reflective_dataset, components_to_update
    ):
        """Return mock proposals."""
        return {comp: f"Improved: {candidate[comp]}" for comp in components_to_update}


class TestAsyncGEPAEngineContract:
    """Test AsyncGEPAEngine protocol compliance."""

    @pytest.mark.asyncio
    async def test_engine_returns_evolution_result(self) -> None:
        """Test that engine.run() returns EvolutionResult."""
        adapter = MockAdapter(scores=[0.5])
        config = EvolutionConfig(max_iterations=0)
        candidate = Candidate(components={"instruction": "Be helpful"}, generation=0)
        batch = [{"input": "Hello", "expected": "Hi"}]
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        result = await engine.run()

        assert isinstance(result, EvolutionResult)
        assert hasattr(result, "original_score")
        assert hasattr(result, "final_score")
        assert hasattr(result, "evolved_components")
        assert hasattr(result, "iteration_history")
        assert hasattr(result, "total_iterations")

    @pytest.mark.asyncio
    async def test_ct105_iteration_records_track_evolved_component(self) -> None:
        """CT-105: Test that IterationRecord tracks which component was evolved.

        Contract: Each iteration record must include the `evolved_component`
        field identifying which component was modified in that iteration.
        For single-component evolution, this is always "instruction".
        """
        # Baseline + 2 iterations with improving scores
        adapter = MockAdapter(scores=[0.5, 0.5, 0.6, 0.6, 0.7, 0.7])
        config = EvolutionConfig(max_iterations=2)
        candidate = Candidate(components={"instruction": "Be helpful"}, generation=0)
        batch = [{"input": "Hello", "expected": "Hi"}]
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
        )

        result = await engine.run()

        # Contract: evolved_component field must exist and contain valid component name
        for record in result.iteration_history:
            assert hasattr(record, "evolved_component")
            assert record.evolved_component == "instruction"

    @pytest.mark.asyncio
    async def test_ct105_round_robin_alternates_components(self) -> None:
        """CT-105: Test that round-robin selector alternates evolved_component.

        Contract: When using RoundRobinComponentSelector with multiple components,
        the evolved_component field must cycle through components in order.
        """
        from gepa_adk.adapters.component_selector import RoundRobinComponentSelector

        # Multi-component candidate
        candidate = Candidate(
            components={
                "instruction": "Primary",  # Required by engine
                "gen1_instruction": "Generator 1",
                "gen2_instruction": "Generator 2",
            },
            generation=0,
        )

        # Baseline + 4 iterations to observe round-robin pattern
        adapter = MockAdapter(
            scores=[0.5, 0.5, 0.55, 0.55, 0.6, 0.6, 0.65, 0.65, 0.7, 0.7]
        )
        config = EvolutionConfig(max_iterations=4, min_improvement_threshold=0.0)
        batch = [{"input": "test"}]
        component_selector = RoundRobinComponentSelector()

        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=batch,
            component_selector=component_selector,
        )

        result = await engine.run()

        # Contract: evolved_component must alternate in round-robin fashion
        assert len(result.iteration_history) == 4
        evolved_components = [r.evolved_component for r in result.iteration_history]

        # Round-robin cycles through gen1_instruction, gen2_instruction
        # (instruction is excluded when other components exist)
        assert evolved_components[0] == "gen1_instruction"
        assert evolved_components[1] == "gen2_instruction"
        assert evolved_components[2] == "gen1_instruction"
        assert evolved_components[3] == "gen2_instruction"
