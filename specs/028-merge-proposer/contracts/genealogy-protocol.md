# Genealogy Protocol Contract

## Protocol Definition

```python
from typing import Protocol

class GenealogyProtocol(Protocol):
    """Protocol for genealogy tracking and ancestor queries.

    Genealogy tracks parent-child relationships between candidates
    to enable merge operations that combine improvements from
    different evolutionary branches.

    Examples:
        ```python
        class MyGenealogy:
            def add_candidate(
                self, candidate_idx: int, parent_indices: list[int | None]
            ) -> None:
                ...

            def get_ancestors(self, candidate_idx: int) -> set[int]:
                ...

            def find_common_ancestor(self, idx1: int, idx2: int) -> int | None:
                ...
        ```
    """

    def add_candidate(
        self, candidate_idx: int, parent_indices: list[int | None]
    ) -> None:
        """Register a candidate's parent relationship.

        Args:
            candidate_idx: Index of the new candidate.
            parent_indices: List of parent indices (or [None] for seeds).
        """
        ...

    def get_ancestors(self, candidate_idx: int) -> set[int]:
        """Return all ancestor indices for a candidate.

        Args:
            candidate_idx: Index of the candidate to trace.

        Returns:
            Set of all ancestor candidate indices.
        """
        ...

    def find_common_ancestor(self, idx1: int, idx2: int) -> int | None:
        """Find the most recent common ancestor of two candidates.

        Args:
            idx1: First candidate index.
            idx2: Second candidate index.

        Returns:
            Index of most recent common ancestor, or None if none exists.
        """
        ...
```

## Contract Requirements

### CR-001: Seed Candidate Handling
- Seed candidates MUST have `parent_indices = [None]`
- `get_ancestors()` of seed MUST return empty set

### CR-002: Single Parent (Mutation)
- Mutated candidates MUST have `parent_indices = [single_idx]`
- Parent MUST be a valid candidate index

### CR-003: Dual Parent (Merge)
- Merged candidates MUST have `parent_indices = [idx1, idx2]`
- Both indices MUST be valid candidate indices
- Indices MUST be different (no self-merge)

### CR-004: Ancestor Completeness
- `get_ancestors()` MUST return ALL ancestors (transitive closure)
- MUST NOT include the candidate itself in ancestors

### CR-005: Common Ancestor Correctness
- `find_common_ancestor()` MUST return None if no common ancestor
- MUST return the most recent (highest index) common ancestor
- MUST handle case where one is ancestor of the other

### CR-006: Cycle Prevention
- Implementation MUST NOT allow circular ancestry
- A candidate MUST NOT be its own ancestor

## Implementation Checklist

- [ ] Handle seed candidates with `[None]` parents
- [ ] Support single parent for mutation
- [ ] Support dual parents for merge
- [ ] Implement transitive ancestor traversal
- [ ] Find most recent common ancestor
- [ ] Prevent circular ancestry
- [ ] Handle invalid indices gracefully
