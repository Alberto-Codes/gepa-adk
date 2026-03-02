"""Integration tests for schema-constrained evolution.

These tests verify end-to-end schema constraint behavior during evolution,
including backward compatibility when no constraints are specified.
"""

from __future__ import annotations

from pydantic import BaseModel
from pytest_mock import MockerFixture


class TestSchemaConstrainedEvolution:
    """Integration tests for schema-constrained evolution scenarios."""

    def test_required_field_constraint_rejects_removal(
        self, mocker: MockerFixture
    ) -> None:
        """Evolution should reject schema changes that remove required fields."""
        from gepa_adk.adapters.components.component_handlers import get_handler
        from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA, SchemaConstraints

        # Original critic schema with score and feedback
        class CriticSchema(BaseModel):
            score: float
            feedback: str
            details: str

        # Constraint: score must be preserved
        constraints = SchemaConstraints(required_fields=("score",))

        # Mock agent
        mock_agent = mocker.MagicMock()
        mock_agent.output_schema = CriticSchema

        # Get handler and set constraints
        handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
        handler.set_constraints(constraints)

        # Try to evolve to a schema without score
        invalid_schema = """
class EvolvedSchema(BaseModel):
    feedback: str
    details: str
    new_field: int
"""
        _original = handler.apply(mock_agent, invalid_schema)

        # Schema should NOT change - mutation rejected
        assert mock_agent.output_schema is CriticSchema
        assert "score" in mock_agent.output_schema.model_fields

        # Clean up
        handler.set_constraints(None)

    def test_type_constraint_rejects_incompatible_change(
        self, mocker: MockerFixture
    ) -> None:
        """Evolution should reject schema changes that break type constraints."""
        from gepa_adk.adapters.components.component_handlers import get_handler
        from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA, SchemaConstraints

        # Original schema
        class OriginalSchema(BaseModel):
            score: float
            result: str

        # Constraint: score must remain float
        constraints = SchemaConstraints(preserve_types={"score": float})

        # Mock agent
        mock_agent = mocker.MagicMock()
        mock_agent.output_schema = OriginalSchema

        # Get handler and set constraints
        handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
        handler.set_constraints(constraints)

        # Try to evolve score to a string type
        invalid_schema = """
class EvolvedSchema(BaseModel):
    score: str
    result: str
"""
        _original = handler.apply(mock_agent, invalid_schema)

        # Schema should NOT change - type constraint violated
        assert mock_agent.output_schema is OriginalSchema

        # Clean up
        handler.set_constraints(None)

    def test_combined_constraints_validates_both(self, mocker: MockerFixture) -> None:
        """Evolution should validate both required fields and type constraints."""
        from gepa_adk.adapters.components.component_handlers import get_handler
        from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA, SchemaConstraints

        # Original schema
        class OriginalSchema(BaseModel):
            score: float
            feedback: str

        # Combined constraints
        constraints = SchemaConstraints(
            required_fields=("score", "feedback"),
            preserve_types={"score": float, "feedback": str},
        )

        # Mock agent
        mock_agent = mocker.MagicMock()
        mock_agent.output_schema = OriginalSchema

        # Get handler and set constraints
        handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
        handler.set_constraints(constraints)

        # Valid evolution - keeps both fields with correct types
        valid_schema = """
class EvolvedSchema(BaseModel):
    score: float
    feedback: str
    extra_field: int
"""
        _original = handler.apply(mock_agent, valid_schema)

        # Schema SHOULD change - all constraints satisfied
        assert mock_agent.output_schema is not OriginalSchema
        assert "score" in mock_agent.output_schema.model_fields
        assert "feedback" in mock_agent.output_schema.model_fields
        assert "extra_field" in mock_agent.output_schema.model_fields

        # Clean up
        handler.set_constraints(None)


class TestBackwardCompatibility:
    """Tests verifying backward compatibility when no constraints are set."""

    def test_no_constraints_allows_any_mutation(self, mocker: MockerFixture) -> None:
        """Without constraints, any schema mutation should be allowed."""
        from gepa_adk.adapters.components.component_handlers import get_handler
        from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA

        # Original schema
        class OriginalSchema(BaseModel):
            score: float
            feedback: str

        # Mock agent
        mock_agent = mocker.MagicMock()
        mock_agent.output_schema = OriginalSchema

        # Get handler - no constraints set (backward compatible behavior)
        handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
        handler.set_constraints(None)

        # Completely different schema
        new_schema = """
class TotallyDifferentSchema(BaseModel):
    unrelated_field: str
    another_field: int
"""
        _original = handler.apply(mock_agent, new_schema)

        # Schema SHOULD change - no constraints
        assert mock_agent.output_schema is not OriginalSchema
        assert "unrelated_field" in mock_agent.output_schema.model_fields
        assert "another_field" in mock_agent.output_schema.model_fields
        assert "score" not in mock_agent.output_schema.model_fields

    def test_empty_constraints_allows_any_mutation(self, mocker: MockerFixture) -> None:
        """Empty SchemaConstraints should allow any schema mutation."""
        from gepa_adk.adapters.components.component_handlers import get_handler
        from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA, SchemaConstraints

        # Original schema
        class OriginalSchema(BaseModel):
            score: float

        # Mock agent
        mock_agent = mocker.MagicMock()
        mock_agent.output_schema = OriginalSchema

        # Get handler with empty constraints
        handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
        handler.set_constraints(SchemaConstraints())  # Empty constraints

        # Different schema
        new_schema = """
class NewSchema(BaseModel):
    different: str
"""
        _original = handler.apply(mock_agent, new_schema)

        # Schema SHOULD change - empty constraints allow everything
        assert mock_agent.output_schema is not OriginalSchema
        assert "different" in mock_agent.output_schema.model_fields

        # Clean up
        handler.set_constraints(None)

    def test_existing_tests_unaffected(self) -> None:
        """Verify that existing schema utilities work without constraints."""
        from gepa_adk.utils.schema_utils import (
            deserialize_schema,
            serialize_pydantic_schema,
        )

        # Original schema
        class TestSchema(BaseModel):
            name: str
            value: int

        # Serialize
        schema_text = serialize_pydantic_schema(TestSchema)

        # Verify it's valid Python with class definition
        assert "class TestSchema" in schema_text
        assert "name: str" in schema_text
        assert "value: int" in schema_text

        # Deserialize (different schema text to avoid name collision)
        new_schema_text = """
class NewTestSchema(BaseModel):
    result: str
"""
        NewSchema = deserialize_schema(new_schema_text)

        assert NewSchema is not None
        assert "result" in NewSchema.model_fields
