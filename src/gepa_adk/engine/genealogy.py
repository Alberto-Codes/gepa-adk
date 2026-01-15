"""Genealogy tracking and ancestor queries for merge operations.

This module provides functions for tracking parent-child relationships between
candidates and finding common ancestors, enabling merge operations that combine
improvements from different evolutionary branches.

Attributes:
    get_ancestors (function): Return all ancestor indices for a candidate.
    find_common_ancestor (function): Find the most recent common ancestor of two candidates.

Examples:
    Getting all ancestors of a candidate:

    ```python
    from gepa_adk.engine.genealogy import get_ancestors

    parent_indices = {0: [None], 1: [0], 2: [1]}
    ancestors = get_ancestors(2, parent_indices)
    # Returns: {0, 1}
    ```

    Finding common ancestor:

    ```python
    from gepa_adk.engine.genealogy import find_common_ancestor

    parent_indices = {0: [None], 1: [0], 2: [0], 3: [1, 2]}
    ancestor = find_common_ancestor(1, 2, parent_indices)
    # Returns: 0
    ```

Note:
    This module provides genealogy tracking functions for merge operations.
    Genealogy tracking enables merge operations by identifying which candidates
    share common ancestry and can be safely combined.
"""

from __future__ import annotations

from collections import deque

import structlog

logger = structlog.get_logger(__name__)


def get_ancestors(
    candidate_idx: int, parent_indices: dict[int, list[int | None]]
) -> set[int]:
    """Return all ancestor indices for a candidate.

    Traverses the genealogy tree using breadth-first search to find all
    ancestors transitively. Seed candidates (with [None] parents) have
    no ancestors.

    Args:
        candidate_idx: Index of the candidate to trace.
        parent_indices: Mapping of candidate index to parent indices list.

    Returns:
        Set of all ancestor candidate indices (excluding the candidate itself).

    Examples:
        Simple linear genealogy:

        ```python
        parent_indices = {0: [None], 1: [0], 2: [1]}
        ancestors = get_ancestors(2, parent_indices)
        # Returns: {0, 1}
        ```

        Merge candidate with two parents:

        ```python
        parent_indices = {0: [None], 1: [0], 2: [0], 3: [1, 2]}
        ancestors = get_ancestors(3, parent_indices)
        # Returns: {0, 1, 2}
        ```

    Note:
        Operations use BFS to avoid recursion depth issues with deep genealogies.
        Prevents cycles by tracking visited nodes.
    """
    ancestors: set[int] = set()
    visited: set[int] = {candidate_idx}
    queue: deque[int] = deque([candidate_idx])

    while queue:
        current = queue.popleft()
        parents = parent_indices.get(current, [])

        for parent in parents:
            if parent is not None and parent not in visited:
                ancestors.add(parent)
                visited.add(parent)
                queue.append(parent)

    logger.debug(
        "genealogy.ancestors_found",
        candidate_idx=candidate_idx,
        ancestor_count=len(ancestors),
        ancestors=sorted(ancestors),
    )

    return ancestors


def find_common_ancestor(
    idx1: int, idx2: int, parent_indices: dict[int, list[int | None]]
) -> int | None:
    """Find the most recent common ancestor of two candidates.

    Identifies the common ancestor with the highest index (most recent) between
    two candidates. Returns None if no common ancestor exists (separate lineages).

    Args:
        idx1: First candidate index.
        idx2: Second candidate index.
        parent_indices: Mapping of candidate index to parent indices list.

    Returns:
        Index of the most recent common ancestor, or None if no common ancestor exists.

    Examples:
        Candidates sharing a seed:

        ```python
        parent_indices = {0: [None], 1: [0], 2: [0]}
        ancestor = find_common_ancestor(1, 2, parent_indices)
        # Returns: 0
        ```

        One candidate is ancestor of the other:

        ```python
        parent_indices = {0: [None], 1: [0], 2: [1]}
        ancestor = find_common_ancestor(1, 2, parent_indices)
        # Returns: 1 (1 is ancestor of 2)
        ```

        No common ancestor:

        ```python
        parent_indices = {0: [None], 1: [0], 2: [None], 3: [2]}
        ancestor = find_common_ancestor(1, 3, parent_indices)
        # Returns: None (separate lineages)
        ```

    Note:
        Operations return the highest-indexed common ancestor to ensure we find the most
        recent shared ancestor, which is most useful for merge operations.
    """
    # If same candidate, return itself
    if idx1 == idx2:
        logger.debug(
            "genealogy.ancestor_found",
            idx1=idx1,
            idx2=idx2,
            ancestor_idx=idx1,
            relationship="same_candidate",
        )
        return idx1

    ancestors1 = get_ancestors(idx1, parent_indices)
    ancestors2 = get_ancestors(idx2, parent_indices)

    # Include the candidates themselves in case one is an ancestor of the other
    if idx1 in ancestors2:
        # idx1 is an ancestor of idx2
        logger.debug(
            "genealogy.ancestor_found",
            idx1=idx1,
            idx2=idx2,
            ancestor_idx=idx1,
            relationship="idx1_is_ancestor",
        )
        return idx1

    if idx2 in ancestors1:
        # idx2 is an ancestor of idx1
        logger.debug(
            "genealogy.ancestor_found",
            idx1=idx1,
            idx2=idx2,
            ancestor_idx=idx2,
            relationship="idx2_is_ancestor",
        )
        return idx2

    # Find common ancestors
    common = ancestors1 & ancestors2

    if not common:
        logger.debug(
            "genealogy.no_common_ancestor",
            idx1=idx1,
            idx2=idx2,
        )
        return None

    # Return most recent (highest index) common ancestor
    ancestor_idx = max(common)
    logger.debug(
        "genealogy.common_ancestor_found",
        idx1=idx1,
        idx2=idx2,
        ancestor_idx=ancestor_idx,
        all_common=sorted(common),
    )

    return ancestor_idx


def filter_ancestors_by_score(
    ancestors: set[int],
    candidate_scores: dict[int, dict[int, float]],
    min_avg_score: float,
) -> set[int]:
    """Filter ancestors by minimum average score constraint.

    Removes ancestors that don't meet the minimum average score requirement,
    ensuring only viable ancestors are considered for merge operations.

    Args:
        ancestors: Set of ancestor candidate indices to filter.
        candidate_scores: Mapping of candidate index to per-example scores.
        min_avg_score: Minimum average score threshold.

    Returns:
        Set of ancestor indices that meet the score constraint.

    Examples:
        Filtering ancestors by score:

        ```python
        ancestors = {0, 1, 2}
        candidate_scores = {
            0: {0: 0.5, 1: 0.5},  # avg: 0.5
            1: {0: 0.7, 1: 0.7},  # avg: 0.7
            2: {0: 0.9, 1: 0.9},  # avg: 0.9
        }
        filtered = filter_ancestors_by_score(
            ancestors, candidate_scores, min_avg_score=0.6
        )
        # Returns: {1, 2} (0 filtered out)
        ```

    Note:
        Operations exclude ancestors without scores from the result.
    """
    from statistics import fmean

    filtered: set[int] = set()

    for ancestor_idx in ancestors:
        scores = candidate_scores.get(ancestor_idx)
        if scores:
            avg_score = fmean(scores.values())
            if avg_score >= min_avg_score:
                filtered.add(ancestor_idx)

    logger.debug(
        "genealogy.ancestors_filtered",
        original_count=len(ancestors),
        filtered_count=len(filtered),
        min_avg_score=min_avg_score,
    )

    return filtered


def detect_component_divergence(
    ancestor_components: dict[str, str],
    parent_components: dict[str, str],
) -> set[str]:
    """Detect which components have diverged from ancestor to parent.

    Identifies component keys where the parent's value differs from the
    ancestor's value, indicating where improvements or changes occurred.

    Args:
        ancestor_components: Component dictionary from ancestor candidate.
        parent_components: Component dictionary from parent candidate.

    Returns:
        Set of component keys that have diverged (changed values).

    Examples:
        Detecting divergence:

        ```python
        ancestor = {"instruction": "A", "output_schema": "B"}
        parent = {"instruction": "A", "output_schema": "C"}
        divergence = detect_component_divergence(ancestor, parent)
        # Returns: {"output_schema"}
        ```

    Note:
        Only checks components present in the ancestor. Components added by
        the parent are ignored. Missing components are not considered diverged.
    """
    diverged: set[str] = set()

    for key in ancestor_components:
        if key in parent_components:
            if ancestor_components[key] != parent_components[key]:
                diverged.add(key)

    logger.debug(
        "genealogy.component_divergence",
        diverged_components=sorted(diverged),
        total_components=len(ancestor_components),
    )

    return diverged


def has_desirable_predictors(
    ancestor_components: dict[str, str],
    parent1_components: dict[str, str],
    parent2_components: dict[str, str],
) -> bool:
    """Check if merge has desirable complementary component changes.

    A merge is desirable when parents have changed different components
    from the ancestor, indicating complementary improvements that can
    be combined.

    Args:
        ancestor_components: Component dictionary from common ancestor.
        parent1_components: Component dictionary from first parent.
        parent2_components: Component dictionary from second parent.

    Returns:
        True if parents have complementary component changes, False otherwise.

    Examples:
        Complementary changes (desirable):

        ```python
        ancestor = {"instruction": "A", "output_schema": "B"}
        parent1 = {"instruction": "A", "output_schema": "C"}  # output_schema changed
        parent2 = {"instruction": "D", "output_schema": "B"}  # instruction changed
        assert has_desirable_predictors(ancestor, parent1, parent2) is True
        ```

        Overlapping changes (less desirable):

        ```python
        ancestor = {"instruction": "A", "output_schema": "B"}
        parent1 = {"instruction": "C", "output_schema": "B"}
        parent2 = {"instruction": "C", "output_schema": "B"}  # Same change
        assert has_desirable_predictors(ancestor, parent1, parent2) is False
        ```

    Note:
        Operations return False if no components have changed, or if both parents
        changed the same components identically.
    """
    divergence1 = detect_component_divergence(ancestor_components, parent1_components)
    divergence2 = detect_component_divergence(ancestor_components, parent2_components)

    # No divergence means no desirable merge
    if not divergence1 or not divergence2:
        logger.debug(
            "genealogy.no_desirable_predictors",
            reason="no_divergence",
            divergence1=sorted(divergence1),
            divergence2=sorted(divergence2),
        )
        return False

    # Check if divergences are complementary (different components or different values)
    # If they overlap but have different values, that's still desirable
    if divergence1 != divergence2:
        # Different components changed - complementary
        logger.debug(
            "genealogy.desirable_predictors",
            divergence1=sorted(divergence1),
            divergence2=sorted(divergence2),
            reason="complementary_components",
        )
        return True

    # Same components changed - check if values differ
    for component in divergence1:
        if parent1_components.get(component) != parent2_components.get(component):
            # Same component, different values - still desirable
            logger.debug(
                "genealogy.desirable_predictors",
                divergence1=sorted(divergence1),
                divergence2=sorted(divergence2),
                reason="different_values",
            )
            return True

    # Same components, same values - not desirable
    logger.debug(
        "genealogy.no_desirable_predictors",
        reason="identical_changes",
        divergence1=sorted(divergence1),
        divergence2=sorted(divergence2),
    )
    return False
