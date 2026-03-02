"""Contract tests for EvaluationPolicyProtocol compliance.

Tests verify that all evaluation policy implementations correctly
adhere to the EvaluationPolicyProtocol contract.
"""

from __future__ import annotations

import math

import pytest

from gepa_adk.domain.exceptions import NoCandidateAvailableError
from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState
from gepa_adk.ports.evaluation_policy import EvaluationPolicyProtocol

pytestmark = pytest.mark.contract


def test_import_path_equivalence() -> None:
    """EvaluationPolicyProtocol is accessible from both import paths."""
    from gepa_adk.ports import EvaluationPolicyProtocol as from_init
    from gepa_adk.ports.evaluation_policy import EvaluationPolicyProtocol as from_module

    assert from_init is from_module


class TestEvaluationPolicyProtocolCompliance:
    """Contract tests for EvaluationPolicyProtocol implementations."""

    __test__ = False  # Prevent pytest from collecting the abstract base class.

    @pytest.fixture
    def policy(self) -> EvaluationPolicyProtocol:
        """Override in subclass to provide implementation under test."""
        raise NotImplementedError

    @pytest.fixture
    def state_with_candidates(self) -> ParetoState:
        """State with 3 candidates and scores."""
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "a"}), [0.8, 0.6, 0.7])
        state.add_candidate(Candidate(components={"instruction": "b"}), [0.9, 0.5, 0.8])
        state.add_candidate(Candidate(components={"instruction": "c"}), [0.7, 0.9, 0.6])
        return state

    @pytest.fixture
    def empty_state(self) -> ParetoState:
        """State with no candidates."""
        return ParetoState()

    def test_get_eval_batch_returns_nonempty_for_nonempty_valset(
        self, policy: EvaluationPolicyProtocol, state_with_candidates: ParetoState
    ) -> None:
        """CT-001: get_eval_batch returns non-empty for non-empty valset."""
        valset_ids = [0, 1, 2, 3, 4]
        result = policy.get_eval_batch(valset_ids, state_with_candidates)
        assert len(result) > 0
        assert all(idx in valset_ids for idx in result)

    def test_get_eval_batch_returns_empty_for_empty_valset(
        self, policy: EvaluationPolicyProtocol, state_with_candidates: ParetoState
    ) -> None:
        """CT-002: get_eval_batch handles empty valset."""
        result = policy.get_eval_batch([], state_with_candidates)
        assert result == []

    def test_get_best_candidate_returns_valid_index(
        self, policy: EvaluationPolicyProtocol, state_with_candidates: ParetoState
    ) -> None:
        """CT-003: get_best_candidate returns valid index."""
        result = policy.get_best_candidate(state_with_candidates)
        assert 0 <= result < len(state_with_candidates.candidates)

    def test_get_best_candidate_raises_for_empty_state(
        self, policy: EvaluationPolicyProtocol, empty_state: ParetoState
    ) -> None:
        """CT-004: get_best_candidate raises for empty state."""
        with pytest.raises(NoCandidateAvailableError):
            policy.get_best_candidate(empty_state)

    def test_get_valset_score_returns_finite_float(
        self, policy: EvaluationPolicyProtocol, state_with_candidates: ParetoState
    ) -> None:
        """CT-005: get_valset_score returns finite float."""
        result = policy.get_valset_score(0, state_with_candidates)
        assert isinstance(result, float)
        assert math.isfinite(result)

    def test_get_valset_score_returns_neg_inf_for_unscored_candidate(
        self, policy: EvaluationPolicyProtocol, state_with_candidates: ParetoState
    ) -> None:
        """CT-006: get_valset_score returns -inf for unscored candidate."""
        # Create state with candidate but no scores
        state = ParetoState()
        state.candidates.append(Candidate(components={"instruction": "test"}))
        result = policy.get_valset_score(0, state)
        assert result == float("-inf")


class TestFullEvaluationPolicyCompliance(TestEvaluationPolicyProtocolCompliance):
    """Contract tests for FullEvaluationPolicy (T018)."""

    @pytest.fixture
    def policy(self) -> EvaluationPolicyProtocol:
        """Provide FullEvaluationPolicy implementation."""
        from gepa_adk.adapters.evaluation_policy import FullEvaluationPolicy

        return FullEvaluationPolicy()


class TestSubsetEvaluationPolicyCompliance(TestEvaluationPolicyProtocolCompliance):
    """Contract tests for SubsetEvaluationPolicy (T042)."""

    @pytest.fixture
    def policy(self) -> EvaluationPolicyProtocol:
        """Provide SubsetEvaluationPolicy implementation."""
        from gepa_adk.adapters.evaluation_policy import SubsetEvaluationPolicy

        return SubsetEvaluationPolicy(subset_size=0.2)
