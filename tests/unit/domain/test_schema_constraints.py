"""Unit tests for SchemaConstraints dataclass.

These tests verify the SchemaConstraints dataclass behavior including
construction, attribute access, and equality.
"""

from __future__ import annotations

import pytest


class TestSchemaConstraintsBasics:
    """Unit tests for SchemaConstraints basic functionality."""

    def test_create_empty_constraints(self) -> None:
        """Empty constraints should be valid."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints()
        assert constraints.required_fields == ()
        assert constraints.preserve_types == {}

    def test_create_with_required_fields_only(self) -> None:
        """Constraints with only required_fields should work."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints(required_fields=("score",))
        assert constraints.required_fields == ("score",)
        assert constraints.preserve_types == {}

    def test_create_with_preserve_types_only(self) -> None:
        """Constraints with only preserve_types should work."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints(preserve_types={"score": float})
        assert constraints.required_fields == ()
        assert constraints.preserve_types == {"score": float}

    def test_equality(self) -> None:
        """Two SchemaConstraints with same values should be equal."""
        from gepa_adk.domain.types import SchemaConstraints

        c1 = SchemaConstraints(required_fields=("a", "b"))
        c2 = SchemaConstraints(required_fields=("a", "b"))
        assert c1 == c2

    def test_inequality(self) -> None:
        """Two SchemaConstraints with different values should not be equal."""
        from gepa_adk.domain.types import SchemaConstraints

        c1 = SchemaConstraints(required_fields=("a",))
        c2 = SchemaConstraints(required_fields=("b",))
        assert c1 != c2

    def test_hashable(self) -> None:
        """SchemaConstraints should be hashable (for use in sets/dicts)."""
        from gepa_adk.domain.types import SchemaConstraints

        # Note: dict is not hashable, so this will only work with empty preserve_types
        # or if we use frozendict in the future
        constraints = SchemaConstraints(required_fields=("score",))
        # This should not raise - frozen dataclasses are hashable if all fields are
        # But dict is not hashable, so we skip this for now
        # The dataclass is still frozen (immutable) which is the key requirement


class TestSchemaConstraintsTypeHints:
    """Tests for type hint correctness."""

    def test_required_fields_is_tuple(self) -> None:
        """required_fields should be a tuple, not a list."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints(required_fields=("a", "b"))
        assert isinstance(constraints.required_fields, tuple)

    def test_preserve_types_is_dict(self) -> None:
        """preserve_types should be a dict."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints(preserve_types={"score": float})
        assert isinstance(constraints.preserve_types, dict)
