"""MergeProposer for combining Pareto-optimal candidates via genetic crossover.

This module provides the MergeProposer class that performs genetic crossover by
combining instruction components from two Pareto-optimal candidates that share
a common ancestor. This complements mutation-based evolution with recombination.

Attributes:
    MergeProposer (class): Proposer that combines two candidates via merge.

Examples:
    Basic usage:

    ```python
    from gepa_adk.engine.merge_proposer import MergeProposer
    import random

    proposer = MergeProposer(rng=random.Random(42))
    result = await proposer.propose(state)
    if result:
        print(f"Merged from parents {result.parent_indices}")
    ```

Note:
    MergeProposer implements ProposerProtocol and can be used alongside
    mutation proposers in the evolution engine.
"""

from __future__ import annotations

import random
from statistics import fmean

import structlog

from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState
from gepa_adk.domain.types import AncestorLog, ProposalResult
from gepa_adk.engine.genealogy import (
    find_common_ancestor,
    has_desirable_predictors,
)

logger = structlog.get_logger(__name__)


class MergeProposer:
    """Proposer that combines two Pareto-optimal candidates via genetic crossover.

    Selects two candidates from the frontier that share a common ancestor,
    identifies which components each improved, and creates a merged candidate
    that combines improvements from both branches.

    Attributes:
        rng (random.Random): Random number generator for candidate selection.
        val_overlap_floor (int): Minimum overlapping validation coverage required.
        max_attempts (int): Maximum merge attempts before giving up.
        attempted_merges (set[AncestorLog]): Set of attempted merge triplets to prevent duplicates.

    Examples:
        Creating a merge proposer:

        ```python
        proposer = MergeProposer(rng=random.Random(42))
        result = await proposer.propose(state)
        if result:
            print(f"Merged from parents {result.parent_indices}")
        ```
    """

    def __init__(
        self,
        rng: random.Random,
        val_overlap_floor: int = 5,
        max_attempts: int = 10,
    ) -> None:
        """Initialize MergeProposer.

        Args:
            rng: Random number generator for candidate selection.
            val_overlap_floor: Minimum overlapping validation examples required.
            max_attempts: Maximum merge attempts before giving up.
        """
        self.rng = rng
        self.val_overlap_floor = val_overlap_floor
        self.max_attempts = max_attempts
        self.attempted_merges: set[AncestorLog] = set()

    async def propose(
        self,
        state: ParetoState,
        eval_batch: object | None = None,  # Ignored for merge proposals
    ) -> ProposalResult | None:
        """Attempt to merge two frontier candidates.

        Args:
            state (ParetoState): Current Pareto state with candidates, scores, and genealogy.
                Must contain at least 2 candidates on the Pareto frontier with a shared
                common ancestor for merge to succeed.
            eval_batch (object | None): Ignored for merge proposals. Merge operations
                do not require evaluation batch data as they combine existing candidates.

        Returns:
            ProposalResult | None: ProposalResult with merged candidate and both parent indices,
            or None if merge not possible (e.g., no common ancestor, insufficient frontier,
            or no complementary component changes).

        Examples:
            Proposing a merge from evolution state:

            ```python
            proposer = MergeProposer(rng=random.Random(42))
            result = await proposer.propose(state)
            if result:
                print(f"Merged from parents {result.parent_indices}")
                print(f"Ancestor: {result.metadata['ancestor_idx']}")
            ```

        Note:
            Selects candidates from Pareto frontier only. Requires common ancestor
            and complementary component changes for successful merge. Validates
            minimum validation overlap before merging.
        """
        # Find suitable merge candidates
        merge_candidates = self._find_merge_candidates(state)
        if merge_candidates is None:
            logger.debug("merge_proposer.no_candidates", reason="no_suitable_pair")
            return None

        parent1_idx, parent2_idx, ancestor_idx = merge_candidates

        # Get candidate components
        ancestor = state.candidates[ancestor_idx]
        parent1 = state.candidates[parent1_idx]
        parent2 = state.candidates[parent2_idx]

        # Check if merge is desirable (complementary changes)
        if not has_desirable_predictors(
            ancestor.components, parent1.components, parent2.components
        ):
            logger.debug(
                "merge_proposer.no_desirable_predictors",
                parent1_idx=parent1_idx,
                parent2_idx=parent2_idx,
                ancestor_idx=ancestor_idx,
            )
            return None

        # Check validation overlap
        scores1 = state.candidate_scores.get(parent1_idx, {})
        scores2 = state.candidate_scores.get(parent2_idx, {})
        overlap = set(scores1.keys()) & set(scores2.keys())
        if len(overlap) < self.val_overlap_floor:
            logger.debug(
                "merge_proposer.insufficient_overlap",
                parent1_idx=parent1_idx,
                parent2_idx=parent2_idx,
                overlap_count=len(overlap),
                required=self.val_overlap_floor,
            )
            return None

        # Calculate average scores for component selection
        avg_score1 = fmean(scores1.values()) if scores1 else 0.0
        avg_score2 = fmean(scores2.values()) if scores2 else 0.0

        # Merge components
        merged_components = self._merge_components(
            ancestor.components,
            parent1.components,
            parent2.components,
            avg_score1,
            avg_score2,
        )

        # Create merged candidate
        merged_candidate = Candidate(
            components=merged_components,
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1_idx, parent2_idx],
        )

        # Log successful merge
        logger.info(
            "merge_proposer.merge_success",
            parent1_idx=parent1_idx,
            parent2_idx=parent2_idx,
            ancestor_idx=ancestor_idx,
            components_merged=list(merged_components.keys()),
        )

        return ProposalResult(
            candidate=merged_candidate,
            parent_indices=[parent1_idx, parent2_idx],
            tag="merge",
            metadata={"ancestor_idx": ancestor_idx},
        )

    def _find_merge_candidates(
        self,
        state: ParetoState,
    ) -> tuple[int, int, int] | None:
        """Find two candidates suitable for merging.

        Args:
            state: Current Pareto state.

        Returns:
            Tuple of (parent1_idx, parent2_idx, ancestor_idx) or None if no
            suitable pair found.

        Note:
            Only selects candidates from Pareto frontier. Requires common ancestor
            and prevents duplicate merge attempts.
        """
        # Get frontier candidates (non-dominated)
        frontier_candidates = state.frontier.get_non_dominated()

        if len(frontier_candidates) < 2:
            logger.debug(
                "merge_proposer.insufficient_frontier",
                frontier_size=len(frontier_candidates),
            )
            return None

        # Try to find a suitable pair
        for _ in range(self.max_attempts):
            # Sample two different candidates from frontier
            candidate_list = list(frontier_candidates)
            if len(candidate_list) < 2:
                return None

            parent1_idx = self.rng.choice(candidate_list)
            parent2_idx = self.rng.choice(candidate_list)

            # Must be different candidates
            if parent1_idx == parent2_idx:
                continue

            # Ensure consistent ordering for deduplication
            if parent1_idx > parent2_idx:
                parent1_idx, parent2_idx = parent2_idx, parent1_idx

            # Find common ancestor
            ancestor_idx = find_common_ancestor(
                parent1_idx, parent2_idx, state.parent_indices
            )

            if ancestor_idx is None:
                continue

            # Check if already attempted
            merge_log: AncestorLog = (parent1_idx, parent2_idx, ancestor_idx)
            if merge_log in self.attempted_merges:
                continue

            # Check ancestor score constraint (ancestor should not be better than descendants)
            ancestor_scores = state.candidate_scores.get(ancestor_idx, {})
            parent1_scores = state.candidate_scores.get(parent1_idx, {})
            parent2_scores = state.candidate_scores.get(parent2_idx, {})

            if ancestor_scores and parent1_scores and parent2_scores:
                ancestor_avg = fmean(ancestor_scores.values())
                parent1_avg = fmean(parent1_scores.values())
                parent2_avg = fmean(parent2_scores.values())

                # Ancestor should not be better than both descendants
                if ancestor_avg > max(parent1_avg, parent2_avg):
                    logger.debug(
                        "merge_proposer.ancestor_too_good",
                        ancestor_idx=ancestor_idx,
                        ancestor_avg=ancestor_avg,
                        parent1_avg=parent1_avg,
                        parent2_avg=parent2_avg,
                    )
                    continue

            # Mark as attempted
            self.attempted_merges.add(merge_log)

            return (parent1_idx, parent2_idx, ancestor_idx)

        logger.debug("merge_proposer.max_attempts_exceeded", attempts=self.max_attempts)
        return None

    def _merge_components(
        self,
        ancestor: dict[str, str],
        parent1: dict[str, str],
        parent2: dict[str, str],
        score1: float,
        score2: float,
    ) -> dict[str, str]:
        """Merge components from two parents based on ancestor divergence.

        Args:
            ancestor: Component dictionary from common ancestor.
            parent1: Component dictionary from first parent.
            parent2: Component dictionary from second parent.
            score1: Average score of first parent.
            score2: Average score of second parent.

        Returns:
            Merged component dictionary.

        Note:
            Merge logic:
            - If both parents same → take either
            - If one unchanged from ancestor, other changed → take changed value
            - If both changed differently → take higher scorer's value
        """
        merged: dict[str, str] = {}

        for key in ancestor.keys():
            anc_val = ancestor[key]
            p1_val = parent1.get(key, anc_val)
            p2_val = parent2.get(key, anc_val)

            if p1_val == p2_val:
                # Both same - take either
                merged[key] = p1_val
            elif p1_val == anc_val and p2_val != anc_val:
                # P1 unchanged, P2 changed - take P2's innovation
                merged[key] = p2_val
            elif p2_val == anc_val and p1_val != anc_val:
                # P2 unchanged, P1 changed - take P1's innovation
                merged[key] = p1_val
            else:
                # Both changed differently - take higher scorer's value
                merged[key] = p1_val if score1 >= score2 else p2_val

        return merged
