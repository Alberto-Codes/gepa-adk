"""Unit tests for schema_utils module.

Tests for schema serialization, validation, and deserialization utilities
used in output schema evolution.
"""

import pytest
from pydantic import BaseModel, Field

# =============================================================================
# Test Schemas
# =============================================================================


class SimpleSchema(BaseModel):
    """Simple schema for testing."""

    name: str
    value: int


class SchemaWithConstraints(BaseModel):
    """Schema with Field constraints."""

    score: float = Field(ge=0.0, le=1.0, default=0.5)
    feedback: str = Field(default="", max_length=1000)


class SchemaWithOptional(BaseModel):
    """Schema with optional fields."""

    required_field: str
    optional_field: str | None = None


# =============================================================================
# Serialization Tests (US1)
# =============================================================================


@pytest.mark.unit
class TestSerializePydanticSchema:
    """Unit tests for serialize_pydantic_schema()."""

    def test_serialize_simple_schema(self):
        """Should serialize a simple BaseModel to source code."""
        from gepa_adk.utils.schema_utils import serialize_pydantic_schema

        result = serialize_pydantic_schema(SimpleSchema)

        assert isinstance(result, str)
        assert "class SimpleSchema" in result
        assert "BaseModel" in result
        assert "name: str" in result
        assert "value: int" in result

    def test_serialize_preserves_constraints(self):
        """Should preserve Field() constraints in serialized output."""
        from gepa_adk.utils.schema_utils import serialize_pydantic_schema

        result = serialize_pydantic_schema(SchemaWithConstraints)

        assert "Field(" in result
        assert "ge=" in result or "0.0" in result
        assert "le=" in result or "1.0" in result
        assert "default=" in result

    def test_serialize_preserves_optional(self):
        """Should preserve Optional type annotations."""
        from gepa_adk.utils.schema_utils import serialize_pydantic_schema

        result = serialize_pydantic_schema(SchemaWithOptional)

        assert "optional_field" in result
        assert "None" in result

    def test_serialize_rejects_non_class(self):
        """Should reject non-class arguments."""
        from gepa_adk.utils.schema_utils import serialize_pydantic_schema

        with pytest.raises(TypeError):
            serialize_pydantic_schema("not a class")

    def test_serialize_rejects_non_basemodel(self):
        """Should reject classes not inheriting from BaseModel."""
        from gepa_adk.utils.schema_utils import serialize_pydantic_schema

        class NotAModel:
            field: str

        with pytest.raises(TypeError):
            serialize_pydantic_schema(NotAModel)

    def test_serialize_rejects_instance(self):
        """Should reject BaseModel instances (not classes)."""
        from gepa_adk.utils.schema_utils import serialize_pydantic_schema

        instance = SimpleSchema(name="test", value=1)

        with pytest.raises(TypeError):
            serialize_pydantic_schema(instance)

    def test_serialize_includes_docstring(self):
        """Should include class docstring if present."""
        from gepa_adk.utils.schema_utils import serialize_pydantic_schema

        result = serialize_pydantic_schema(SimpleSchema)

        assert "Simple schema for testing" in result


# =============================================================================
# Validation Tests (US2)
# =============================================================================


@pytest.mark.unit
class TestValidateSchemaTextSyntax:
    """Unit tests for validate_schema_text() syntax validation."""

    def test_rejects_syntax_error(self):
        """Should reject code with Python syntax errors."""
        from gepa_adk.domain.exceptions import SchemaValidationError
        from gepa_adk.utils.schema_utils import validate_schema_text

        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text("class Broken(BaseModel:\n    x: int")

        assert exc_info.value.validation_stage == "syntax"
        assert exc_info.value.line_number is not None

    def test_rejects_incomplete_code(self):
        """Should reject incomplete Python code."""
        from gepa_adk.domain.exceptions import SchemaValidationError
        from gepa_adk.utils.schema_utils import validate_schema_text

        with pytest.raises(SchemaValidationError):
            validate_schema_text("class Incomplete(")


@pytest.mark.unit
class TestValidateSchemaTextStructure:
    """Unit tests for validate_schema_text() structure validation."""

    def test_rejects_no_class(self):
        """Should reject code without any class definition."""
        from gepa_adk.domain.exceptions import SchemaValidationError
        from gepa_adk.utils.schema_utils import validate_schema_text

        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text("x = 1\ny = 2")

        assert "BaseModel" in str(exc_info.value)

    def test_rejects_non_basemodel_class(self):
        """Should reject classes not inheriting from BaseModel."""
        from gepa_adk.domain.exceptions import SchemaValidationError
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
class NotAModel:
    field: str
"""
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text(schema_text)

        assert "BaseModel" in str(exc_info.value)
        assert exc_info.value.validation_stage == "structure"


@pytest.mark.unit
class TestValidateSchemaTextSecurity:
    """Unit tests for validate_schema_text() security rules."""

    def test_rejects_import_statement(self):
        """Should reject import statements."""
        from gepa_adk.domain.exceptions import SchemaValidationError
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
import os
class Malicious(BaseModel):
    field: str
"""
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text(schema_text)

        assert "import" in str(exc_info.value).lower()
        assert exc_info.value.validation_stage == "structure"

    def test_rejects_from_import_statement(self):
        """Should reject from...import statements."""
        from gepa_adk.domain.exceptions import SchemaValidationError
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
from os import path
class Malicious(BaseModel):
    field: str
"""
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text(schema_text)

        assert "import" in str(exc_info.value).lower()

    def test_rejects_function_definition(self):
        """Should reject function definitions."""
        from gepa_adk.domain.exceptions import SchemaValidationError
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
def helper():
    return "hack"

class WithFunction(BaseModel):
    field: str
"""
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text(schema_text)

        assert "function" in str(exc_info.value).lower()
        assert exc_info.value.validation_stage == "structure"

    def test_rejects_async_function_definition(self):
        """Should reject async function definitions."""
        from gepa_adk.domain.exceptions import SchemaValidationError
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
async def async_helper():
    return "hack"

class WithAsyncFunction(BaseModel):
    field: str
"""
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text(schema_text)

        assert "function" in str(exc_info.value).lower()


@pytest.mark.unit
class TestValidateSchemaTextValid:
    """Unit tests for validate_schema_text() with valid schemas."""

    def test_accepts_simple_schema(self):
        """Should accept a simple valid schema."""
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
class TestSchema(BaseModel):
    name: str
    value: int
"""
        result = validate_schema_text(schema_text)

        assert result.class_name == "TestSchema"
        assert result.field_count == 2
        assert "name" in result.field_names
        assert "value" in result.field_names

    def test_accepts_schema_with_constraints(self):
        """Should accept schema with Field() constraints."""
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
class Constrained(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    name: str = Field(min_length=1)
"""
        result = validate_schema_text(schema_text)

        assert result.class_name == "Constrained"
        assert result.field_count == 2

    def test_accepts_schema_with_optional(self):
        """Should accept schema with Optional fields."""
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
class WithOptional(BaseModel):
    required: str
    optional: str | None = None
"""
        result = validate_schema_text(schema_text)

        assert "optional" in result.field_names

    def test_accepts_schema_with_list_types(self):
        """Should accept schema with list type annotations."""
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
class WithList(BaseModel):
    items: list[str]
    scores: list[float] = Field(default_factory=list)
"""
        result = validate_schema_text(schema_text)

        assert result.field_count == 2

    def test_accepts_schema_with_dict_types(self):
        """Should accept schema with dict type annotations."""
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
class WithDict(BaseModel):
    metadata: dict[str, str] = Field(default_factory=dict)
"""
        result = validate_schema_text(schema_text)

        assert "metadata" in result.field_names


class TestValidateSchemaTextMarkdownFences:
    """Tests for markdown code fence stripping."""

    def test_accepts_schema_with_python_fence(self):
        """Should strip ```python fences and validate the code inside."""
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """```python
class FencedSchema(BaseModel):
    name: str
    value: int
```"""
        result = validate_schema_text(schema_text)

        assert result.class_name == "FencedSchema"
        assert result.field_names == ("name", "value")

    def test_accepts_schema_with_plain_fence(self):
        """Should strip plain ``` fences without language identifier."""
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """```
class PlainFenced(BaseModel):
    data: str
```"""
        result = validate_schema_text(schema_text)

        assert result.class_name == "PlainFenced"

    def test_accepts_schema_with_py_fence(self):
        """Should strip ```py fences (short form)."""
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """```py
class PyFenced(BaseModel):
    field: str
```"""
        result = validate_schema_text(schema_text)

        assert result.class_name == "PyFenced"

    def test_preserves_schema_without_fences(self):
        """Should preserve schema text that has no fences."""
        from gepa_adk.utils.schema_utils import validate_schema_text

        schema_text = """
class NoFences(BaseModel):
    field: str
"""
        result = validate_schema_text(schema_text)

        assert result.class_name == "NoFences"


# =============================================================================
# Deserialization Tests (US3)
# =============================================================================


@pytest.mark.unit
class TestDeserializeSchema:
    """Unit tests for deserialize_schema()."""

    def test_deserialize_simple_schema(self):
        """Should deserialize valid schema text to a class."""
        from gepa_adk.utils.schema_utils import deserialize_schema

        schema_text = """
class TestSchema(BaseModel):
    name: str
    value: int = 0
"""
        Schema = deserialize_schema(schema_text)

        assert issubclass(Schema, BaseModel)
        assert Schema.__name__ == "TestSchema"

    def test_deserialized_class_is_usable(self):
        """Should return a usable class that can be instantiated."""
        from gepa_adk.utils.schema_utils import deserialize_schema

        schema_text = """
class UsableSchema(BaseModel):
    name: str
    value: int = 0
"""
        Schema = deserialize_schema(schema_text)
        instance = Schema(name="test")

        assert instance.name == "test"
        assert instance.value == 0

    def test_deserialize_propagates_errors(self):
        """Should propagate SchemaValidationError for invalid text."""
        from gepa_adk.domain.exceptions import SchemaValidationError
        from gepa_adk.utils.schema_utils import deserialize_schema

        with pytest.raises(SchemaValidationError):
            deserialize_schema("invalid python {{{")


# =============================================================================
# Round-Trip Tests (US3)
# =============================================================================


@pytest.mark.unit
class TestSchemaRoundTrip:
    """Unit tests for serialize -> deserialize round-trip."""

    def test_round_trip_preserves_fields(self):
        """Should preserve field names in round-trip."""
        from gepa_adk.utils.schema_utils import (
            deserialize_schema,
            serialize_pydantic_schema,
        )

        text = serialize_pydantic_schema(SimpleSchema)
        Restored = deserialize_schema(text)

        original_fields = set(SimpleSchema.model_fields.keys())
        restored_fields = set(Restored.model_fields.keys())
        assert original_fields == restored_fields

    def test_round_trip_preserves_types(self):
        """Should preserve field types in round-trip."""
        from gepa_adk.utils.schema_utils import (
            deserialize_schema,
            serialize_pydantic_schema,
        )

        text = serialize_pydantic_schema(SimpleSchema)
        Restored = deserialize_schema(text)

        original = SimpleSchema(name="test", value=42)
        restored = Restored(name="test", value=42)

        assert type(original.name) is type(restored.name)
        assert type(original.value) is type(restored.value)

    def test_round_trip_with_constraints(self):
        """Should preserve field constraints in round-trip."""
        from gepa_adk.utils.schema_utils import (
            deserialize_schema,
            serialize_pydantic_schema,
        )

        text = serialize_pydantic_schema(SchemaWithConstraints)
        Restored = deserialize_schema(text)

        # Should be able to instantiate with valid values
        instance = Restored(score=0.5, feedback="good")
        assert instance.score == 0.5

        # Should reject invalid values (constraint preserved)
        with pytest.raises(Exception):  # ValidationError
            Restored(score=2.0)  # Exceeds le=1.0
