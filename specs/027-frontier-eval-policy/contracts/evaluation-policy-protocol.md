# Contract: EvaluationPolicyProtocol

**Feature**: 027-frontier-eval-policy
**Date**: 2026-01-15

## Protocol Definition

```python
from typing import Protocol, Sequence, runtime_checkable
from gepa_adk.domain.state import ParetoState

@runtime_checkable
class EvaluationPolicyProtocol(Protocol):
    """Protocol for valset evaluation strategies.

    Determines which validation examples to evaluate per iteration
    and how to identify the best candidate based on evaluation results.
    """

    def get_eval_batch(
        self,
        valset_ids: Sequence[int],
        state: ParetoState,
        target_candidate_idx: int | None = None,
    ) -> list[int]:
        """Select validation example indices to evaluate.

        Args:
            valset_ids: All available validation example indices (0 to N-1).
            state: Current evolution state with candidate scores.
            target_candidate_idx: Optional candidate being evaluated (for adaptive policies).

        Returns:
            List of example indices to evaluate this iteration.
            Must be a subset of valset_ids (or equal).

        Contract:
            - MUST return non-empty list when valset_ids is non-empty
            - MUST only return indices present in valset_ids
            - MAY return all indices (full evaluation)
            - MAY return subset (partial evaluation)
        """
        ...

    def get_best_candidate(self, state: ParetoState) -> int:
        """Return index of best candidate based on evaluation results.

        Args:
            state: Current evolution state with candidate_scores populated.

        Returns:
            Index of best performing candidate.

        Raises:
            NoCandidateAvailableError: If state has no candidates.

        Contract:
            - MUST return valid index into state.candidates
            - MUST raise NoCandidateAvailableError if len(state.candidates) == 0
            - MAY use different scoring strategies (average, weighted, etc.)
        """
        ...

    def get_valset_score(self, candidate_idx: int, state: ParetoState) -> float:
        """Return aggregated valset score for a candidate.

        Args:
            candidate_idx: Index of candidate to score.
            state: Current evolution state.

        Returns:
            Aggregated score (typically mean across evaluated examples).
            Returns float('-inf') if candidate has no evaluated scores.

        Contract:
            - MUST return finite float (not NaN)
            - MUST return float('-inf') for candidates with no scores
            - MUST be consistent with get_best_candidate() ranking
        """
        ...
```

---

## Contract Test Cases

### CT-001: get_eval_batch returns non-empty for non-empty valset

```gherkin
Given a policy implementation
And valset_ids = [0, 1, 2, 3, 4]
And state has at least one candidate
When get_eval_batch(valset_ids, state) is called
Then result is non-empty list
And all indices in result are in valset_ids
```

### CT-002: get_eval_batch handles empty valset

```gherkin
Given a policy implementation
And valset_ids = []
When get_eval_batch(valset_ids, state) is called
Then result is empty list
```

### CT-003: get_best_candidate returns valid index

```gherkin
Given a policy implementation
And state has 3 candidates with scores
When get_best_candidate(state) is called
Then result is integer in range [0, 2]
```

### CT-004: get_best_candidate raises for empty state

```gherkin
Given a policy implementation
And state has 0 candidates
When get_best_candidate(state) is called
Then NoCandidateAvailableError is raised
```

### CT-005: get_valset_score returns finite float

```gherkin
Given a policy implementation
And state has candidate 0 with scores {0: 0.8, 1: 0.6}
When get_valset_score(0, state) is called
Then result is finite float (not NaN, not inf)
```

### CT-006: get_valset_score returns -inf for unscored candidate

```gherkin
Given a policy implementation
And state has candidate 0 with no scores (empty dict)
When get_valset_score(0, state) is called
Then result is float('-inf')
```

---

## Implementation Requirements

### FullEvaluationPolicy

| Method | Behavior |
|--------|----------|
| `get_eval_batch` | Return `list(valset_ids)` (all examples) |
| `get_best_candidate` | Return `argmax(mean(scores) for each candidate)` |
| `get_valset_score` | Return `mean(state.candidate_scores[candidate_idx].values())` |

### SubsetEvaluationPolicy

| Method | Behavior |
|--------|----------|
| `get_eval_batch` | Return slice of size `subset_size` with round-robin offset |
| `get_best_candidate` | Return `argmax(mean(scores) for each candidate)` |
| `get_valset_score` | Return `mean(state.candidate_scores[candidate_idx].values())` |

---

## Protocol Compliance Test Template

```python
import pytest
from gepa_adk.ports.selector import EvaluationPolicyProtocol
from gepa_adk.domain.state import ParetoState
from gepa_adk.domain.exceptions import NoCandidateAvailableError


class TestEvaluationPolicyProtocolCompliance:
    """Contract tests for EvaluationPolicyProtocol implementations."""

    @pytest.fixture
    def policy(self) -> EvaluationPolicyProtocol:
        """Override in subclass to provide implementation under test."""
        raise NotImplementedError

    @pytest.fixture
    def state_with_candidates(self) -> ParetoState:
        """State with 3 candidates and scores."""
        state = ParetoState()
        # Add candidates via add_candidate()
        return state

    @pytest.fixture
    def empty_state(self) -> ParetoState:
        """State with no candidates."""
        return ParetoState()

    def test_get_eval_batch_returns_nonempty_for_nonempty_valset(
        self, policy: EvaluationPolicyProtocol, state_with_candidates: ParetoState
    ):
        """CT-001: get_eval_batch returns non-empty for non-empty valset."""
        valset_ids = [0, 1, 2, 3, 4]
        result = policy.get_eval_batch(valset_ids, state_with_candidates)
        assert len(result) > 0
        assert all(idx in valset_ids for idx in result)

    def test_get_eval_batch_returns_empty_for_empty_valset(
        self, policy: EvaluationPolicyProtocol, state_with_candidates: ParetoState
    ):
        """CT-002: get_eval_batch handles empty valset."""
        result = policy.get_eval_batch([], state_with_candidates)
        assert result == []

    def test_get_best_candidate_returns_valid_index(
        self, policy: EvaluationPolicyProtocol, state_with_candidates: ParetoState
    ):
        """CT-003: get_best_candidate returns valid index."""
        result = policy.get_best_candidate(state_with_candidates)
        assert 0 <= result < len(state_with_candidates.candidates)

    def test_get_best_candidate_raises_for_empty_state(
        self, policy: EvaluationPolicyProtocol, empty_state: ParetoState
    ):
        """CT-004: get_best_candidate raises for empty state."""
        with pytest.raises(NoCandidateAvailableError):
            policy.get_best_candidate(empty_state)

    def test_get_valset_score_returns_finite_float(
        self, policy: EvaluationPolicyProtocol, state_with_candidates: ParetoState
    ):
        """CT-005: get_valset_score returns finite float."""
        import math
        result = policy.get_valset_score(0, state_with_candidates)
        assert isinstance(result, float)
        assert math.isfinite(result)
```
