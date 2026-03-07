"""Contract tests for CandidateSelectorProtocol compliance."""

from __future__ import annotations

import random

import pytest

from gepa_adk.adapters.selection.candidate_selector import (
    CurrentBestCandidateSelector,
    EpsilonGreedyCandidateSelector,
    ParetoCandidateSelector,
)
from gepa_adk.domain.exceptions import NoCandidateAvailableError
from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState
from gepa_adk.ports.candidate_selector import CandidateSelectorProtocol

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


class TestCandidateSelectorProtocolRuntimeCheckable:
    """Positive compliance: isinstance checks for all implementations."""

    def test_import_path_equivalence(self) -> None:
        """CandidateSelectorProtocol is accessible from both import paths."""
        from gepa_adk.ports import CandidateSelectorProtocol as from_init
        from gepa_adk.ports.candidate_selector import (
            CandidateSelectorProtocol as from_module,
        )

        assert from_init is from_module

    def test_is_protocol_compliant(self, selector: CandidateSelectorProtocol) -> None:
        """Selectors implement CandidateSelectorProtocol."""
        assert isinstance(selector, CandidateSelectorProtocol)


class TestCandidateSelectorProtocolBehavior:
    """Behavioral expectations: return types, edge cases."""

    @pytest.mark.asyncio
    async def test_select_candidate_returns_valid_index(
        self, selector: CandidateSelectorProtocol, pareto_state: ParetoState
    ) -> None:
        """select_candidate returns a valid candidate index."""
        result = await selector.select_candidate(pareto_state)
        assert 0 <= result < len(pareto_state.candidates)

    @pytest.mark.asyncio
    async def test_select_candidate_returns_int(
        self, selector: CandidateSelectorProtocol, pareto_state: ParetoState
    ) -> None:
        """select_candidate returns an int."""
        result = await selector.select_candidate(pareto_state)
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_select_candidate_raises_on_empty_state(
        self, selector: CandidateSelectorProtocol, empty_state: ParetoState
    ) -> None:
        """select_candidate raises NoCandidateAvailableError for empty state."""
        with pytest.raises(NoCandidateAvailableError):
            await selector.select_candidate(empty_state)


class TestCandidateSelectorProtocolNonCompliance:
    """Negative cases: objects missing required methods are not instances."""

    def test_missing_method_not_isinstance(self) -> None:
        """Class without select_candidate is not a CandidateSelectorProtocol."""

        class Incomplete:
            pass

        assert not isinstance(Incomplete(), CandidateSelectorProtocol)

    def test_runtime_checkable_limitation_documented(self) -> None:
        """@runtime_checkable only checks method existence, not signatures."""

        class WrongSignature:
            async def select_candidate(self): ...

        # isinstance passes because runtime_checkable doesn't check signatures
        assert isinstance(WrongSignature(), CandidateSelectorProtocol)
