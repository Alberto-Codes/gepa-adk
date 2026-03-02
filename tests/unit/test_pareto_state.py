"""Unit tests for ParetoState and ParetoFrontier."""

from __future__ import annotations

import time

import pytest

from gepa_adk.adapters.selection.candidate_selector import CurrentBestCandidateSelector
from gepa_adk.domain.exceptions import NoCandidateAvailableError
from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoFrontier, ParetoState
from gepa_adk.domain.types import FrontierType

pytestmark = pytest.mark.unit


def test_frontier_tracks_example_leaders() -> None:
    """Frontier tracks best candidates per example."""
    frontier = ParetoFrontier()

    frontier.update(0, {0: 0.9, 1: 0.3})
    frontier.update(1, {0: 0.5, 1: 0.8})

    assert frontier.best_scores == {0: 0.9, 1: 0.8}
    assert frontier.example_leaders[0] == {0}
    assert frontier.example_leaders[1] == {1}
    assert frontier.get_non_dominated() == {0, 1}


def test_frontier_selection_weights_count_frequency() -> None:
    """Weights reflect how many examples each candidate leads."""
    frontier = ParetoFrontier()

    frontier.update(0, {0: 0.9, 1: 0.9})
    frontier.update(1, {0: 0.9, 1: 0.5})

    weights = frontier.get_selection_weights()

    assert weights[0] == 2
    assert weights[1] == 1


def test_frontier_retains_specialist_candidates() -> None:
    """Specialists leading different examples remain on the frontier."""
    frontier = ParetoFrontier()

    frontier.update(0, {0: 0.95, 1: 0.2, 2: 0.2})
    frontier.update(1, {0: 0.1, 1: 0.96, 2: 0.2})
    frontier.update(2, {0: 0.1, 1: 0.2, 2: 0.97})

    assert frontier.get_non_dominated() == {0, 1, 2}


def test_identical_scores_have_equal_weights() -> None:
    """Identical scores produce equal selection weights."""
    frontier = ParetoFrontier()

    frontier.update(0, {0: 0.8, 1: 0.8})
    frontier.update(1, {0: 0.8, 1: 0.8})

    weights = frontier.get_selection_weights()

    assert weights[0] == weights[1]


def test_dominant_candidate_reduces_frontier() -> None:
    """Dominant candidate removes dominated candidates from frontier."""
    frontier = ParetoFrontier()

    frontier.update(0, {0: 0.9, 1: 0.9})
    frontier.update(1, {0: 0.2, 1: 0.1})

    assert frontier.get_non_dominated() == {0}


def test_state_add_candidate_updates_best_average() -> None:
    """ParetoState tracks best average candidate."""
    state = ParetoState(frontier_type=FrontierType.INSTANCE)

    idx0 = state.add_candidate(Candidate(components={"instruction": "a"}), [0.2, 0.4])
    idx1 = state.add_candidate(Candidate(components={"instruction": "b"}), [0.6, 0.6])

    assert state.best_average_idx == idx1
    assert state.get_average_score(idx0) == pytest.approx(0.3)
    assert state.get_average_score(idx1) == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_empty_state_selector_raises() -> None:
    """Empty state raises NoCandidateAvailableError when selecting."""
    selector = CurrentBestCandidateSelector()
    state = ParetoState()

    with pytest.raises(NoCandidateAvailableError):
        await selector.select_candidate(state)


def test_frontier_update_performance_budget() -> None:
    """Frontier update stays within performance budget for expected scale."""
    frontier = ParetoFrontier()

    scores = [{idx: (idx % 10) / 10 for idx in range(50)} for _ in range(100)]
    start = time.perf_counter()
    for candidate_idx, candidate_scores in enumerate(scores):
        frontier.update(candidate_idx, candidate_scores)
    duration = time.perf_counter() - start

    assert duration < 0.01
