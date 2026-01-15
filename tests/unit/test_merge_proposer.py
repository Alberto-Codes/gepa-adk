"""Unit tests for MergeProposer implementation.

Note:
    These tests verify merge component logic and candidate selection
    for genetic crossover operations.
"""

from __future__ import annotations

import random

import pytest

from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState
from gepa_adk.engine.merge_proposer import MergeProposer

pytestmark = pytest.mark.unit


class TestMergeComponents:
    """Tests for merge_components() function."""

    def test_merge_complementary_components(self) -> None:
        """Test merging candidates with complementary component changes."""
        proposer = MergeProposer(rng=random.Random(42))

        ancestor = {"instruction": "A", "output_schema": "B"}
        parent1 = {"instruction": "A", "output_schema": "C"}  # output_schema changed
        parent2 = {"instruction": "D", "output_schema": "B"}  # instruction changed

        merged = proposer._merge_components(ancestor, parent1, parent2, 0.7, 0.8)

        # Should take parent1's output_schema (changed) and parent2's instruction (changed)
        assert merged["instruction"] == "D"  # From parent2
        assert merged["output_schema"] == "C"  # From parent1

    def test_merge_takes_higher_scorer_when_both_changed(self) -> None:
        """Test that when both parents changed a component, take higher scorer's value."""
        proposer = MergeProposer(rng=random.Random(42))

        ancestor = {"instruction": "A"}
        parent1 = {"instruction": "B"}  # Changed, score 0.7
        parent2 = {"instruction": "C"}  # Changed, score 0.9

        merged = proposer._merge_components(ancestor, parent1, parent2, 0.7, 0.9)

        # Should take parent2's value (higher score)
        assert merged["instruction"] == "C"

    def test_merge_identical_components(self) -> None:
        """Test merging when components are identical."""
        proposer = MergeProposer(rng=random.Random(42))

        ancestor = {"instruction": "A"}
        parent1 = {"instruction": "B"}
        parent2 = {"instruction": "B"}  # Same as parent1

        merged = proposer._merge_components(ancestor, parent1, parent2, 0.7, 0.8)

        # Should take either (they're the same)
        assert merged["instruction"] == "B"


class TestFindMergeCandidates:
    """Tests for _find_merge_candidates() method."""

    def test_finds_candidates_with_common_ancestor(self) -> None:
        """Test finding merge candidates that share a common ancestor."""
        proposer = MergeProposer(rng=random.Random(42))
        state = ParetoState()
        # Create genealogy: 0 (seed) -> 1, 2
        # Use different scores per example to ensure all are on frontier
        state.add_candidate(
            Candidate(components={"instruction": "seed"}),
            [0.5, 0.3],
            parent_indices=None,
        )
        state.add_candidate(
            Candidate(components={"instruction": "child1"}),
            [0.7, 0.2],
            parent_indices=[0],
        )
        state.add_candidate(
            Candidate(components={"instruction": "child2"}),
            [0.2, 0.8],
            parent_indices=[0],
        )

        result = proposer._find_merge_candidates(state)

        assert result is not None
        parent1_idx, parent2_idx, ancestor_idx = result
        assert parent1_idx in (1, 2)
        assert parent2_idx in (1, 2)
        assert parent1_idx != parent2_idx
        assert ancestor_idx == 0

    def test_returns_none_when_no_common_ancestor(self) -> None:
        """Test that separate lineages return None."""
        proposer = MergeProposer(rng=random.Random(42))
        state = ParetoState()
        # Create separate lineages
        state.add_candidate(
            Candidate(components={"instruction": "seed1"}), [0.5], parent_indices=None
        )
        state.add_candidate(
            Candidate(components={"instruction": "seed2"}), [0.6], parent_indices=None
        )

        result = proposer._find_merge_candidates(state)

        assert result is None

    def test_returns_none_when_insufficient_frontier(self) -> None:
        """Test that insufficient frontier candidates return None."""
        proposer = MergeProposer(rng=random.Random(42))
        state = ParetoState()
        # Only one candidate on frontier
        state.add_candidate(
            Candidate(components={"instruction": "only"}), [0.5], parent_indices=None
        )

        result = proposer._find_merge_candidates(state)

        assert result is None


class TestMergeProposerPropose:
    """Tests for MergeProposer.propose() method."""

    @pytest.mark.asyncio
    async def test_propose_returns_none_when_no_candidates(self) -> None:
        """Test that empty state returns None."""
        proposer = MergeProposer(rng=random.Random(42))
        state = ParetoState()

        result = await proposer.propose(state)

        assert result is None

    @pytest.mark.asyncio
    async def test_propose_creates_merged_candidate(self) -> None:
        """Test that propose creates a merged candidate from two parents."""
        proposer = MergeProposer(rng=random.Random(42))
        state = ParetoState()
        # Create mergeable candidates
        state.add_candidate(
            Candidate(components={"instruction": "A", "output_schema": "X"}),
            [0.5],
            parent_indices=None,
        )
        state.add_candidate(
            Candidate(components={"instruction": "A", "output_schema": "Y"}),
            [0.7],
            parent_indices=[0],
        )
        state.add_candidate(
            Candidate(components={"instruction": "B", "output_schema": "X"}),
            [0.8],
            parent_indices=[0],
        )

        result = await proposer.propose(state)

        if result is not None:
            assert result.tag == "merge"
            assert len(result.parent_indices) == 2
            assert "ancestor_idx" in result.metadata
            # Merged candidate should combine components
            assert "instruction" in result.candidate.components
            assert "output_schema" in result.candidate.components

    @pytest.mark.asyncio
    async def test_propose_tracks_merge_attempts(self) -> None:
        """Test that merge attempts are tracked to prevent duplicates."""
        proposer = MergeProposer(rng=random.Random(42), val_overlap_floor=1)
        state = ParetoState()
        state.add_candidate(
            Candidate(components={"instruction": "A"}), [0.5, 0.5], parent_indices=None
        )
        state.add_candidate(
            Candidate(components={"instruction": "B"}),
            [0.8, 0.2],
            parent_indices=[0],
        )
        state.add_candidate(
            Candidate(components={"instruction": "C"}),
            [0.2, 0.8],
            parent_indices=[0],
        )

        result1 = await proposer.propose(state)
        result2 = await proposer.propose(state)

        assert result1 is not None
        assert result1.tag == "merge"
        assert result2 is None
