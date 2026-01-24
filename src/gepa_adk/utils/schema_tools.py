"""ADK tool wrappers for schema validation.

This module provides ADK-compatible tool functions that wrap existing
schema validation utilities from schema_utils. These tools can be used
by reflection agents to validate proposed schemas before returning them.

The tools return dict results compatible with ADK's FunctionTool pattern,
enabling LLM agents to self-validate and retry on errors.

Attributes:
    validate_output_schema (Callable): ADK tool function that validates
        Pydantic schema definitions. Returns structured validation results
        as a dict, enabling LLM agents to validate proposed schemas and
        retry on errors. Never raises exceptions - all errors are returned
        in the result dict.

Examples:
    Use validate_output_schema as an ADK tool:

    ```python
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
    from gepa_adk.utils.schema_tools import validate_output_schema

    agent = LlmAgent(
        name="schema_reflector",
        model="gemini-2.5-flash",
        instruction="Improve the schema. Validate before returning.",
        tools=[FunctionTool(validate_output_schema)],
    )
    ```

See Also:
    - [`gepa_adk.utils.schema_utils`]: Core validation logic.
    - [`gepa_adk.engine.reflection_agents`]: Reflection agent factories.
"""

__all__ = ["validate_output_schema"]

from typing import Any

import structlog

from gepa_adk.domain.exceptions import SchemaValidationError
from gepa_adk.utils.schema_utils import validate_schema_text

logger = structlog.get_logger(__name__)


def validate_output_schema(schema_text: str) -> dict[str, Any]:
    """Validate a Pydantic schema definition.

    This function wraps `validate_schema_text()` to provide a tool-compatible
    interface for ADK agents. It returns structured validation results as a dict,
    enabling LLM agents to validate proposed schemas and retry on errors.

    The function performs three-stage validation:
    1. **Preprocessing**: Strip markdown code fences if present
    2. **Syntax**: Parse Python syntax with ast.parse()
    3. **Structure**: Check for security violations and BaseModel inheritance
    4. **Execution**: Execute in controlled namespace and verify class

    Args:
        schema_text: Python code defining a Pydantic BaseModel class.
            May be wrapped in markdown code fences (` ```python...``` `).

    Returns:
        dict with validation result:
        - If valid: `{"valid": True, "class_name": str, "field_count": int, "field_names": list}`
        - If invalid: `{"valid": False, "errors": list, "stage": str, "line_number": int|None}`

    Examples:
        Valid schema:

        ```python
        from gepa_adk.utils.schema_tools import validate_output_schema

        schema = '''
        class MySchema(BaseModel):
            name: str
            value: int
        '''

        result = validate_output_schema(schema)
        assert result["valid"] is True
        assert result["class_name"] == "MySchema"
        assert result["field_names"] == ["name", "value"]
        ```

        Invalid schema:

        ```python
        schema = '''
        class BadSchema(BaseModel):
            import os  # Not allowed!
        '''

        result = validate_output_schema(schema)
        assert result["valid"] is False
        assert "stage" in result
        assert "errors" in result
        ```

        Tool usage in ADK agent:

        ```python
        from google.adk.agents import LlmAgent
        from google.adk.tools import FunctionTool

        agent = LlmAgent(
            name="schema_validator",
            model="gemini-2.5-flash",
            instruction="Validate and improve schemas",
            tools=[FunctionTool(validate_output_schema)],
        )
        ```

    See Also:
        - [`validate_schema_text()`][gepa_adk.utils.schema_utils.validate_schema_text]:
          Core validation function.

    Note:
        This function never raises exceptions - validation errors are returned
        in the dict result with `valid=False`. This ensures ADK tools can always
        return successfully and let the LLM handle the error.
    """
    try:
        logger.debug(
            "schema_tool.validate.start",
            schema_length=len(schema_text),
        )

        result = validate_schema_text(schema_text)

        logger.info(
            "schema_tool.validate.success",
            class_name=result.class_name,
            field_count=result.field_count,
        )

        return {
            "valid": True,
            "class_name": result.class_name,
            "field_count": result.field_count,
            "field_names": list(result.field_names),
        }

    except SchemaValidationError as e:
        logger.warning(
            "schema_tool.validate.error",
            stage=e.validation_stage,
            error=str(e),
            line_number=getattr(e, "line_number", None),
        )

        return {
            "valid": False,
            "errors": [str(e)],
            "stage": e.validation_stage,
            "line_number": getattr(e, "line_number", None),
        }
