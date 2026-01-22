"""Unit tests for schema constraint validation.

These tests verify the validate_schema_against_constraints function
including required field checking and performance requirements.
"""

from __future__ import annotations

import time

from pydantic import BaseModel


class TestRequiredFieldValidation:
    """Unit tests for required field validation."""

    def test_empty_constraints_always_pass(self) -> None:
        """Empty constraints should allow any schema change."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float
            feedback: str

        class ProposedSchema(BaseModel):
            totally_different: int

        constraints = SchemaConstraints()  # No constraints

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert is_valid
        assert violations == []

    def test_no_original_schema_skips_validation(self) -> None:
        """If original schema is None, validation should pass."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class ProposedSchema(BaseModel):
            score: float

        constraints = SchemaConstraints(required_fields=("score",))

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema,
            None,
            constraints,  # type: ignore[arg-type]
        )

        assert is_valid
        assert violations == []


class TestValidationPerformance:
    """Tests for validation performance requirements."""

    def test_validation_under_1ms(self) -> None:
        """Validation should complete in under 1ms."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            field1: str
            field2: int
            field3: float
            field4: bool
            field5: list[str]

        class ProposedSchema(BaseModel):
            field1: str
            field2: int
            field3: float
            field4: bool
            field5: list[str]

        constraints = SchemaConstraints(
            required_fields=("field1", "field2", "field3"),
        )

        # Warm up
        validate_schema_against_constraints(ProposedSchema, OriginalSchema, constraints)

        # Time the validation
        start = time.perf_counter()
        for _ in range(100):
            validate_schema_against_constraints(
                ProposedSchema, OriginalSchema, constraints
            )
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / 100) * 1000
        assert avg_time_ms < 1.0, f"Validation took {avg_time_ms:.3f}ms on average"


class TestEdgeCases:
    """Edge case tests for validation."""

    def test_constraint_field_not_in_original(self) -> None:
        """Constraint referencing non-existent field should be skipped."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float

        class ProposedSchema(BaseModel):
            score: float

        # Constraint references field that doesn't exist in original
        constraints = SchemaConstraints(required_fields=("nonexistent",))

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        # Should pass - can't require a field that was never there
        assert is_valid
        assert violations == []


class TestTypePreservation:
    """Unit tests for type preservation validation."""

    def test_exact_type_match_passes(self) -> None:
        """Exact type match should pass validation."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float

        class ProposedSchema(BaseModel):
            score: float

        constraints = SchemaConstraints(preserve_types={"score": float})

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert is_valid
        assert violations == []

    def test_type_mismatch_fails(self) -> None:
        """Type mismatch should fail validation."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float

        class ProposedSchema(BaseModel):
            score: str  # Changed type

        constraints = SchemaConstraints(preserve_types={"score": float})

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert not is_valid
        assert len(violations) == 1

    def test_type_not_in_original_skipped(self) -> None:
        """Type constraint for non-existent field should be skipped."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            feedback: str

        class ProposedSchema(BaseModel):
            feedback: str

        # Constraint references field that doesn't exist in original
        constraints = SchemaConstraints(preserve_types={"score": float})

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert is_valid
        assert violations == []

    def test_field_removed_with_type_constraint(self) -> None:
        """Field removal should be caught by type constraint."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float

        class ProposedSchema(BaseModel):
            other: str  # score removed

        constraints = SchemaConstraints(preserve_types={"score": float})

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert not is_valid
        assert len(violations) == 1


class TestTupleTypeMatching:
    """Unit tests for tuple type matching in preserve_types."""

    def test_first_type_in_tuple_matches(self) -> None:
        """First type in tuple should match."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float

        class ProposedSchema(BaseModel):
            score: float  # Matches first type in tuple

        constraints = SchemaConstraints(preserve_types={"score": (float, int)})

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert is_valid
        assert violations == []

    def test_second_type_in_tuple_matches(self) -> None:
        """Second type in tuple should match."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float

        class ProposedSchema(BaseModel):
            score: int  # Matches second type in tuple

        constraints = SchemaConstraints(preserve_types={"score": (float, int)})

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert is_valid
        assert violations == []

    def test_type_not_in_tuple_fails(self) -> None:
        """Type not in tuple should fail."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float

        class ProposedSchema(BaseModel):
            score: str  # Not in (float, int)

        constraints = SchemaConstraints(preserve_types={"score": (float, int)})

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert not is_valid
        assert len(violations) == 1

    def test_multiple_type_constraints(self) -> None:
        """Multiple type constraints should all be checked."""
        from gepa_adk.domain.types import SchemaConstraints
        from gepa_adk.utils.schema_utils import validate_schema_against_constraints

        class OriginalSchema(BaseModel):
            score: float
            feedback: str

        class ProposedSchema(BaseModel):
            score: int  # Wrong - should be float
            feedback: int  # Wrong - should be str

        constraints = SchemaConstraints(
            preserve_types={"score": float, "feedback": str}
        )

        is_valid, violations = validate_schema_against_constraints(
            ProposedSchema, OriginalSchema, constraints
        )

        assert not is_valid
        assert len(violations) == 2
