# MergeProposer Protocol Contract

## Class Definition

```python
from dataclasses import dataclass
from typing import Any

from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState
from gepa_adk.ports.proposer import ProposalResult

@dataclass
class MergeProposer:
    """Proposer that combines two Pareto-optimal candidates via genetic crossover.

    Selects two candidates from the frontier that share a common ancestor,
    identifies which components each improved, and creates a merged candidate
    that combines improvements from both branches.

    Attributes:
        rng: Random number generator for candidate selection.
        val_overlap_floor: Minimum overlapping validation coverage required.
        max_attempts: Maximum merge attempts before giving up.

    Examples:
        ```python
        proposer = MergeProposer(rng=random.Random(42))
        result = await proposer.propose(state)
        if result:
            print(f"Merged from parents {result.parent_indices}")
        ```
    """

    rng: random.Random
    val_overlap_floor: int = 5
    max_attempts: int = 10

    async def propose(
        self,
        state: ParetoState,
        eval_batch: EvaluationBatch | None = None,
    ) -> ProposalResult | None:
        """Attempt to merge two frontier candidates.

        Args:
            state: Current Pareto state with candidates, scores, and genealogy.
            eval_batch: Ignored for merge proposals.

        Returns:
            ProposalResult with merged candidate and both parent indices,
            or None if merge not possible.
        """
        ...

    def _find_merge_candidates(
        self,
        state: ParetoState,
    ) -> tuple[int, int, int] | None:
        """Find two candidates suitable for merging.

        Returns:
            Tuple of (parent1_idx, parent2_idx, ancestor_idx) or None.
        """
        ...

    def _merge_components(
        self,
        ancestor: dict[str, str],
        parent1: dict[str, str],
        parent2: dict[str, str],
        score1: float,
        score2: float,
    ) -> dict[str, str]:
        """Merge components from two parents based on ancestor divergence.

        Returns:
            Merged component dictionary.
        """
        ...
```

## Contract Requirements

### CR-001: Frontier Selection
- MUST only select candidates from Pareto frontier
- MUST NOT merge non-frontier candidates

### CR-002: Common Ancestor Requirement
- MUST find common ancestor before merging
- MUST return None if no common ancestor exists
- Ancestor MUST have lower or equal score to both descendants

### CR-003: Component Merging Logic
- If component unchanged from ancestor in one parent → take other parent's value
- If component unchanged from ancestor in both → take either (same value)
- If component changed differently in both → take higher-scoring parent's value

### CR-004: Merge Deduplication
- MUST track previously attempted merges
- MUST NOT re-attempt same (parent1, parent2, ancestor) triplet
- MUST NOT re-attempt same component combination

### CR-005: Validation Coverage
- MUST require minimum overlapping validation examples
- `val_overlap_floor` MUST be respected
- Return None if insufficient overlap

### CR-006: Return Format
- On success: `ProposalResult(candidate=..., parent_indices=[p1, p2], tag="merge", metadata={"ancestor_idx": ...})`
- On failure: `None`

### CR-007: Logging
- MUST log merge attempts via structlog
- MUST log merge success with parent and ancestor info
- MUST log merge failures with reason

## Merge Algorithm Flowchart

```
[Start]
    │
    ▼
[Get Frontier Candidates]
    │
    ├── frontier empty ──► [Return None]
    │
    ▼
[Sample Two Candidates]
    │
    ├── same candidate ──► [Retry up to max_attempts]
    │
    ▼
[Find Common Ancestor]
    │
    ├── no ancestor ──► [Retry with different pair]
    │
    ▼
[Check Ancestor Score]
    │
    ├── ancestor better than descendants ──► [Retry]
    │
    ▼
[Check Component Divergence]
    │
    ├── no useful divergence ──► [Retry]
    │
    ▼
[Check Already Attempted]
    │
    ├── already tried ──► [Retry]
    │
    ▼
[Check Val Overlap]
    │
    ├── insufficient overlap ──► [Retry]
    │
    ▼
[Merge Components]
    │
    ▼
[Return ProposalResult]
```

## Implementation Checklist

- [ ] Select from frontier only
- [ ] Find common ancestor
- [ ] Validate ancestor score constraint
- [ ] Track attempted merges
- [ ] Check validation overlap
- [ ] Implement component merge logic
- [ ] Return proper ProposalResult format
- [ ] Log all outcomes via structlog
