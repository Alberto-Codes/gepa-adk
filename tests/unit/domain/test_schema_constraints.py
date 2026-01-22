"""Unit tests for SchemaConstraints dataclass.

These tests verify the SchemaConstraints dataclass behavior including
construction, attribute access, and equality.
"""

from __future__ import annotations


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

    def test_not_hashable_due_to_dict_field(self) -> None:
        """SchemaConstraints is not hashable due to preserve_types dict field.

        Note: This is acceptable for the use case - constraints are stored as
        references in handler._constraints, not used in sets or as dict keys.
        """
        import pytest

        from gepa_adk.domain.types import SchemaConstraints

        # Even with empty preserve_types, the dict makes it unhashable
        constraints = SchemaConstraints(required_fields=("score",))

        with pytest.raises(TypeError, match="unhashable type"):
            hash(constraints)


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
