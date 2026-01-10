"""Pytest fixtures for engine tests."""

from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch


class MockAdapter(AsyncGEPAAdapter[dict[str, str], dict[str, Any], None]):
    """Mock adapter for testing engine behavior."""

    def __init__(self, scores: list[float] | None = None) -> None:
        """Initialize mock adapter with predetermined scores.

        Args:
            scores: List of scores to return sequentially. If None, returns 0.5.
        """
        self._scores = iter(scores) if scores else iter([0.5])
        self._call_count = 0
        self._evaluate_calls: list[tuple[Any, dict[str, str], bool]] = []

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate candidate and return mock results.

        Args:
            batch: Input data instances.
            candidate: Candidate components.
            capture_traces: Whether to capture traces.

        Returns:
            Mock evaluation batch with predetermined scores.
        """
        self._call_count += 1
        self._evaluate_calls.append((batch, candidate, capture_traces))
        score = next(self._scores, 0.5)  # Default if exhausted
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
        """Build mock reflective dataset.

        Args:
            candidate: Current candidate components.
            eval_batch: Evaluation results.
            components_to_update: Components to generate datasets for.

        Returns:
            Mock reflective dataset.
        """
        return {comp: [] for comp in components_to_update}

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Generate mock text proposals.

        Args:
            candidate: Current candidate components.
            reflective_dataset: Reflective examples.
            components_to_update: Components to propose updates for.

        Returns:
            Mock proposals with improved text.
        """
        return {comp: f"Improved: {candidate[comp]}" for comp in components_to_update}


@pytest.fixture
def mock_adapter() -> MockAdapter:
    """Provide a mock adapter for tests."""
    return MockAdapter()


@pytest.fixture
def sample_config() -> EvolutionConfig:
    """Provide a sample evolution configuration."""
    return EvolutionConfig(max_iterations=50, patience=5)


@pytest.fixture
def sample_candidate() -> Candidate:
    """Provide a sample initial candidate."""
    return Candidate(components={"instruction": "Be helpful"}, generation=0)


@pytest.fixture
def sample_batch() -> list[dict[str, str]]:
    """Provide a sample evaluation batch."""
    return [{"input": "Hello", "expected": "Hi"}]
