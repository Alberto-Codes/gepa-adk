"""Unit tests for evaluation policy implementations.

Tests verify the business logic of FullEvaluationPolicy and SubsetEvaluationPolicy
implementations.
"""

from __future__ import annotations

import pytest

from gepa_adk.adapters.evaluation_policy import (
    FullEvaluationPolicy,
    SubsetEvaluationPolicy,
)
from gepa_adk.domain.exceptions import NoCandidateAvailableError
from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState

pytestmark = pytest.mark.unit


class TestFullEvaluationPolicy:
    """Tests for FullEvaluationPolicy (T019-T021)."""

    @pytest.fixture
    def policy(self) -> FullEvaluationPolicy:
        """Create FullEvaluationPolicy instance."""
        return FullEvaluationPolicy()

    @pytest.fixture
    def state_with_scores(self) -> ParetoState:
        """Create state with candidates and scores."""
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "a"}), [0.8, 0.6, 0.7])
        state.add_candidate(Candidate(components={"instruction": "b"}), [0.9, 0.5, 0.8])
        return state

    def test_get_eval_batch_returns_all_ids(
        self, policy: FullEvaluationPolicy, state_with_scores: ParetoState
    ) -> None:
        """T019: get_eval_batch returns all valset IDs."""
        valset_ids = [0, 1, 2, 3, 4]
        result = policy.get_eval_batch(valset_ids, state_with_scores)
        assert result == [0, 1, 2, 3, 4]
        assert len(result) == len(valset_ids)

    def test_get_best_candidate_returns_highest_average(
        self, policy: FullEvaluationPolicy, state_with_scores: ParetoState
    ) -> None:
        """T020: get_best_candidate returns candidate with highest average score."""
        # Candidate 0: (0.8 + 0.6 + 0.7) / 3 = 0.7
        # Candidate 1: (0.9 + 0.5 + 0.8) / 3 = 0.733...
        result = policy.get_best_candidate(state_with_scores)
        assert result == 1  # Candidate 1 has higher average

    def test_get_valset_score_calculation(
        self, policy: FullEvaluationPolicy, state_with_scores: ParetoState
    ) -> None:
        """T021: get_valset_score returns mean of candidate scores."""
        score_0 = policy.get_valset_score(0, state_with_scores)
        score_1 = policy.get_valset_score(1, state_with_scores)

        assert score_0 == pytest.approx(0.7)  # (0.8 + 0.6 + 0.7) / 3
        assert score_1 == pytest.approx(0.7333333333333334)  # (0.9 + 0.5 + 0.8) / 3

    def test_get_valset_score_returns_neg_inf_for_unscored(
        self, policy: FullEvaluationPolicy
    ) -> None:
        """get_valset_score returns -inf for candidate with no scores."""
        state = ParetoState()
        state.candidates.append(Candidate(components={"instruction": "test"}))
        score = policy.get_valset_score(0, state)
        assert score == float("-inf")

    def test_get_best_candidate_raises_for_empty_state(
        self, policy: FullEvaluationPolicy
    ) -> None:
        """get_best_candidate raises NoCandidateAvailableError for empty state."""
        state = ParetoState()
        with pytest.raises(NoCandidateAvailableError):
            policy.get_best_candidate(state)


class TestSubsetEvaluationPolicy:
    """Tests for SubsetEvaluationPolicy (T043-T046)."""

    def test_get_eval_batch_returns_subset(self) -> None:
        """T043: get_eval_batch returns subset of valset IDs."""
        policy = SubsetEvaluationPolicy(subset_size=0.2)
        valset_ids = list(range(10))  # [0, 1, 2, ..., 9]
        state = ParetoState()

        result = policy.get_eval_batch(valset_ids, state)
        assert len(result) == 2  # 20% of 10 = 2
        assert all(idx in valset_ids for idx in result)

    def test_round_robin_offset_advancement(self) -> None:
        """T044: round-robin offset advances across iterations."""
        policy = SubsetEvaluationPolicy(subset_size=0.2)
        valset_ids = list(range(10))
        state = ParetoState()

        batch1 = policy.get_eval_batch(valset_ids, state)
        batch2 = policy.get_eval_batch(valset_ids, state)
        batch3 = policy.get_eval_batch(valset_ids, state)

        # Each batch should start at different offset
        assert batch1[0] != batch2[0] or batch2[0] != batch3[0]

    def test_subset_size_as_int_vs_float(self) -> None:
        """T045: subset_size handles both int and float values."""
        valset_ids = list(range(10))
        state = ParetoState()

        # Float: fraction of total
        policy_float = SubsetEvaluationPolicy(subset_size=0.3)
        result_float = policy_float.get_eval_batch(valset_ids, state)
        assert len(result_float) == 3  # 30% of 10 = 3

        # Int: absolute count
        policy_int = SubsetEvaluationPolicy(subset_size=5)
        result_int = policy_int.get_eval_batch(valset_ids, state)
        assert len(result_int) == 5

    def test_subset_size_exceeding_valset_falls_back(self) -> None:
        """T046: subset_size exceeding valset size falls back to full evaluation."""
        policy = SubsetEvaluationPolicy(subset_size=15)  # More than valset size
        valset_ids = list(range(10))
        state = ParetoState()

        result = policy.get_eval_batch(valset_ids, state)
        # Should return all IDs when subset_size > valset_size
        assert len(result) == len(valset_ids)
        assert set(result) == set(valset_ids)
