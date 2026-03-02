"""Protocol definition for valset evaluation strategies.

Attributes:
    EvaluationPolicyProtocol: Protocol for valset evaluation strategies.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from gepa_adk.domain.state import ParetoState


@runtime_checkable
class EvaluationPolicyProtocol(Protocol):
    """Protocol for valset evaluation strategies.

    Determines which validation examples to evaluate per iteration
    and how to identify the best candidate based on evaluation results.

    Note:
        Adapters implementing this protocol control evaluation cost and
        candidate selection strategies for scalable evolution runs.

    Examples:
        ```python
        class MyPolicy:
            def get_eval_batch(
                self, valset_ids: Sequence[int], state: ParetoState
            ) -> list[int]:
                return list(valset_ids)

            def get_best_candidate(self, state: ParetoState) -> int:
                return 0

            def get_valset_score(self, candidate_idx: int, state: ParetoState) -> float:
                return 0.5
        ```
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

        Note:
            Outputs a list of valset indices to evaluate, which may be a subset
            or the full valset depending on the policy implementation.

        Examples:
            ```python
            batch = policy.get_eval_batch([0, 1, 2, 3, 4], state)
            # Returns: [0, 1, 2, 3, 4] for full evaluation
            ```
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

        Note:
            Outputs the index of the best candidate based on the policy's
            scoring strategy (e.g., highest average score).

        Examples:
            ```python
            best_idx = policy.get_best_candidate(state)
            ```
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

        Note:
            Outputs an aggregated score for the candidate, typically the mean
            across evaluated examples, or negative infinity if no scores exist.

        Examples:
            ```python
            score = policy.get_valset_score(0, state)
            ```
        """
        ...


__all__ = ["EvaluationPolicyProtocol"]
