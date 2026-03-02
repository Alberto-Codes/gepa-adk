"""Evaluation policy implementations for valset evaluation strategies.

This module provides implementations of EvaluationPolicyProtocol for selecting
which validation examples to evaluate per iteration and how to identify the
best candidate based on evaluation results.

Attributes:
    FullEvaluationPolicy (class): Scores all validation examples every iteration.
    SubsetEvaluationPolicy (class): Scores a configurable subset with round-robin
        coverage across iterations.

Examples:
    Select all examples with the default policy:

    ```python
    from gepa_adk.adapters.evaluation_policy import FullEvaluationPolicy

    policy = FullEvaluationPolicy()
    batch = policy.get_eval_batch([0, 1, 2], state)
    ```

    Use subset evaluation for large valsets:

    ```python
    from gepa_adk.adapters.evaluation_policy import SubsetEvaluationPolicy

    policy = SubsetEvaluationPolicy(subset_size=0.2)
    batch = policy.get_eval_batch(list(range(100)), state)
    ```

See Also:
    - [`EvaluationPolicyProtocol`][gepa_adk.ports.evaluation_policy.EvaluationPolicyProtocol]
      for the protocol contract.

Note:
    These policies provide strategies for selecting validation examples to
    evaluate per iteration. FullEvaluationPolicy scores all examples,
    while SubsetEvaluationPolicy scores a configurable subset with round-robin
    coverage to ensure all examples are eventually evaluated.
"""

from __future__ import annotations

from statistics import fmean
from typing import Sequence

from gepa_adk.domain.exceptions import NoCandidateAvailableError
from gepa_adk.domain.state import ParetoState

__all__ = [
    "FullEvaluationPolicy",
    "SubsetEvaluationPolicy",
]


class FullEvaluationPolicy:
    """Evaluation policy that scores all validation examples every iteration.

    This is the default evaluation policy, providing complete visibility
    into solution performance across all validation examples.

    Note:
        Always returns all valset IDs, ensuring complete evaluation coverage
        each iteration.

    Examples:
        ```python
        policy = FullEvaluationPolicy()
        batch = policy.get_eval_batch([0, 1, 2, 3, 4], state)
        # Returns: [0, 1, 2, 3, 4]
        ```
    """

    def get_eval_batch(
        self,
        valset_ids: Sequence[int],
        state: ParetoState,
        target_candidate_idx: int | None = None,
    ) -> list[int]:
        """Return all validation example indices.

        Args:
            valset_ids (Sequence[int]): All available validation example indices.
            state (ParetoState): Current evolution state (unused for full evaluation).
            target_candidate_idx (int | None): Optional candidate being evaluated
                (unused).

        Returns:
            list[int]: List of all valset_ids.

        Note:
            Outputs the complete valset for comprehensive evaluation coverage.

        Examples:
            ```python
            policy = FullEvaluationPolicy()
            batch = policy.get_eval_batch([0, 1, 2], state)
            assert batch == [0, 1, 2]
            ```
        """
        return list(valset_ids)

    def get_best_candidate(self, state: ParetoState) -> int:
        """Return index of candidate with highest average score.

        Args:
            state: Current evolution state with candidate scores.

        Returns:
            Index of best performing candidate.

        Raises:
            NoCandidateAvailableError: If state has no candidates.

        Note:
            Outputs the candidate index with the highest mean score across
            all evaluated examples.

        Examples:
            ```python
            policy = FullEvaluationPolicy()
            best_idx = policy.get_best_candidate(state)
            ```
        """
        if not state.candidates:
            raise NoCandidateAvailableError("No candidates available")

        best_idx = None
        best_score = float("-inf")
        for candidate_idx in range(len(state.candidates)):
            score = self.get_valset_score(candidate_idx, state)
            if score > best_score:
                best_score = score
                best_idx = candidate_idx

        if best_idx is None:
            raise NoCandidateAvailableError("No scored candidates available")
        return best_idx

    def get_valset_score(self, candidate_idx: int, state: ParetoState) -> float:
        """Return mean score across all evaluated examples for a candidate.

        Args:
            candidate_idx (int): Index of candidate to score.
            state (ParetoState): Current evolution state.

        Returns:
            float: Mean score across all examples, or float('-inf') if no scores.

        Note:
            Outputs the arithmetic mean of all scores for the candidate,
            or negative infinity if no scores exist.

        Examples:
            ```python
            policy = FullEvaluationPolicy()
            score = policy.get_valset_score(0, state)
            ```
        """
        scores = state.candidate_scores.get(candidate_idx)
        if not scores:
            return float("-inf")
        return fmean(scores.values())


class SubsetEvaluationPolicy:
    """Evaluation policy that scores a configurable subset with round-robin coverage.

    This policy reduces evaluation cost for large validation sets by evaluating
    only a subset of examples per iteration, using round-robin selection to
    ensure all examples are eventually covered.

    Attributes:
        subset_size (int | float): If int, absolute count of examples to evaluate
            per iteration. If float (0.0-1.0), fraction of total valset size.
        _offset (int): Internal state tracking current position for round-robin
            selection.

    Note:
        Advances offset each iteration to provide round-robin coverage across
        the full valset over multiple iterations.

    Examples:
        ```python
        # Evaluate 20% of valset per iteration
        policy = SubsetEvaluationPolicy(subset_size=0.2)

        # Evaluate exactly 5 examples per iteration
        policy = SubsetEvaluationPolicy(subset_size=5)
        ```
    """

    def __init__(self, subset_size: int | float = 0.2) -> None:
        """Initialize subset evaluation policy.

        Args:
            subset_size: If int, evaluate this many examples per iteration.
                If float, evaluate this fraction of total valset.
                Default: 0.2 (20% of valset per iteration).

        Note:
            Creates policy with initial offset of 0 for round-robin selection.
        """
        self.subset_size = subset_size
        self._offset = 0

    def get_eval_batch(
        self,
        valset_ids: Sequence[int],
        state: ParetoState,
        target_candidate_idx: int | None = None,
    ) -> list[int]:
        """Return subset of validation example indices with round-robin selection.

        Args:
            valset_ids: All available validation example indices.
            state: Current evolution state (unused for subset selection).
            target_candidate_idx: Optional candidate being evaluated (unused).

        Returns:
            List of example indices to evaluate this iteration.
            Uses round-robin to ensure all examples are eventually covered.

        Raises:
            ValueError: If subset_size is outside the allowed range.

        Note:
            Outputs a subset of valset IDs starting at the current offset,
            wrapping around if needed to provide round-robin coverage.

        Examples:
            ```python
            policy = SubsetEvaluationPolicy(subset_size=0.25)
            batch = policy.get_eval_batch(list(range(8)), state)
            assert len(batch) == 2
            ```
        """
        if not valset_ids:
            return []

        total_size = len(valset_ids)

        # Calculate subset count
        if isinstance(self.subset_size, float):
            if not (0.0 < self.subset_size <= 1.0):
                raise ValueError(
                    f"subset_size float must be in (0.0, 1.0], got {self.subset_size}"
                )
            subset_count = max(1, int(self.subset_size * total_size))
        else:
            subset_count = self.subset_size

        # Fallback to full evaluation if subset_size exceeds valset size
        if subset_count >= total_size:
            return list(valset_ids)

        # Round-robin selection: slice starting at _offset, wrapping around
        result: list[int] = []
        for i in range(subset_count):
            idx = (self._offset + i) % total_size
            result.append(valset_ids[idx])

        # Advance offset for next iteration
        self._offset = (self._offset + subset_count) % total_size

        return result

    def get_best_candidate(self, state: ParetoState) -> int:
        """Return index of candidate with highest average score.

        Args:
            state (ParetoState): Current evolution state with candidate scores.

        Returns:
            int: Index of best performing candidate.

        Raises:
            NoCandidateAvailableError: If state has no candidates.

        Note:
            Outputs the candidate index with the highest mean score across
            evaluated examples, consistent with FullEvaluationPolicy behavior.

        Examples:
            ```python
            policy = SubsetEvaluationPolicy()
            best_idx = policy.get_best_candidate(state)
            ```
        """
        if not state.candidates:
            raise NoCandidateAvailableError("No candidates available")

        best_idx = None
        best_score = float("-inf")
        for candidate_idx in range(len(state.candidates)):
            score = self.get_valset_score(candidate_idx, state)
            if score > best_score:
                best_score = score
                best_idx = candidate_idx

        if best_idx is None:
            raise NoCandidateAvailableError("No scored candidates available")
        return best_idx

    def get_valset_score(self, candidate_idx: int, state: ParetoState) -> float:
        """Return mean score across evaluated examples for a candidate.

        Args:
            candidate_idx (int): Index of candidate to score.
            state (ParetoState): Current evolution state.

        Returns:
            float: Mean score across evaluated examples, or float('-inf') if no scores.

        Note:
            Outputs the arithmetic mean of scores for the candidate across
            only the examples that were actually evaluated (subset).

        Examples:
            ```python
            policy = SubsetEvaluationPolicy()
            score = policy.get_valset_score(0, state)
            ```
        """
        scores = state.candidate_scores.get(candidate_idx)
        if not scores:
            return float("-inf")
        return fmean(scores.values())
