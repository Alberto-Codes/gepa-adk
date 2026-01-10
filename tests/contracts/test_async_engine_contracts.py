"""Contract tests for AsyncGEPAEngine protocol compliance."""

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig, EvolutionResult
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch


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

    async def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        """Return empty reflective dataset."""
        return {comp: [] for comp in components_to_update}

    async def propose_new_texts(self, candidate, reflective_dataset, components_to_update):
        """Return mock proposals."""
        return {comp: f"Improved: {candidate[comp]}" for comp in components_to_update}


@pytest.mark.contract
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
        assert hasattr(result, "evolved_instruction")
        assert hasattr(result, "iteration_history")
        assert hasattr(result, "total_iterations")
