"""Contract tests for MergeProposer protocol compliance.

Note:
    These tests ensure MergeProposer implements ProposerProtocol correctly
    and follows the merge proposer contract requirements.
"""

from __future__ import annotations

import random

import pytest

from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState
from gepa_adk.engine.merge_proposer import MergeProposer
from gepa_adk.ports.proposer import ProposerProtocol

pytestmark = pytest.mark.contract


class TestMergeProposerProtocol:
    """Contract tests for MergeProposer protocol compliance."""

    @pytest.mark.asyncio
    async def test_implements_proposer_protocol(self) -> None:
        """Ensure MergeProposer implements ProposerProtocol."""
        proposer = MergeProposer(rng=random.Random(42))

        assert isinstance(proposer, ProposerProtocol)

    @pytest.mark.asyncio
    async def test_propose_returns_proposal_result_or_none(self) -> None:
        """Ensure propose returns ProposalResult or None."""
        proposer = MergeProposer(rng=random.Random(42))
        state = ParetoState()

        # Empty state should return None
        result = await proposer.propose(state)
        assert result is None

    @pytest.mark.asyncio
    async def test_proposal_result_has_merge_tag(self) -> None:
        """Ensure merge proposals have tag='merge'."""
        proposer = MergeProposer(rng=random.Random(42))
        state = ParetoState()
        # Create state with mergeable candidates
        state.add_candidate(
            Candidate(components={"instruction": "A"}), [0.5], parent_indices=None
        )
        state.add_candidate(
            Candidate(components={"instruction": "B"}), [0.6], parent_indices=[0]
        )
        state.add_candidate(
            Candidate(components={"instruction": "C"}), [0.7], parent_indices=[0]
        )

        result = await proposer.propose(state)

        if result is not None:
            assert result.tag == "merge"

    @pytest.mark.asyncio
    async def test_merge_proposal_has_two_parents(self) -> None:
        """Ensure merge proposals have exactly two parent indices."""
        proposer = MergeProposer(rng=random.Random(42))
        state = ParetoState()
        state.add_candidate(
            Candidate(components={"instruction": "A"}), [0.5], parent_indices=None
        )
        state.add_candidate(
            Candidate(components={"instruction": "B"}), [0.6], parent_indices=[0]
        )
        state.add_candidate(
            Candidate(components={"instruction": "C"}), [0.7], parent_indices=[0]
        )

        result = await proposer.propose(state)

        if result is not None:
            assert len(result.parent_indices) == 2
            assert result.parent_indices[0] != result.parent_indices[1]

    @pytest.mark.asyncio
    async def test_proposal_result_includes_ancestor_metadata(self) -> None:
        """Ensure merge proposals include ancestor_idx in metadata."""
        proposer = MergeProposer(rng=random.Random(42))
        state = ParetoState()
        state.add_candidate(
            Candidate(components={"instruction": "A"}), [0.5], parent_indices=None
        )
        state.add_candidate(
            Candidate(components={"instruction": "B"}), [0.6], parent_indices=[0]
        )
        state.add_candidate(
            Candidate(components={"instruction": "C"}), [0.7], parent_indices=[0]
        )

        result = await proposer.propose(state)

        if result is not None:
            assert "ancestor_idx" in result.metadata
            assert isinstance(result.metadata["ancestor_idx"], int)

    @pytest.mark.asyncio
    async def test_propose_does_not_modify_state(self) -> None:
        """Ensure propose does not modify the input state."""
        proposer = MergeProposer(rng=random.Random(42))
        state = ParetoState()
        state.add_candidate(
            Candidate(components={"instruction": "A"}), [0.5], parent_indices=None
        )
        original_candidates = state.candidates.copy()
        original_scores = state.candidate_scores.copy()

        await proposer.propose(state)

        assert state.candidates == original_candidates
        assert state.candidate_scores == original_scores


class TestMergeProposerProtocolNonCompliance:
    """Negative cases: objects missing required methods are not instances."""

    def test_missing_propose_not_isinstance(self) -> None:
        """Class without propose method is not a ProposerProtocol."""

        class Incomplete:
            pass

        assert not isinstance(Incomplete(), ProposerProtocol)

    def test_runtime_checkable_limitation_documented(self) -> None:
        """@runtime_checkable only checks method existence, not signatures."""

        class WrongSignature:
            async def propose(self): ...

        # isinstance passes because runtime_checkable doesn't check signatures
        assert isinstance(WrongSignature(), ProposerProtocol)
