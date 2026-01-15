"""Unit tests for candidate selector implementations."""

from __future__ import annotations

import random

import pytest

from gepa_adk.adapters.candidate_selector import (
    CurrentBestCandidateSelector,
    EpsilonGreedyCandidateSelector,
    ParetoCandidateSelector,
)
from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState

pytestmark = pytest.mark.unit


class DeterministicExplorationRng(random.Random):
    """Random generator that forces exploration to a fixed index."""

    def __init__(self, seed: int, exploration_index: int) -> None:
        """Initialize with seed and fixed exploration index."""
        super().__init__(seed)
        self._exploration_index = exploration_index

    def randint(self, a: int, b: int) -> int:
        """Return a fixed exploration index within bounds."""
        if a <= self._exploration_index <= b:
            return self._exploration_index
        return a


@pytest.fixture
def pareto_state() -> ParetoState:
    """Create a ParetoState with three candidates."""
    state = ParetoState()
    state.add_candidate(Candidate(components={"instruction": "best"}), [0.8, 0.8])
    state.add_candidate(Candidate(components={"instruction": "left"}), [0.9, 0.2])
    state.add_candidate(Candidate(components={"instruction": "right"}), [0.2, 0.9])
    return state


@pytest.mark.asyncio
async def test_pareto_selector_samples_from_frontier(pareto_state: ParetoState) -> None:
    """Pareto selector samples from non-dominated candidates."""
    selector = ParetoCandidateSelector(rng=random.Random(1))

    selected = await selector.select_candidate(pareto_state)

    assert selected in pareto_state.frontier.get_non_dominated()


@pytest.mark.asyncio
async def test_current_best_selector_returns_best_average(
    pareto_state: ParetoState,
) -> None:
    """Current best selector returns the highest average candidate."""
    selector = CurrentBestCandidateSelector()

    selected = await selector.select_candidate(pareto_state)

    assert selected == pareto_state.best_average_idx


@pytest.mark.asyncio
async def test_epsilon_greedy_zero_epsilon_is_greedy(
    pareto_state: ParetoState,
) -> None:
    """Epsilon-greedy falls back to greedy when epsilon is zero."""
    selector = EpsilonGreedyCandidateSelector(epsilon=0.0, rng=random.Random(3))

    selected = await selector.select_candidate(pareto_state)

    assert selected == pareto_state.best_average_idx


@pytest.mark.asyncio
async def test_epsilon_greedy_exploration_rate() -> None:
    """Exploration rate stays within tolerance for fixed RNG."""
    rng = DeterministicExplorationRng(seed=1234, exploration_index=1)
    selector = EpsilonGreedyCandidateSelector(epsilon=0.1, rng=rng)
    state = ParetoState()
    state.add_candidate(Candidate(components={"instruction": "best"}), [0.9, 0.9])
    state.add_candidate(Candidate(components={"instruction": "alt"}), [0.1, 0.1])

    selections = [await selector.select_candidate(state) for _ in range(200)]
    exploration_count = sum(1 for idx in selections if idx != state.best_average_idx)
    exploration_rate = exploration_count / len(selections)

    assert abs(exploration_rate - 0.1) <= 0.05
