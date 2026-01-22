"""Unit tests for OutputSchemaHandler constraint integration.

These tests verify that OutputSchemaHandler correctly validates
schema mutations against constraints.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel
from pytest_mock import MockerFixture


class TestOutputSchemaHandlerConstraints:
    """Tests for OutputSchemaHandler constraint validation."""

    def test_set_constraints(self) -> None:
        """Handler should store constraints via set_constraints()."""
        from gepa_adk.adapters.component_handlers import OutputSchemaHandler
        from gepa_adk.domain.types import SchemaConstraints

        handler = OutputSchemaHandler()
        constraints = SchemaConstraints(required_fields=("score",))

        handler.set_constraints(constraints)

        assert handler._constraints is constraints

    def test_set_constraints_none_clears(self) -> None:
        """Setting constraints to None should clear them."""
        from gepa_adk.adapters.component_handlers import OutputSchemaHandler
        from gepa_adk.domain.types import SchemaConstraints

        handler = OutputSchemaHandler()
        handler.set_constraints(SchemaConstraints(required_fields=("score",)))
        handler.set_constraints(None)

        assert handler._constraints is None

    def test_apply_accepts_valid_mutation(self, mocker: MockerFixture) -> None:
        """Handler should apply mutation when constraints satisfied."""
        from gepa_adk.adapters.component_handlers import OutputSchemaHandler
        from gepa_adk.domain.types import SchemaConstraints

        class OriginalSchema(BaseModel):
            score: float
            old_field: str

        handler = OutputSchemaHandler()
        handler.set_constraints(SchemaConstraints(required_fields=("score",)))

        agent = mocker.MagicMock()
        agent.output_schema = OriginalSchema

        new_schema_text = '''
class NewSchema(BaseModel):
    score: float
    new_field: str
'''

        original = handler.apply(agent, new_schema_text)

        # Verify new schema was applied
        assert agent.output_schema is not OriginalSchema
        assert "score" in agent.output_schema.model_fields
        assert "new_field" in agent.output_schema.model_fields

    def test_apply_rejects_invalid_mutation(self, mocker: MockerFixture) -> None:
        """Handler should keep original when constraints violated."""
        from gepa_adk.adapters.component_handlers import OutputSchemaHandler
        from gepa_adk.domain.types import SchemaConstraints

        class OriginalSchema(BaseModel):
            score: float
            feedback: str

        handler = OutputSchemaHandler()
        handler.set_constraints(SchemaConstraints(required_fields=("score",)))

        agent = mocker.MagicMock()
        agent.output_schema = OriginalSchema

        invalid_schema_text = '''
class NewSchema(BaseModel):
    feedback: str
'''

        handler.apply(agent, invalid_schema_text)

        # Schema should be unchanged
        assert agent.output_schema is OriginalSchema
        assert "score" in agent.output_schema.model_fields

    def test_apply_without_constraints_allows_all(self, mocker: MockerFixture) -> None:
        """Handler without constraints should allow all mutations."""
        from gepa_adk.adapters.component_handlers import OutputSchemaHandler

        class OriginalSchema(BaseModel):
            score: float

        handler = OutputSchemaHandler()
        # No set_constraints() call

        agent = mocker.MagicMock()
        agent.output_schema = OriginalSchema

        new_schema_text = '''
class TotallyDifferent(BaseModel):
    unrelated: str
'''

        handler.apply(agent, new_schema_text)

        # Mutation should be applied
        assert "unrelated" in agent.output_schema.model_fields
        assert "score" not in agent.output_schema.model_fields
