"""Unit tests for frontier type implementations.

Tests verify objective-level, hybrid, and cartesian frontier tracking
functionality across different frontier types.

Note:
    Following TDD approach - tests written before implementation.
"""

from __future__ import annotations

import pytest

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoFrontier, ParetoState
from gepa_adk.domain.types import FrontierType

pytestmark = pytest.mark.unit


class TestUpdateObjective:
    """Tests for update_objective method (T009)."""

    def test_update_objective_sets_new_leader(self) -> None:
        """update_objective sets candidate as leader when score is higher."""
        frontier = ParetoFrontier()
        objective_scores = {"accuracy": 0.9, "latency": 0.7}

        frontier.update_objective(0, objective_scores)

        assert frontier.objective_leaders["accuracy"] == {0}
        assert frontier.objective_leaders["latency"] == {0}
        assert frontier.objective_best_scores["accuracy"] == 0.9
        assert frontier.objective_best_scores["latency"] == 0.7

    def test_update_objective_adds_tied_candidate(self) -> None:
        """update_objective adds candidate to leaders when score equals best."""
        frontier = ParetoFrontier()
        frontier.update_objective(0, {"accuracy": 0.8})
        frontier.update_objective(1, {"accuracy": 0.8})

        assert frontier.objective_leaders["accuracy"] == {0, 1}
        assert frontier.objective_best_scores["accuracy"] == 0.8

    def test_update_objective_ignores_lower_scores(self) -> None:
        """update_objective does not update when score is lower."""
        frontier = ParetoFrontier()
        frontier.update_objective(0, {"accuracy": 0.9})
        frontier.update_objective(1, {"accuracy": 0.7})

        assert frontier.objective_leaders["accuracy"] == {0}
        assert 1 not in frontier.objective_leaders["accuracy"]


class TestObjectiveFrontierDominance:
    """Tests for objective frontier dominance logic (T010)."""

    def test_objective_dominance_excludes_dominated(self) -> None:
        """Objective-level dominance excludes candidates dominated across all objectives."""
        frontier = ParetoFrontier()
        frontier.update_objective(0, {"accuracy": 0.9, "latency": 0.8})
        frontier.update_objective(1, {"accuracy": 0.7, "latency": 0.6})

        # Candidate 0 dominates candidate 1 on both objectives
        assert 0 in frontier.objective_leaders["accuracy"]
        assert 0 in frontier.objective_leaders["latency"]
        # Candidate 1 should not be in leaders if dominated
        assert 1 not in frontier.objective_leaders.get("accuracy", set())
        assert 1 not in frontier.objective_leaders.get("latency", set())

    def test_non_dominated_objectives_both_remain(self) -> None:
        """Non-dominated candidates remain on frontier for respective objectives."""
        frontier = ParetoFrontier()
        frontier.update_objective(0, {"accuracy": 0.9, "latency": 0.5})
        frontier.update_objective(1, {"accuracy": 0.6, "latency": 0.9})

        # Candidate 0 leads accuracy, candidate 1 leads latency
        assert 0 in frontier.objective_leaders["accuracy"]
        assert 1 in frontier.objective_leaders["latency"]


class TestObjectiveScoresValidation:
    """Tests for objective_scores validation (T011)."""

    def test_objective_frontier_requires_objective_scores(self) -> None:
        """OBJECTIVE frontier type requires objective_scores parameter."""
        state = ParetoState(frontier_type=FrontierType.OBJECTIVE)
        candidate = Candidate(components={"instruction": "test"})

        with pytest.raises(ConfigurationError) as exc_info:
            state.add_candidate(candidate, [0.8, 0.6])

        assert "objective_scores" in str(exc_info.value).lower()

    def test_hybrid_frontier_requires_objective_scores(self) -> None:
        """HYBRID frontier type requires objective_scores parameter."""
        state = ParetoState(frontier_type=FrontierType.HYBRID)
        candidate = Candidate(components={"instruction": "test"})

        with pytest.raises(ConfigurationError) as exc_info:
            state.add_candidate(candidate, [0.8, 0.6])

        assert "objective_scores" in str(exc_info.value).lower()

    def test_cartesian_frontier_requires_objective_scores(self) -> None:
        """CARTESIAN frontier type requires objective_scores parameter."""
        state = ParetoState(frontier_type=FrontierType.CARTESIAN)
        candidate = Candidate(components={"instruction": "test"})

        with pytest.raises(ConfigurationError) as exc_info:
            state.add_candidate(candidate, [0.8, 0.6])

        assert "objective_scores" in str(exc_info.value).lower()

    def test_instance_frontier_accepts_scores_without_objective_scores(self) -> None:
        """INSTANCE frontier type works without objective_scores."""
        state = ParetoState(frontier_type=FrontierType.INSTANCE)
        candidate = Candidate(components={"instruction": "test"})

        # Should not raise
        state.add_candidate(candidate, [0.8, 0.6])

        assert len(state.candidates) == 1


class TestHybridFrontier:
    """Tests for hybrid frontier tracking (T029-T030)."""

    def test_hybrid_frontier_updates_both_structures(self) -> None:
        """T029: Hybrid frontier updates both instance and objective structures."""
        state = ParetoState(frontier_type=FrontierType.HYBRID)
        candidate = Candidate(components={"instruction": "test"})

        state.add_candidate(
            candidate,
            [0.8, 0.6],
            objective_scores={"accuracy": 0.9, "latency": 0.7},
        )

        # Check instance-level frontier
        assert 0 in state.frontier.example_leaders.get(0, set())
        assert state.frontier.best_scores[0] == 0.8

        # Check objective-level frontier
        assert 0 in state.frontier.objective_leaders.get("accuracy", set())
        assert state.frontier.objective_best_scores["accuracy"] == 0.9
        assert 0 in state.frontier.objective_leaders.get("latency", set())
        assert state.frontier.objective_best_scores["latency"] == 0.7

    def test_get_pareto_front_mapping_returns_combined_mapping(self) -> None:
        """T030: get_pareto_front_mapping returns combined mapping for HYBRID."""
        frontier = ParetoFrontier()
        frontier.update(0, {0: 0.8, 1: 0.6})
        frontier.update_objective(1, {"accuracy": 0.9, "latency": 0.7})

        mapping = frontier.get_pareto_front_mapping(FrontierType.HYBRID)

        # Check instance-level entries with type tag
        assert ("val_id", 0) in mapping
        assert 0 in mapping[("val_id", 0)]
        assert ("val_id", 1) in mapping
        assert 0 in mapping[("val_id", 1)]

        # Check objective-level entries with type tag
        assert ("objective", "accuracy") in mapping
        assert 1 in mapping[("objective", "accuracy")]
        assert ("objective", "latency") in mapping
        assert 1 in mapping[("objective", "latency")]


class TestCartesianFrontier:
    """Tests for cartesian frontier tracking (T034-T036)."""

    def test_update_cartesian_method(self) -> None:
        """T034: update_cartesian method updates per (example, objective) pairs."""
        frontier = ParetoFrontier()
        scores = {0: 0.8, 1: 0.6}
        per_example_objective_scores = {
            0: {"accuracy": 0.9, "latency": 0.7},
            1: {"accuracy": 0.8, "latency": 0.9},
        }

        frontier.update_cartesian(0, scores, per_example_objective_scores)

        # Check cartesian leaders
        assert 0 in frontier.cartesian_leaders.get((0, "accuracy"), set())
        assert frontier.cartesian_best_scores[(0, "accuracy")] == 0.9
        assert 0 in frontier.cartesian_leaders.get((0, "latency"), set())
        assert frontier.cartesian_best_scores[(0, "latency")] == 0.7
        assert 0 in frontier.cartesian_leaders.get((1, "accuracy"), set())
        assert frontier.cartesian_best_scores[(1, "accuracy")] == 0.8
        assert 0 in frontier.cartesian_leaders.get((1, "latency"), set())
        assert frontier.cartesian_best_scores[(1, "latency")] == 0.9

    def test_cartesian_key_structure(self) -> None:
        """T035: cartesian key structure is (example_idx, objective_name)."""
        frontier = ParetoFrontier()
        per_example_objective_scores = {0: {"accuracy": 0.9}}

        frontier.update_cartesian(0, {0: 0.8}, per_example_objective_scores)

        # Verify key structure
        assert (0, "accuracy") in frontier.cartesian_leaders
        assert (0, "accuracy") in frontier.cartesian_best_scores

    def test_get_pareto_front_mapping_cartesian_type(self) -> None:
        """T036: get_pareto_front_mapping returns cartesian mapping with type tags."""
        frontier = ParetoFrontier()
        per_example_objective_scores = {
            0: {"accuracy": 0.9},
            1: {"latency": 0.8},
        }
        frontier.update_cartesian(0, {0: 0.8, 1: 0.6}, per_example_objective_scores)

        mapping = frontier.get_pareto_front_mapping(FrontierType.CARTESIAN)

        # Check cartesian entries with type tag
        assert ("cartesian", 0, "accuracy") in mapping
        assert 0 in mapping[("cartesian", 0, "accuracy")]
        assert ("cartesian", 1, "latency") in mapping
        assert 0 in mapping[("cartesian", 1, "latency")]
