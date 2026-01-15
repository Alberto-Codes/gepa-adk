"""Protocol definition for candidate selection strategies.

Note:
    This module defines the async contract for candidate selection strategies
    and evaluation policies.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from gepa_adk.domain.state import ParetoState


@runtime_checkable
class CandidateSelectorProtocol(Protocol):
    """Async protocol for candidate selection strategies.

    Note:
        A selector protocol standardizes how candidates are chosen for mutation.

    Examples:
        ```python
        class Selector:
            async def select_candidate(self, state: ParetoState) -> int:
                return 0
        ```
    """

    async def select_candidate(self, state: ParetoState) -> int:
        """Select a candidate index for mutation.

        Args:
            state: Current evolution state with Pareto frontier tracking.

        Returns:
            Index of selected candidate.

        Raises:
            NoCandidateAvailableError: If state has no candidates.

        Examples:
            ```python
            candidate_idx = await selector.select_candidate(state)
            ```
        """
        ...


@runtime_checkable
class EvaluationPolicyProtocol(Protocol):
    """Protocol for valset evaluation strategies.

    Determines which validation examples to evaluate per iteration
    and how to identify the best candidate based on evaluation results.

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

        Examples:
            ```python
            score = policy.get_valset_score(0, state)
            ```
        """
        ...


@runtime_checkable
class ComponentSelectorProtocol(Protocol):
    """Async protocol for component selection strategies.

    Note:
        A selector protocol standardizes how components are chosen for update.

    Examples:
        ```python
        class MySelector:
            async def select_components(
                self, components: list[str], iteration: int, candidate_idx: int
            ) -> list[str]:
                return components[:1]
        ```
    """

    async def select_components(
        self, components: list[str], iteration: int, candidate_idx: int
    ) -> list[str]:
        """Select components to update for the current iteration.

        Args:
            components: List of available component keys (e.g. ["instruction", "input_schema"]).
            iteration: Current global iteration number (0-based).
            candidate_idx: Index of the candidate being evolved.

        Returns:
            List of component keys to update.

        Raises:
            ValueError: If components list is empty.

        Examples:
            ```python
            selected = await selector.select_components(
                components=["instruction", "schema"], iteration=1, candidate_idx=0
            )
            ```
        """
        ...
