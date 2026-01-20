"""Unit tests for schema validation tool wrappers.

Tests the ADK-compatible tool functions in schema_tools that wrap
core schema validation logic.
"""

from gepa_adk.utils.schema_tools import validate_output_schema


class TestValidateOutputSchema:
    """Tests for validate_output_schema tool function."""

    def test_valid_schema_returns_success(self):
        """Valid Pydantic schema returns success dict with metadata."""
        schema_text = """
class MySchema(BaseModel):
    name: str
    value: int
"""

        result = validate_output_schema(schema_text)

        assert result["valid"] is True
        assert result["class_name"] == "MySchema"
        assert result["field_count"] == 2
        assert set(result["field_names"]) == {"name", "value"}

    def test_invalid_schema_returns_error(self):
        """Invalid schema returns error dict with details."""
        # Import statements not allowed
        schema_text = """
import os

class BadSchema(BaseModel):
    name: str
"""

        result = validate_output_schema(schema_text)

        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0
        assert "stage" in result

    def test_syntax_error_returns_error(self):
        """Schema with syntax error returns error dict."""
        schema_text = """
class BadSchema(BaseModel):
    name: str
    value: int = Field(  # Missing closing parenthesis
"""

        result = validate_output_schema(schema_text)

        assert result["valid"] is False
        assert "errors" in result

    def test_markdown_fences_stripped(self):
        """Schema wrapped in markdown fences is validated correctly."""
        schema_text = """```python
class MySchema(BaseModel):
    field: str
```"""

        result = validate_output_schema(schema_text)

        assert result["valid"] is True
        assert result["class_name"] == "MySchema"

    def test_no_basemodel_returns_error(self):
        """Schema without BaseModel inheritance returns error."""
        schema_text = """
class NotASchema:
    field: str
"""

        result = validate_output_schema(schema_text)

        assert result["valid"] is False
        assert "errors" in result

    def test_multiple_classes_uses_first_basemodel(self):
        """When multiple classes present, first BaseModel is validated."""
        schema_text = """
class Helper:
    pass

class MySchema(BaseModel):
    name: str
"""

        result = validate_output_schema(schema_text)

        assert result["valid"] is True
        assert result["class_name"] == "MySchema"

    def test_complex_schema_with_optional_fields(self):
        """Complex schema with Optional fields validates correctly."""
        schema_text = """
class ComplexSchema(BaseModel):
    required_field: str
    optional_field: int | None = None
    list_field: list[str]
"""

        result = validate_output_schema(schema_text)

        assert result["valid"] is True
        assert result["class_name"] == "ComplexSchema"
        assert result["field_count"] == 3

    def test_empty_string_returns_error(self):
        """Empty schema text returns validation error."""
        result = validate_output_schema("")

        assert result["valid"] is False
        assert "errors" in result
