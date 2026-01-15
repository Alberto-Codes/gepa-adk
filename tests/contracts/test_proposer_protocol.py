"""Contract tests for ProposerProtocol protocol compliance.

Note:
    These tests ensure proposers implement the required async methods
    with correct signatures and return types for engine compatibility.
"""

from __future__ import annotations

import pytest

from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState
from gepa_adk.domain.types import ProposalResult
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.proposer import ProposerProtocol

pytestmark = pytest.mark.contract


class MockProposer:
    """Skeleton mock proposer for contract testing.

    Note:
        All methods return minimal valid responses for testing
        protocol compliance without complex business logic.
    """

    async def propose(
        self,
        state: ParetoState,
        eval_batch: EvaluationBatch | None = None,
    ) -> ProposalResult | None:
        """Return a minimal proposal result for contract checks."""
        if not state.candidates:
            return None
        candidate = Candidate(components={"instruction": "test"})
        return ProposalResult(
            candidate=candidate,
            parent_indices=[0],
            tag="mutation",
        )


class TestProposerProtocol:
    """Contract tests for ProposerProtocol protocol compliance.

    Note:
        All tests use MockProposer to verify protocol contracts.
        Tests cover method signatures, return types, and async behavior.
    """

    @pytest.mark.asyncio
    async def test_propose_is_async(self) -> None:
        """Ensure propose is an async method."""
        proposer = MockProposer()
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])

        result = await proposer.propose(state)

        assert result is not None
        assert isinstance(result, ProposalResult)

    @pytest.mark.asyncio
    async def test_propose_returns_proposal_result_or_none(self) -> None:
        """Ensure propose returns ProposalResult or None."""
        proposer = MockProposer()
        state = ParetoState()

        # Empty state should return None
        result = await proposer.propose(state)
        assert result is None

        # State with candidates should return ProposalResult
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])
        result = await proposer.propose(state)
        assert isinstance(result, ProposalResult)

    @pytest.mark.asyncio
    async def test_proposal_result_has_required_fields(self) -> None:
        """Ensure ProposalResult contains required fields."""
        proposer = MockProposer()
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])

        result = await proposer.propose(state)

        assert result is not None
        assert hasattr(result, "candidate")
        assert hasattr(result, "parent_indices")
        assert hasattr(result, "tag")
        assert hasattr(result, "metadata")
        assert isinstance(result.candidate, Candidate)
        assert isinstance(result.parent_indices, list)
        assert isinstance(result.tag, str)
        assert isinstance(result.metadata, dict)

    @pytest.mark.asyncio
    async def test_proposal_result_parent_indices_valid(self) -> None:
        """Ensure parent_indices are valid candidate indices."""
        proposer = MockProposer()
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])

        result = await proposer.propose(state)

        assert result is not None
        assert len(result.parent_indices) > 0
        for parent_idx in result.parent_indices:
            assert isinstance(parent_idx, int)
            assert 0 <= parent_idx < len(state.candidates)

    @pytest.mark.asyncio
    async def test_proposal_result_tag_values(self) -> None:
        """Ensure tag is one of the expected values."""
        proposer = MockProposer()
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])

        result = await proposer.propose(state)

        assert result is not None
        assert result.tag in ("mutation", "merge")

    @pytest.mark.asyncio
    async def test_propose_does_not_modify_state(self) -> None:
        """Ensure propose does not modify the input state."""
        proposer = MockProposer()
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])
        original_candidates = state.candidates.copy()
        original_scores = state.candidate_scores.copy()

        await proposer.propose(state)

        assert state.candidates == original_candidates
        assert state.candidate_scores == original_scores

    @pytest.mark.asyncio
    async def test_propose_accepts_optional_eval_batch(self) -> None:
        """Ensure propose accepts optional eval_batch parameter."""
        proposer = MockProposer()
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])
        eval_batch = EvaluationBatch(outputs=["test"], scores=[0.8])

        # Should work with eval_batch
        result1 = await proposer.propose(state, eval_batch)
        assert result1 is not None

        # Should work without eval_batch
        result2 = await proposer.propose(state, None)
        assert result2 is not None

    def test_proposer_protocol_runtime_checkable(self) -> None:
        """Ensure ProposerProtocol supports runtime checking."""
        proposer = MockProposer()

        assert isinstance(proposer, ProposerProtocol)

    @pytest.mark.asyncio
    async def test_mutation_proposal_has_single_parent(self) -> None:
        """Ensure mutation proposals have exactly one parent index."""
        proposer = MockProposer()
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])

        result = await proposer.propose(state)

        assert result is not None
        if result.tag == "mutation":
            assert len(result.parent_indices) == 1

    @pytest.mark.asyncio
    async def test_merge_proposal_has_two_parents(self) -> None:
        """Ensure merge proposals have exactly two parent indices."""
        # This test would need a merge proposer implementation
        # For now, we just verify the contract expectation
        proposer = MockProposer()
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])

        result = await proposer.propose(state)

        assert result is not None
        if result.tag == "merge":
            assert len(result.parent_indices) == 2
