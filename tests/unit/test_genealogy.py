"""Unit tests for genealogy tracking functions.

Note:
    These tests verify ancestor traversal and common ancestor finding
    for merge operations in evolution.
"""

from __future__ import annotations

import pytest

from gepa_adk.engine.genealogy import find_common_ancestor, get_ancestors

pytestmark = pytest.mark.unit


class TestGetAncestors:
    """Tests for get_ancestors() function."""

    def test_seed_candidate_has_no_ancestors(self) -> None:
        """Seed candidates should have empty ancestor set."""
        parent_indices: dict[int, list[int | None]] = {0: [None]}

        ancestors = get_ancestors(0, parent_indices)

        assert ancestors == set()

    def test_single_parent_returns_parent(self) -> None:
        """Candidates with single parent return that parent as ancestor."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],  # seed
            1: [0],  # child of 0
        }

        ancestors = get_ancestors(1, parent_indices)

        assert ancestors == {0}

    def test_multiple_generations_returns_all_ancestors(self) -> None:
        """Ancestors should include all ancestors transitively."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],  # seed
            1: [0],  # child of 0
            2: [1],  # child of 1
            3: [2],  # child of 2
        }

        ancestors = get_ancestors(3, parent_indices)

        assert ancestors == {0, 1, 2}

    def test_merge_candidate_has_both_parents_as_ancestors(self) -> None:
        """Merged candidates should have both parents as ancestors."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],  # seed
            1: [0],  # child of 0
            2: [0],  # child of 0
            3: [1, 2],  # merge of 1 and 2
        }

        ancestors = get_ancestors(3, parent_indices)

        assert ancestors == {0, 1, 2}

    def test_cycle_detection_prevents_infinite_loop(self) -> None:
        """Cycle detection should prevent infinite loops."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],
            1: [0],
            2: [3],
            3: [2],
        }

        ancestors = get_ancestors(2, parent_indices)

        assert ancestors == {3}
        # Should not include 2 (itself)

    def test_missing_candidate_returns_empty_set(self) -> None:
        """Missing candidate indices should return empty set."""
        parent_indices: dict[int, list[int | None]] = {0: [None]}

        ancestors = get_ancestors(999, parent_indices)

        assert ancestors == set()


class TestFindCommonAncestor:
    """Tests for find_common_ancestor() function."""

    def test_no_common_ancestor_returns_none(self) -> None:
        """Candidates from separate lineages should have no common ancestor."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],  # seed 1
            1: [0],
            2: [None],  # seed 2 (separate lineage)
            3: [2],
        }

        ancestor = find_common_ancestor(1, 3, parent_indices)

        assert ancestor is None

    def test_shared_seed_returns_seed(self) -> None:
        """Candidates sharing a seed should return that seed."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],  # seed
            1: [0],
            2: [0],
        }

        ancestor = find_common_ancestor(1, 2, parent_indices)

        assert ancestor == 0

    def test_most_recent_common_ancestor_selected(self) -> None:
        """Should return the most recent (highest index) common ancestor."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],  # seed
            1: [0],
            2: [1],  # child of 1
            3: [1],  # child of 1
            4: [2],  # child of 2
            5: [3],  # child of 3
        }

        ancestor = find_common_ancestor(4, 5, parent_indices)

        # Both 4 and 5 have ancestors: {0, 1, 2} and {0, 1, 3}
        # Common ancestors: {0, 1}
        # Most recent: 1
        assert ancestor == 1

    def test_one_is_ancestor_of_other_returns_ancestor(self) -> None:
        """When one candidate is an ancestor of the other, return that ancestor."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],
            1: [0],
            2: [1],
        }

        ancestor = find_common_ancestor(1, 2, parent_indices)

        # 1 is an ancestor of 2, so 1 is the common ancestor
        assert ancestor == 1

    def test_same_candidate_returns_itself(self) -> None:
        """Same candidate should return itself as common ancestor."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],
            1: [0],
        }

        ancestor = find_common_ancestor(1, 1, parent_indices)

        assert ancestor == 1

    def test_merge_candidates_with_shared_ancestor(self) -> None:
        """Merged candidates should find common ancestor correctly."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],  # seed
            1: [0],
            2: [0],
            3: [1, 2],  # merge of 1 and 2
            4: [1],
            5: [3, 4],  # merge of 3 and 4
        }

        ancestor = find_common_ancestor(3, 4, parent_indices)

        # 3 has ancestors {0, 1, 2}, 4 has ancestors {0, 1}
        # Common: {0, 1}, most recent: 1
        assert ancestor == 1


class TestAncestryTraversalWithDeepTrees:
    """Tests for ancestry traversal with deep genealogical trees."""

    def test_deep_linear_tree(self) -> None:
        """Test ancestor traversal with a deep linear genealogy."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],
        }
        # Create a chain: 0 -> 1 -> 2 -> ... -> 9
        for i in range(1, 10):
            parent_indices[i] = [i - 1]

        ancestors = get_ancestors(9, parent_indices)

        assert ancestors == set(range(9))  # All ancestors except itself

    def test_wide_branching_tree(self) -> None:
        """Test ancestor traversal with wide branching."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],  # seed
        }
        # Create 5 branches from seed
        for branch in range(1, 6):
            parent_indices[branch] = [0]
            # Each branch has 2 children
            parent_indices[branch * 10] = [branch]
            parent_indices[branch * 10 + 1] = [branch]

        # Check ancestors of a leaf node
        ancestors = get_ancestors(10, parent_indices)

        assert ancestors == {0, 1}

    def test_merge_in_deep_tree(self) -> None:
        """Test common ancestor finding in a deep tree with merges."""
        parent_indices: dict[int, list[int | None]] = {
            0: [None],
        }
        # Create two branches
        for i in range(1, 5):
            parent_indices[i] = [i - 1]
        for i in range(10, 14):
            parent_indices[i] = [i - 1] if i > 10 else [0]

        # Merge at the end
        parent_indices[20] = [4, 13]

        ancestor = find_common_ancestor(4, 13, parent_indices)

        # Both branches start from 0
        assert ancestor == 0


class TestAncestorFilteringByScoreConstraints:
    """Tests for ancestor filtering by score constraints."""

    def test_filter_ancestors_by_min_score(self) -> None:
        """Test filtering ancestors that don't meet minimum score requirement."""
        from gepa_adk.engine.genealogy import filter_ancestors_by_score

        parent_indices: dict[int, list[int | None]] = {
            0: [None],
            1: [0],
            2: [1],
        }
        candidate_scores: dict[int, dict[int, float]] = {
            0: {0: 0.5, 1: 0.5},  # avg: 0.5
            1: {0: 0.7, 1: 0.7},  # avg: 0.7
            2: {0: 0.9, 1: 0.9},  # avg: 0.9
        }

        ancestors = get_ancestors(2, parent_indices)
        filtered = filter_ancestors_by_score(
            ancestors, candidate_scores, min_avg_score=0.6
        )

        # Should filter out 0 (0.5 < 0.6), keep 1 (0.7 >= 0.6)
        assert filtered == {1}

    def test_filter_keeps_all_above_threshold(self) -> None:
        """Test that all ancestors above threshold are kept."""
        from gepa_adk.engine.genealogy import filter_ancestors_by_score

        parent_indices: dict[int, list[int | None]] = {
            0: [None],
            1: [0],
            2: [1],
        }
        candidate_scores: dict[int, dict[int, float]] = {
            0: {0: 0.8, 1: 0.8},
            1: {0: 0.9, 1: 0.9},
            2: {0: 1.0, 1: 1.0},
        }

        ancestors = get_ancestors(2, parent_indices)
        filtered = filter_ancestors_by_score(
            ancestors, candidate_scores, min_avg_score=0.7
        )

        assert filtered == {0, 1}


class TestComponentDivergenceDetection:
    """Tests for component divergence detection."""

    def test_detect_component_divergence(self) -> None:
        """Test detecting which components have diverged from ancestor."""
        from gepa_adk.engine.genealogy import detect_component_divergence

        ancestor_components = {"instruction": "A", "output_schema": "B"}
        parent1_components = {
            "instruction": "A",
            "output_schema": "C",
        }  # output_schema changed
        parent2_components = {
            "instruction": "D",
            "output_schema": "B",
        }  # instruction changed

        divergence1 = detect_component_divergence(
            ancestor_components, parent1_components
        )
        divergence2 = detect_component_divergence(
            ancestor_components, parent2_components
        )

        assert divergence1 == {"output_schema"}
        assert divergence2 == {"instruction"}

    def test_no_divergence_when_identical(self) -> None:
        """Test that identical components show no divergence."""
        from gepa_adk.engine.genealogy import detect_component_divergence

        ancestor_components = {"instruction": "A", "output_schema": "B"}
        parent_components = {"instruction": "A", "output_schema": "B"}

        divergence = detect_component_divergence(ancestor_components, parent_components)

        assert divergence == set()

    def test_all_components_diverged(self) -> None:
        """Test when all components have diverged."""
        from gepa_adk.engine.genealogy import detect_component_divergence

        ancestor_components = {"instruction": "A", "output_schema": "B"}
        parent_components = {"instruction": "C", "output_schema": "D"}

        divergence = detect_component_divergence(ancestor_components, parent_components)

        assert divergence == {"instruction", "output_schema"}


class TestHasDesirablePredictors:
    """Tests for has_desirable_predictors check."""

    def test_has_desirable_predictors_when_complementary(self) -> None:
        """Test that complementary component changes are desirable."""
        from gepa_adk.engine.genealogy import has_desirable_predictors

        ancestor_components = {"instruction": "A", "output_schema": "B"}
        parent1_components = {
            "instruction": "A",
            "output_schema": "C",
        }  # output_schema changed
        parent2_components = {
            "instruction": "D",
            "output_schema": "B",
        }  # instruction changed

        # Parents have complementary changes (different components)
        assert (
            has_desirable_predictors(
                ancestor_components, parent1_components, parent2_components
            )
            is True
        )

    def test_no_desirable_predictors_when_same_changes(self) -> None:
        """Test that identical changes are not desirable."""
        from gepa_adk.engine.genealogy import has_desirable_predictors

        ancestor_components = {"instruction": "A", "output_schema": "B"}
        parent1_components = {"instruction": "C", "output_schema": "B"}
        parent2_components = {
            "instruction": "C",
            "output_schema": "B",
        }  # Same as parent1

        # Both changed the same component the same way
        assert (
            has_desirable_predictors(
                ancestor_components, parent1_components, parent2_components
            )
            is False
        )

    def test_no_desirable_predictors_when_no_changes(self) -> None:
        """Test that no changes from ancestor are not desirable."""
        from gepa_adk.engine.genealogy import has_desirable_predictors

        ancestor_components = {"instruction": "A", "output_schema": "B"}
        parent1_components = {"instruction": "A", "output_schema": "B"}
        parent2_components = {"instruction": "A", "output_schema": "B"}

        # No changes from ancestor
        assert (
            has_desirable_predictors(
                ancestor_components, parent1_components, parent2_components
            )
            is False
        )
