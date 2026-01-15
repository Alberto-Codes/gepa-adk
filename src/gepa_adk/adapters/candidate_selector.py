"""Candidate selector adapter implementations.

Defines adapter implementations of CandidateSelectorProtocol for Pareto, greedy,
and epsilon-greedy selection strategies.
"""

from __future__ import annotations

import random

from gepa_adk.domain.exceptions import ConfigurationError, NoCandidateAvailableError
from gepa_adk.domain.state import ParetoState
from gepa_adk.ports.selector import CandidateSelectorProtocol


class ParetoCandidateSelector:
    """Sample from the Pareto front proportional to leadership frequency."""

    def __init__(self, rng: random.Random | None = None) -> None:
        """Initialize with optional RNG for reproducibility."""
        self._rng = rng or random.Random()

    async def select_candidate(self, state: ParetoState) -> int:
        """Select a candidate index from the Pareto frontier."""
        if not state.candidates:
            raise NoCandidateAvailableError("No candidates available for selection")

        weights = state.frontier.get_selection_weights()
        if not weights:
            raise NoCandidateAvailableError("Pareto frontier is empty")

        sampling_list = [
            candidate_idx
            for candidate_idx, weight in weights.items()
            for _ in range(weight)
        ]
        if not sampling_list:
            raise NoCandidateAvailableError("Pareto frontier has no leaders")

        return self._rng.choice(sampling_list)


class CurrentBestCandidateSelector:
    """Always select the candidate with the highest average score."""

    async def select_candidate(self, state: ParetoState) -> int:
        """Return the best-average candidate index."""
        if state.best_average_idx is None:
            raise NoCandidateAvailableError("No candidates available for selection")
        return state.best_average_idx


class EpsilonGreedyCandidateSelector:
    """Epsilon-greedy selection balancing exploration and exploitation."""

    def __init__(self, epsilon: float, rng: random.Random | None = None) -> None:
        """Initialize with exploration rate and RNG."""
        if not 0.0 <= epsilon <= 1.0:
            raise ConfigurationError(
                "epsilon must be between 0.0 and 1.0",
                field="epsilon",
                value=epsilon,
                constraint="0.0 <= epsilon <= 1.0",
            )
        self._epsilon = epsilon
        self._rng = rng or random.Random()

    async def select_candidate(self, state: ParetoState) -> int:
        """Select a candidate using epsilon-greedy strategy."""
        if not state.candidates:
            raise NoCandidateAvailableError("No candidates available for selection")

        if self._rng.random() < self._epsilon:
            return self._rng.randint(0, len(state.candidates) - 1)

        if state.best_average_idx is None:
            raise NoCandidateAvailableError("No candidates available for selection")

        return state.best_average_idx


def create_candidate_selector(
    selector_type: str,
    *,
    epsilon: float = 0.1,
    rng: random.Random | None = None,
) -> CandidateSelectorProtocol:
    """Create a candidate selector by name.

    Args:
        selector_type: Selector identifier (pareto, greedy, epsilon_greedy).
        epsilon: Exploration rate for epsilon-greedy selector.
        rng: Optional RNG for selectors using randomness.

    Returns:
        CandidateSelectorProtocol implementation.

    Raises:
        ConfigurationError: If selector_type is unsupported.
    """
    normalized = selector_type.strip().lower()
    if normalized in {"pareto"}:
        return ParetoCandidateSelector(rng=rng)
    if normalized in {"greedy", "current_best", "current-best"}:
        return CurrentBestCandidateSelector()
    if normalized in {"epsilon_greedy", "epsilon-greedy"}:
        return EpsilonGreedyCandidateSelector(epsilon=epsilon, rng=rng)
    raise ConfigurationError(
        "selector_type must be one of pareto, greedy, epsilon_greedy",
        field="selector_type",
        value=selector_type,
        constraint="pareto|greedy|epsilon_greedy",
    )


__all__ = [
    "ParetoCandidateSelector",
    "CurrentBestCandidateSelector",
    "EpsilonGreedyCandidateSelector",
    "create_candidate_selector",
]
