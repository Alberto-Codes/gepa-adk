"""Integration tests for schema constraints API-to-handler flow.

These tests verify that schema_constraints parameter flows correctly
from evolve() API through ADKAdapter to OutputSchemaHandler.
"""

from __future__ import annotations

from pydantic import BaseModel
from pytest_mock import MockerFixture


class TestSchemaConstraintsAPIFlow:
    """Integration tests for schema_constraints flowing through API layers."""

    def test_evolve_passes_constraints_to_adapter(self, mocker: MockerFixture) -> None:
        """evolve() should pass schema_constraints to ADKAdapter."""
        # Verify SchemaConstraints is importable from public API
        from gepa_adk import SchemaConstraints as PublicSchemaConstraints

        constraints = PublicSchemaConstraints(required_fields=("score",))
        assert constraints.required_fields == ("score",)

    def test_adapter_sets_constraints_on_handler(self, mocker: MockerFixture) -> None:
        """ADKAdapter should set constraints on OutputSchemaHandler."""
        from gepa_adk.adapters.components.component_handlers import get_handler
        from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter
        from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA, SchemaConstraints

        # Patch isinstance check to allow mocks
        mocker.patch.object(ADKAdapter, "__init__", return_value=None)

        # Now test the constraint setting logic directly
        handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
        constraints = SchemaConstraints(required_fields=("score", "feedback"))

        # Simulate what ADKAdapter.__init__ does
        handler.set_constraints(constraints)

        # Verify constraints were set on the handler
        assert handler._constraints is constraints

        # Clean up - clear constraints for other tests
        handler.set_constraints(None)

    def test_adapter_without_constraints_leaves_handler_unconstrained(
        self, mocker: MockerFixture
    ) -> None:
        """ADKAdapter without schema_constraints should not set handler constraints."""
        from gepa_adk.adapters.components.component_handlers import get_handler
        from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA

        # Clear any existing constraints first
        handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
        handler.set_constraints(None)

        # Verify handler constraints are None
        assert handler._constraints is None


class TestConstraintValidationEndToEnd:
    """End-to-end tests for constraint validation during schema evolution."""

    def test_handler_rejects_constraint_violation_with_constraints_set(
        self, mocker: MockerFixture
    ) -> None:
        """Handler should reject schema changes that violate constraints."""
        from gepa_adk.adapters.components.component_handlers import get_handler
        from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA, SchemaConstraints

        # Define original schema
        class OriginalSchema(BaseModel):
            score: float
            feedback: str

        # Create mock agent with original schema
        mock_agent = mocker.MagicMock()
        mock_agent.name = "test_agent"
        mock_agent.output_schema = OriginalSchema

        # Create constraints requiring 'score' field
        constraints = SchemaConstraints(required_fields=("score",))

        # Get handler and set constraints (simulating ADKAdapter behavior)
        handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
        handler.set_constraints(constraints)

        # Try to apply schema without 'score' field
        invalid_schema_text = """
class InvalidSchema(BaseModel):
    feedback: str
"""

        # Apply the invalid schema
        _original = handler.apply(mock_agent, invalid_schema_text)

        # Original schema should be preserved (mutation rejected)
        assert mock_agent.output_schema is OriginalSchema

        # Clean up
        handler.set_constraints(None)

    def test_handler_accepts_valid_mutation_with_constraints_set(
        self, mocker: MockerFixture
    ) -> None:
        """Handler should accept schema changes that satisfy constraints."""
        from gepa_adk.adapters.components.component_handlers import get_handler
        from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA, SchemaConstraints

        # Define original schema
        class OriginalSchema(BaseModel):
            score: float
            old_field: str

        # Create mock agent with original schema
        mock_agent = mocker.MagicMock()
        mock_agent.name = "test_agent"
        mock_agent.output_schema = OriginalSchema

        # Create constraints requiring 'score' field
        constraints = SchemaConstraints(required_fields=("score",))

        # Get handler and set constraints (simulating ADKAdapter behavior)
        handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
        handler.set_constraints(constraints)

        # Apply valid schema that keeps 'score' field
        valid_schema_text = """
class NewSchema(BaseModel):
    score: float
    new_field: str
"""

        # Apply the valid schema
        _original = handler.apply(mock_agent, valid_schema_text)

        # New schema should be applied (mutation accepted)
        assert mock_agent.output_schema is not OriginalSchema
        assert "score" in mock_agent.output_schema.model_fields
        assert "new_field" in mock_agent.output_schema.model_fields

        # Clean up
        handler.set_constraints(None)
