"""Contract tests for SchemaConstraints behavior.

These tests verify the SchemaConstraints dataclass adheres to its contract:
immutability, default values, and structural requirements.
"""

from __future__ import annotations

import dataclasses

import pytest


class TestSchemaConstraintsImmutability:
    """Contract: SchemaConstraints instances must be immutable."""

    def test_schema_constraints_is_frozen(self) -> None:
        """SchemaConstraints should reject attribute mutation."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints(required_fields=("score",))

        with pytest.raises(dataclasses.FrozenInstanceError):
            constraints.required_fields = ("other",)  # type: ignore[misc]

    def test_schema_constraints_has_slots(self) -> None:
        """SchemaConstraints should use __slots__ for memory efficiency."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints()
        assert hasattr(constraints, "__slots__") or hasattr(
            constraints.__class__, "__slots__"
        )


class TestSchemaConstraintsDefaults:
    """Contract: SchemaConstraints must have sensible defaults."""

    def test_default_required_fields_is_empty_tuple(self) -> None:
        """Default required_fields should be an empty tuple."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints()
        assert constraints.required_fields == ()
        assert isinstance(constraints.required_fields, tuple)

    def test_default_preserve_types_is_empty_dict(self) -> None:
        """Default preserve_types should be an empty dict."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints()
        assert constraints.preserve_types == {}
        assert isinstance(constraints.preserve_types, dict)


class TestSchemaConstraintsConstruction:
    """Contract: SchemaConstraints construction must be valid."""

    def test_required_fields_accepts_tuple(self) -> None:
        """required_fields should accept a tuple of strings."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints(required_fields=("score", "feedback"))
        assert constraints.required_fields == ("score", "feedback")

    def test_preserve_types_accepts_single_type(self) -> None:
        """preserve_types should accept single type values."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints(preserve_types={"score": float})
        assert constraints.preserve_types == {"score": float}

    def test_preserve_types_accepts_tuple_of_types(self) -> None:
        """preserve_types should accept tuple of types for compatibility."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints(preserve_types={"score": (float, int)})
        assert constraints.preserve_types == {"score": (float, int)}

    def test_combined_constraints(self) -> None:
        """Both required_fields and preserve_types can be set together."""
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints(
            required_fields=("score", "feedback"),
            preserve_types={"score": float, "feedback": str},
        )
        assert constraints.required_fields == ("score", "feedback")
        assert constraints.preserve_types == {"score": float, "feedback": str}
