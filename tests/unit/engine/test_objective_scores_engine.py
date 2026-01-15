"""Unit tests for objective_scores passthrough in AsyncGEPAEngine.

Note:
    Tests verify that objective_scores flow correctly through engine state,
    iteration recording, and result building.
"""

from __future__ import annotations

from typing import Any

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch

from .conftest import MockAdapter

pytestmark = pytest.mark.unit


class MockAdapterWithObjectiveScores(MockAdapter):
    """Mock adapter that returns objective_scores."""

    def __init__(
        self,
        scores: list[float] | None = None,
        objective_scores: dict[str, float] | None = None,
    ) -> None:
        """Initialize mock adapter with objective_scores.

        Args:
            scores: List of scores to return sequentially.
            objective_scores: Objective scores dict to return for each example
                (same for all calls). Defaults to {"accuracy": 0.9, "latency": 0.8}.
        """
        super().__init__(scores)
        self._objective_scores = objective_scores or {"accuracy": 0.9, "latency": 0.8}

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate candidate and return mock results with objective_scores."""
        self._call_count += 1
        self._evaluate_calls.append((batch, candidate, capture_traces))
        score = next(self._scores, 0.5)
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
            objective_scores=[self._objective_scores] * len(batch),
        )


class MockAdapterWithoutObjectiveScores(MockAdapter):
    """Mock adapter that does not return objective_scores."""

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate candidate and return mock results without objective_scores."""
        self._call_count += 1
        self._evaluate_calls.append((batch, candidate, capture_traces))
        score = next(self._scores, 0.5)
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
            objective_scores=None,  # Explicitly None
        )


class TestEngineStateWithObjectiveScores:
    """Unit tests for _EngineState with best_objective_scores."""

    @pytest.mark.asyncio
    async def test_engine_state_initializes_with_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """_EngineState stores best_objective_scores after baseline initialization."""
        adapter = MockAdapterWithObjectiveScores(scores=[0.5, 0.5])
        config = EvolutionConfig(max_iterations=0)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        await engine.run()

        assert engine._state is not None
        assert engine._state.best_objective_scores == [
            {"accuracy": 0.9, "latency": 0.8}
        ]

    @pytest.mark.asyncio
    async def test_engine_state_handles_none_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """_EngineState handles None objective_scores gracefully."""
        adapter = MockAdapterWithoutObjectiveScores(scores=[0.5, 0.5])
        config = EvolutionConfig(max_iterations=0)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        await engine.run()

        assert engine._state is not None
        assert engine._state.best_objective_scores is None


class TestRecordIterationWithObjectiveScores:
    """Unit tests for _record_iteration passing objective_scores."""

    @pytest.mark.asyncio
    async def test_record_iteration_passes_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """_record_iteration includes objective_scores in IterationRecord."""
        adapter = MockAdapterWithObjectiveScores(
            scores=[0.5, 0.5, 0.6, 0.6], objective_scores={"accuracy": 0.85}
        )
        config = EvolutionConfig(max_iterations=1)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert len(result.iteration_history) == 1
        record = result.iteration_history[0]
        assert record.objective_scores == [{"accuracy": 0.85}]

    @pytest.mark.asyncio
    async def test_record_iteration_with_none_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """_record_iteration handles None objective_scores."""
        adapter = MockAdapterWithoutObjectiveScores(scores=[0.5, 0.5, 0.6, 0.6])
        config = EvolutionConfig(max_iterations=1)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert len(result.iteration_history) == 1
        record = result.iteration_history[0]
        assert record.objective_scores is None


class TestBuildResultWithObjectiveScores:
    """Unit tests for _build_result including objective_scores."""

    @pytest.mark.asyncio
    async def test_build_result_includes_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """_build_result includes best_objective_scores in EvolutionResult."""
        adapter = MockAdapterWithObjectiveScores(scores=[0.5, 0.5])
        config = EvolutionConfig(max_iterations=0)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert result.objective_scores == [{"accuracy": 0.9, "latency": 0.8}]

    @pytest.mark.asyncio
    async def test_build_result_with_none_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """_build_result handles None objective_scores."""
        adapter = MockAdapterWithoutObjectiveScores(scores=[0.5, 0.5])
        config = EvolutionConfig(max_iterations=0)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert result.objective_scores is None


class TestInitializeBaselineWithObjectiveScores:
    """Unit tests for _initialize_baseline extracting objective_scores."""

    @pytest.mark.asyncio
    async def test_initialize_baseline_extracts_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """_initialize_baseline extracts and stores objective_scores from scoring_batch."""
        adapter = MockAdapterWithObjectiveScores(
            scores=[0.5, 0.5], objective_scores={"accuracy": 0.95, "cost": 0.7}
        )
        config = EvolutionConfig(max_iterations=0)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        await engine.run()

        assert engine._state is not None
        assert engine._state.best_objective_scores == [{"accuracy": 0.95, "cost": 0.7}]

    @pytest.mark.asyncio
    async def test_initialize_baseline_handles_missing_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """_initialize_baseline handles missing objective_scores gracefully."""
        adapter = MockAdapterWithoutObjectiveScores(scores=[0.5, 0.5])
        config = EvolutionConfig(max_iterations=0)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        await engine.run()

        assert engine._state is not None
        assert engine._state.best_objective_scores is None


class TestAcceptProposalWithObjectiveScores:
    """Unit tests for _accept_proposal updating best_objective_scores."""

    @pytest.mark.asyncio
    async def test_accept_proposal_updates_best_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """_accept_proposal stores objective_scores in _EngineState.best_objective_scores."""
        # Baseline: 0.5, Proposal: 0.6 (accepted)
        adapter = MockAdapterWithObjectiveScores(
            scores=[0.5, 0.5, 0.6, 0.6],
            objective_scores={"accuracy": 0.9},
        )
        config = EvolutionConfig(max_iterations=1)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        await engine.run()

        assert engine._state is not None
        # Should have updated to proposal's objective_scores
        assert engine._state.best_objective_scores == [{"accuracy": 0.9}]

    @pytest.mark.asyncio
    async def test_accept_proposal_handles_none_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """_accept_proposal handles None objective_scores."""
        # Baseline: 0.5, Proposal: 0.6 (accepted)
        adapter = MockAdapterWithoutObjectiveScores(scores=[0.5, 0.5, 0.6, 0.6])
        config = EvolutionConfig(max_iterations=1)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        await engine.run()

        assert engine._state is not None
        assert engine._state.best_objective_scores is None


class TestRunMethodWithObjectiveScores:
    """Unit tests for run() method passing objective_scores."""

    @pytest.mark.asyncio
    async def test_run_passes_objective_scores_from_scoring_batch(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """run() method passes objective_scores from scoring_batch to _record_iteration."""
        adapter = MockAdapterWithObjectiveScores(
            scores=[0.5, 0.5, 0.6, 0.6],
            objective_scores={"accuracy": 0.88, "latency": 0.92},
        )
        config = EvolutionConfig(max_iterations=1)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        # Check that iteration history has objective_scores
        assert len(result.iteration_history) == 1
        assert result.iteration_history[0].objective_scores == [
            {"accuracy": 0.88, "latency": 0.92}
        ]
        # Check that result has objective_scores from best candidate
        assert result.objective_scores == [{"accuracy": 0.88, "latency": 0.92}]


class TestBackwardCompatibilityEdgeCases:
    """Unit tests for backward compatibility edge cases."""

    @pytest.mark.asyncio
    async def test_partially_populated_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test handling of partially populated objective_scores.

        Some examples have scores, others None.
        """

        # Create a custom adapter that returns None for some calls
        class PartiallyPopulatedAdapter(MockAdapter):
            def __init__(self) -> None:
                super().__init__(scores=[0.5, 0.5, 0.6, 0.6])
                self._call_count = 0

            async def evaluate(
                self,
                batch: list[Any],
                candidate: dict[str, str],
                capture_traces: bool = False,
            ) -> EvaluationBatch:
                self._call_count += 1
                score = next(self._scores, 0.5)
                # Return objective_scores only for scoring calls (even-numbered calls)
                objective_scores = (
                    [{"accuracy": 0.9}] * len(batch)
                    if self._call_count % 2 == 0
                    else None
                )
                return EvaluationBatch(
                    outputs=[None] * len(batch),
                    scores=[score] * len(batch),
                    trajectories=[{}] * len(batch) if capture_traces else None,
                    objective_scores=objective_scores,
                )

        adapter = PartiallyPopulatedAdapter()
        config = EvolutionConfig(max_iterations=1)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        # Baseline scoring call (call 2) should have objective_scores
        # Iteration scoring call (call 4) should have objective_scores
        assert result.objective_scores is not None
        assert len(result.iteration_history) == 1
        assert result.iteration_history[0].objective_scores is not None

    @pytest.mark.asyncio
    async def test_empty_dict_objective_scores(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test passthrough of empty dict objective_scores ({})."""

        class EmptyDictAdapter(MockAdapter):
            async def evaluate(
                self,
                batch: list[Any],
                candidate: dict[str, str],
                capture_traces: bool = False,
            ) -> EvaluationBatch:
                score = next(self._scores, 0.5)
                return EvaluationBatch(
                    outputs=[None] * len(batch),
                    scores=[score] * len(batch),
                    trajectories=[{}] * len(batch) if capture_traces else None,
                    objective_scores=[{}] * len(batch),  # Empty dict
                )

        adapter = EmptyDictAdapter(scores=[0.5, 0.5])
        config = EvolutionConfig(max_iterations=0)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert result.objective_scores == [{}]

    @pytest.mark.asyncio
    async def test_heterogeneous_keys_across_examples(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test handling of heterogeneous objective keys across examples."""

        class HeterogeneousAdapter(MockAdapter):
            async def evaluate(
                self,
                batch: list[Any],
                candidate: dict[str, str],
                capture_traces: bool = False,
            ) -> EvaluationBatch:
                score = next(self._scores, 0.5)
                # Different examples have different objective keys
                objective_scores = [
                    {"accuracy": 0.9, "latency": 0.8},  # Example 0
                    {"cost": 0.7, "quality": 0.95},  # Example 1 (if batch has 2)
                ]
                return EvaluationBatch(
                    outputs=[None] * len(batch),
                    scores=[score] * len(batch),
                    trajectories=[{}] * len(batch) if capture_traces else None,
                    objective_scores=objective_scores[: len(batch)],
                )

        # Use a batch with 2 examples to test heterogeneity
        batch = [
            {"input": "Hello", "expected": "Hi"},
            {"input": "Bye", "expected": "Goodbye"},
        ]
        adapter = HeterogeneousAdapter(scores=[0.5, 0.5])
        config = EvolutionConfig(max_iterations=0)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=batch,
        )

        result = await engine.run()

        assert result.objective_scores is not None
        assert len(result.objective_scores) == 2
        assert "accuracy" in result.objective_scores[0]
        assert "cost" in result.objective_scores[1]
