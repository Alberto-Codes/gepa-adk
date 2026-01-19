"""Contract tests for schema_utils module.

These contracts define the expected behavior of schema serialization,
validation, and deserialization functions. Implementation must satisfy
all contracts to be considered complete.

Contract tests run on every commit to verify protocol compliance.
"""

from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from gepa_adk.utils.schema_utils import (
        SchemaValidationResult,
        deserialize_schema,
        serialize_pydantic_schema,
        validate_schema_text,
    )


# =============================================================================
# Test Fixtures
# =============================================================================


class SimpleSchema(BaseModel):
    """Simple schema for testing."""

    name: str
    value: int


class SchemaWithDefaults(BaseModel):
    """Schema with Field defaults and constraints."""

    score: float = Field(ge=0.0, le=1.0, default=0.5)
    feedback: str = Field(default="")
    tags: list[str] = Field(default_factory=list)


class SchemaWithOptional(BaseModel):
    """Schema with Optional fields."""

    required_field: str
    optional_field: str | None = None


# =============================================================================
# Serialization Contracts
# =============================================================================


class TestSerializePydanticSchemaContract:
    """Contract: serialize_pydantic_schema() behavior."""

    def test_returns_string(self, serialize_pydantic_schema):
        """MUST return a string."""
        result = serialize_pydantic_schema(SimpleSchema)
        assert isinstance(result, str)

    def test_contains_class_definition(self, serialize_pydantic_schema):
        """MUST contain the class definition."""
        result = serialize_pydantic_schema(SimpleSchema)
        assert "class SimpleSchema" in result
        assert "BaseModel" in result

    def test_contains_fields(self, serialize_pydantic_schema):
        """MUST contain field definitions."""
        result = serialize_pydantic_schema(SimpleSchema)
        assert "name: str" in result
        assert "value: int" in result

    def test_preserves_field_constraints(self, serialize_pydantic_schema):
        """MUST preserve Field() constraints."""
        result = serialize_pydantic_schema(SchemaWithDefaults)
        assert "Field(" in result
        # Constraints should be present
        assert "ge=" in result or "0.0" in result
        assert "le=" in result or "1.0" in result

    def test_rejects_non_basemodel(self, serialize_pydantic_schema):
        """MUST reject non-BaseModel classes."""
        with pytest.raises(TypeError):
            serialize_pydantic_schema(dict)

    def test_rejects_instance(self, serialize_pydantic_schema):
        """MUST reject instances (not classes)."""
        instance = SimpleSchema(name="test", value=1)
        with pytest.raises(TypeError):
            serialize_pydantic_schema(instance)


# =============================================================================
# Validation Contracts
# =============================================================================


class TestValidateSchemaTextContract:
    """Contract: validate_schema_text() behavior."""

    def test_returns_validation_result(self, validate_schema_text):
        """MUST return SchemaValidationResult."""
        schema_text = '''
class TestSchema(BaseModel):
    field: str
'''
        result = validate_schema_text(schema_text)
        assert hasattr(result, "schema_class")
        assert hasattr(result, "class_name")
        assert hasattr(result, "field_count")

    def test_result_has_valid_class(self, validate_schema_text):
        """MUST return a valid BaseModel subclass."""
        schema_text = '''
class TestSchema(BaseModel):
    field: str
'''
        result = validate_schema_text(schema_text)
        assert issubclass(result.schema_class, BaseModel)

    def test_rejects_syntax_errors(self, validate_schema_text):
        """MUST reject invalid Python syntax."""
        from gepa_adk.domain.exceptions import SchemaValidationError

        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text("class Broken(BaseModel:\n    x: int")  # Missing )
        assert "syntax" in str(exc_info.value).lower()

    def test_rejects_missing_basemodel(self, validate_schema_text):
        """MUST reject classes not inheriting from BaseModel."""
        from gepa_adk.domain.exceptions import SchemaValidationError

        schema_text = '''
class NotAModel:
    field: str
'''
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text(schema_text)
        assert "BaseModel" in str(exc_info.value)

    def test_rejects_import_statements(self, validate_schema_text):
        """MUST reject import statements for security."""
        from gepa_adk.domain.exceptions import SchemaValidationError

        schema_text = '''
import os
class Malicious(BaseModel):
    field: str
'''
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text(schema_text)
        assert "import" in str(exc_info.value).lower()

    def test_rejects_function_definitions(self, validate_schema_text):
        """MUST reject function definitions for security."""
        from gepa_adk.domain.exceptions import SchemaValidationError

        schema_text = '''
def helper():
    return "hack"

class WithFunction(BaseModel):
    field: str
'''
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text(schema_text)
        assert "function" in str(exc_info.value).lower()

    def test_accepts_field_constraints(self, validate_schema_text):
        """MUST accept Field() with constraints."""
        schema_text = '''
class Constrained(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    name: str = Field(min_length=1, max_length=100)
'''
        result = validate_schema_text(schema_text)
        assert result.class_name == "Constrained"
        assert result.field_count == 2

    def test_accepts_optional_fields(self, validate_schema_text):
        """MUST accept Optional type annotations."""
        schema_text = '''
class WithOptional(BaseModel):
    required: str
    optional: str | None = None
'''
        result = validate_schema_text(schema_text)
        assert "optional" in result.field_names


# =============================================================================
# Deserialization Contracts
# =============================================================================


class TestDeserializeSchemaContract:
    """Contract: deserialize_schema() behavior."""

    def test_returns_basemodel_class(self, deserialize_schema):
        """MUST return a BaseModel subclass."""
        schema_text = '''
class TestSchema(BaseModel):
    field: str
'''
        result = deserialize_schema(schema_text)
        assert issubclass(result, BaseModel)

    def test_class_is_usable(self, deserialize_schema):
        """MUST return a usable class that can be instantiated."""
        schema_text = '''
class UsableSchema(BaseModel):
    name: str
    value: int = 0
'''
        Schema = deserialize_schema(schema_text)
        # Should be able to instantiate
        instance = Schema(name="test")
        assert instance.name == "test"
        assert instance.value == 0

    def test_propagates_validation_errors(self, deserialize_schema):
        """MUST propagate SchemaValidationError for invalid text."""
        from gepa_adk.domain.exceptions import SchemaValidationError

        with pytest.raises(SchemaValidationError):
            deserialize_schema("not valid python {{{")


# =============================================================================
# Round-Trip Contracts
# =============================================================================


class TestRoundTripContract:
    """Contract: serialize → deserialize round-trip."""

    def test_round_trip_preserves_fields(
        self, serialize_pydantic_schema, deserialize_schema
    ):
        """MUST preserve field names in round-trip."""
        text = serialize_pydantic_schema(SimpleSchema)
        Restored = deserialize_schema(text)

        original_fields = set(SimpleSchema.model_fields.keys())
        restored_fields = set(Restored.model_fields.keys())
        assert original_fields == restored_fields

    def test_round_trip_preserves_types(
        self, serialize_pydantic_schema, deserialize_schema
    ):
        """MUST preserve field types in round-trip."""
        text = serialize_pydantic_schema(SimpleSchema)
        Restored = deserialize_schema(text)

        # Create instances and verify types
        original = SimpleSchema(name="test", value=42)
        restored = Restored(name="test", value=42)

        assert type(original.name) == type(restored.name)
        assert type(original.value) == type(restored.value)


# =============================================================================
# Fixtures (to be provided by conftest.py)
# =============================================================================


@pytest.fixture
def serialize_pydantic_schema():
    """Provide serialize_pydantic_schema function."""
    from gepa_adk.utils.schema_utils import serialize_pydantic_schema

    return serialize_pydantic_schema


@pytest.fixture
def validate_schema_text():
    """Provide validate_schema_text function."""
    from gepa_adk.utils.schema_utils import validate_schema_text

    return validate_schema_text


@pytest.fixture
def deserialize_schema():
    """Provide deserialize_schema function."""
    from gepa_adk.utils.schema_utils import deserialize_schema

    return deserialize_schema
