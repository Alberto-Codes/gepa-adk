"""Default implementations of the selection ports.

This module provides the default component selector and evaluation policy
beside the protocols they implement. They live in `ports` so that both the
engine, which falls back on them when no strategy is passed, and the adapter
selection modules, which re-export them, may import them under ADR-000.

Attributes:
    RoundRobinComponentSelector (class): Default ComponentSelectorProtocol
        implementation; cycles through components sequentially.
    FullEvaluationPolicy (class): Default EvaluationPolicyProtocol
        implementation; scores all validation examples every iteration.

Examples:
    Use the defaults directly:

    ```python
    from gepa_adk.ports.defaults import (
        FullEvaluationPolicy,
        RoundRobinComponentSelector,
    )

    selector = RoundRobinComponentSelector()
    components = await selector.select_components(["a", "b"], 1, 0)
    policy = FullEvaluationPolicy()
    batch = policy.get_eval_batch([0, 1, 2], state)
    ```

See Also:
    - [`ComponentSelectorProtocol`][gepa_adk.ports.component_selector.ComponentSelectorProtocol]:
      Port protocol the round-robin selector implements.
    - [`EvaluationPolicyProtocol`][gepa_adk.ports.evaluation_policy.EvaluationPolicyProtocol]:
      Port protocol the full evaluation policy implements.
    - [`AsyncGEPAEngine`][gepa_adk.engine.async_engine.AsyncGEPAEngine]: Engine
      that uses these classes when no selector or policy is passed.
    - [`gepa_adk.adapters`][gepa_adk.adapters]: Adapter layer whose selection
      package re-exports these defaults beside the other strategies.

Notes:
    These classes depend only on the standard library and the domain layer,
    so they satisfy both the import-linter layers contract and the ADR-000
    boundary script without an exception.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from statistics import fmean

from gepa_adk.domain.exceptions import NoCandidateAvailableError
from gepa_adk.domain.state import ParetoState

__all__ = [
    "FullEvaluationPolicy",
    "RoundRobinComponentSelector",
]


class RoundRobinComponentSelector:
    """Selects components in a round-robin fashion.

    This selector cycles through the list of components one by one, maintaining
    state per candidate index to ensure consistent rotation.

    Attributes:
        _next_index (dict[int, int]): Mapping of candidate_idx to next component index.

    Examples:
        ```python
        selector = RoundRobinComponentSelector()
        # First call selects first component
        c1 = await selector.select_components(["a", "b"], 1, 0)  # ["a"]
        # Second call selects second component
        c2 = await selector.select_components(["a", "b"], 2, 0)  # ["b"]
        ```

    Notes:
        Alternates through components sequentially, ensuring balanced evolution
        across all candidate parts.
    """

    def __init__(self) -> None:
        """Initialize the round-robin selector.

        Notes:
            Creates empty index tracking dictionary for per-candidate rotation state.
        """
        self._next_index: dict[int, int] = defaultdict(int)

    async def select_components(
        self, components: list[str], iteration: int, candidate_idx: int
    ) -> list[str]:
        """Select a single component to update using round-robin logic.

        Args:
            components: List of available component keys.
            iteration: Current global iteration number (unused by this strategy).
            candidate_idx: Index of the candidate being evolved.

        Returns:
            List containing the single selected component key.

        Raises:
            ValueError: If components list is empty.

        Examples:
            ```python
            selected = await selector.select_components(["a", "b"], 1, 0)
            ```

        Notes:
            Outputs one component per call, advancing the rotation index for
            the specified candidate.
        """
        if not components:
            raise ValueError("No components provided for selection")

        # Get current index for this candidate
        current_idx = self._next_index[candidate_idx]

        # Select component
        selected = components[current_idx % len(components)]

        # Advance index for next time
        self._next_index[candidate_idx] = (current_idx + 1) % len(components)

        return [selected]


class FullEvaluationPolicy:
    """Evaluation policy that scores all validation examples every iteration.

    This is the default evaluation policy, providing complete visibility
    into solution performance across all validation examples.

    Notes:
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

        Notes:
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

        Notes:
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

        Notes:
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
