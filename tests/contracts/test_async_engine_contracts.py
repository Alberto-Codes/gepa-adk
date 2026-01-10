"""Contract tests for AsyncGEPAEngine protocol compliance."""

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig, EvolutionResult
from gepa_adk.engine.async_engine import AsyncGEPAEngine


@pytest.mark.contract
class TestAsyncGEPAEngineContract:
    """Test AsyncGEPAEngine protocol compliance."""

    @pytest.mark.asyncio
    async def test_engine_returns_evolution_result(self) -> None:
        """Test that engine.run() returns EvolutionResult."""
        from tests.unit.engine.conftest import MockAdapter

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
