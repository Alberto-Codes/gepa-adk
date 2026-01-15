"""Contract tests for CandidateSelectorProtocol compliance."""

from __future__ import annotations

import random

import pytest

from gepa_adk.adapters.candidate_selector import (
    CurrentBestCandidateSelector,
    EpsilonGreedyCandidateSelector,
    ParetoCandidateSelector,
)
from gepa_adk.domain.exceptions import NoCandidateAvailableError
from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState
from gepa_adk.ports.selector import CandidateSelectorProtocol

pytestmark = pytest.mark.contract


@pytest.fixture
def pareto_state() -> ParetoState:
    """Create a minimal ParetoState with two candidates."""
    state = ParetoState()
    state.add_candidate(Candidate(components={"instruction": "a"}), [0.9, 0.1])
    state.add_candidate(Candidate(components={"instruction": "b"}), [0.1, 0.8])
    return state


@pytest.fixture
def empty_state() -> ParetoState:
    """Create an empty ParetoState."""
    return ParetoState()


@pytest.fixture(
    params=[
        ParetoCandidateSelector(random.Random(1)),
        CurrentBestCandidateSelector(),
        EpsilonGreedyCandidateSelector(epsilon=0.1, rng=random.Random(2)),
    ]
)
def selector(request) -> CandidateSelectorProtocol:
    """Provide each selector implementation for contract tests."""
    return request.param


def test_is_protocol_compliant(selector: CandidateSelectorProtocol) -> None:
    """Selectors implement CandidateSelectorProtocol."""
    assert isinstance(selector, CandidateSelectorProtocol)


@pytest.mark.asyncio
async def test_select_candidate_returns_valid_index(
    selector: CandidateSelectorProtocol, pareto_state: ParetoState
) -> None:
    """select_candidate returns a valid candidate index."""
    result = await selector.select_candidate(pareto_state)
    assert 0 <= result < len(pareto_state.candidates)


@pytest.mark.asyncio
async def test_select_candidate_raises_on_empty_state(
    selector: CandidateSelectorProtocol, empty_state: ParetoState
) -> None:
    """select_candidate raises NoCandidateAvailableError for empty state."""
    with pytest.raises(NoCandidateAvailableError):
        await selector.select_candidate(empty_state)
