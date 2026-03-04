"""Contract tests for objective_scores in domain models.

Note:
    Tests verify that IterationRecord and EvolutionResult correctly
    support optional objective_scores fields per the contract specification.
"""

from __future__ import annotations

import pytest

from gepa_adk.domain.models import EvolutionResult, IterationRecord

pytestmark = pytest.mark.contract


class TestIterationRecordObjectiveScores:
    """Contract tests for IterationRecord with objective_scores."""

    def test_iteration_record_with_objective_scores(self) -> None:
        """IterationRecord stores objective_scores when provided."""
        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
            objective_scores=[{"accuracy": 0.9, "latency": 0.8}],
        )
        assert record.objective_scores == [{"accuracy": 0.9, "latency": 0.8}]

    def test_iteration_record_without_objective_scores(self) -> None:
        """IterationRecord defaults objective_scores to None."""
        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
        )
        assert record.objective_scores is None

    def test_iteration_record_with_multiple_examples(self) -> None:
        """IterationRecord supports multiple examples in objective_scores."""
        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
            objective_scores=[
                {"accuracy": 0.9, "latency": 0.8},
                {"accuracy": 0.88, "latency": 0.92},
                {"accuracy": 0.91, "latency": 0.85},
            ],
        )
        assert record.objective_scores is not None
        assert len(record.objective_scores) == 3
        assert record.objective_scores[0]["accuracy"] == 0.9
        assert record.objective_scores[1]["latency"] == 0.92


class TestEvolutionResultObjectiveScores:
    """Contract tests for EvolutionResult with objective_scores."""

    def test_evolution_result_with_objective_scores(self) -> None:
        """EvolutionResult includes objective_scores from best candidate."""
        result = EvolutionResult(
            original_score=0.6,
            final_score=0.85,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[],
            total_iterations=10,
            objective_scores=[{"accuracy": 0.95}],
        )
        assert result.objective_scores == [{"accuracy": 0.95}]

    def test_evolution_result_without_objective_scores(self) -> None:
        """EvolutionResult defaults objective_scores to None."""
        result = EvolutionResult(
            original_score=0.6,
            final_score=0.85,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[],
            total_iterations=10,
        )
        assert result.objective_scores is None

    def test_evolution_result_backward_compatible(self) -> None:
        """Creating EvolutionResult without objective_scores works."""
        result = EvolutionResult(
            original_score=0.6,
            final_score=0.85,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[],
            total_iterations=10,
        )
        # Old code accessing existing fields works
        assert result.final_score == 0.85
        assert result.improvement == 0.25
        assert result.schema_version == 1

    def test_iteration_record_backward_compatible(self) -> None:
        """Creating IterationRecord without objective_scores works."""
        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
        )
        # Old code accessing existing fields works
        assert record.iteration_number == 1
        assert record.score == 0.85
