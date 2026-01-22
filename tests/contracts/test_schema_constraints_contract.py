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


class TestRequiredFieldValidation:
    """Contract: Required field validation behavior."""

    def test_required_field_present_passes(self) -> None:
        """Proposed schema with required field passes validation."""
        from pydantic import BaseModel

        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float
            feedback: str

        class ProposedSchema(BaseModel):
            score: float
            result: str  # feedback removed, but not required

        constraints = SchemaConstraints(required_fields=("score",))

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert is_valid
        assert violations == []

    def test_required_field_missing_fails(self) -> None:
        """Proposed schema missing required field fails validation."""
        from pydantic import BaseModel

        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float
            feedback: str

        class ProposedSchema(BaseModel):
            feedback: str  # score removed!

        constraints = SchemaConstraints(required_fields=("score",))

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert not is_valid
        assert len(violations) == 1
        assert "score" in violations[0]

    def test_multiple_required_fields_all_present(self) -> None:
        """All required fields present passes validation."""
        from pydantic import BaseModel

        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float
            feedback: str
            details: str

        class ProposedSchema(BaseModel):
            score: float
            feedback: str
            new_field: int  # details replaced with new_field

        constraints = SchemaConstraints(required_fields=("score", "feedback"))

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert is_valid
        assert violations == []

    def test_multiple_required_fields_some_missing(self) -> None:
        """Some required fields missing reports all violations."""
        from pydantic import BaseModel

        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float
            feedback: str
            result: str

        class ProposedSchema(BaseModel):
            result: str  # both score and feedback removed!

        constraints = SchemaConstraints(required_fields=("score", "feedback"))

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert not is_valid
        assert len(violations) == 2


class TestTypePreservationValidation:
    """Contract: Type preservation validation behavior."""

    def test_same_type_passes(self) -> None:
        """Proposed field with same type passes validation."""
        from pydantic import BaseModel

        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float
            feedback: str

        class ProposedSchema(BaseModel):
            score: float  # Same type
            result: str

        constraints = SchemaConstraints(preserve_types={"score": float})

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert is_valid
        assert violations == []

    def test_incompatible_type_fails(self) -> None:
        """Proposed field with incompatible type fails validation."""
        from pydantic import BaseModel

        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float
            feedback: str

        class ProposedSchema(BaseModel):
            score: str  # Changed from float to str!
            feedback: str

        constraints = SchemaConstraints(preserve_types={"score": float})

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert not is_valid
        assert len(violations) == 1
        assert "score" in violations[0]
        assert "type" in violations[0].lower()

    def test_tuple_types_allows_compatible(self) -> None:
        """Tuple of types allows any compatible type."""
        from pydantic import BaseModel

        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float

        class ProposedSchema(BaseModel):
            score: int  # int is compatible with (float, int)

        constraints = SchemaConstraints(preserve_types={"score": (float, int)})

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert is_valid
        assert violations == []

    def test_combined_required_and_type_constraints(self) -> None:
        """Both required_fields and preserve_types are validated together."""
        from pydantic import BaseModel

        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float
            feedback: str
            details: str

        class ProposedSchema(BaseModel):
            score: str  # Wrong type
            # feedback missing!
            details: str

        constraints = SchemaConstraints(
            required_fields=("score", "feedback"),
            preserve_types={"score": float},
        )

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert not is_valid
        assert len(violations) == 2  # Missing feedback + wrong score type
