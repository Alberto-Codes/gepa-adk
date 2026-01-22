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
