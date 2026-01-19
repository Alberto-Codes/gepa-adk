"""Schema utilities for output schema evolution.

This module provides serialization, validation, and deserialization
utilities for evolving Pydantic output schemas as components.

The module enables the evolution engine to:
1. Serialize Pydantic BaseModel classes to Python source text
2. Validate proposed schema mutations for correctness and security
3. Deserialize validated schema text back to usable Pydantic models

Attributes:
    SCHEMA_NAMESPACE (dict): Controlled namespace for schema execution containing
        Pydantic types, built-in types, and typing constructs.
    SchemaValidationResult (class): Dataclass containing validation results and
        metadata about the deserialized schema.
    serialize_pydantic_schema (function): Convert a Pydantic model class to
        Python source code text.
    validate_schema_text (function): Validate schema text and return the
        deserialized class with metadata.
    deserialize_schema (function): Convenience wrapper to deserialize schema
        text directly to a Pydantic class.

Examples:
    Basic round-trip workflow:

    ```python
    from pydantic import BaseModel
    from gepa_adk.utils.schema_utils import (
        serialize_pydantic_schema,
        deserialize_schema,
    )

    class MySchema(BaseModel):
        name: str
        value: int

    # Serialize for evolution
    text = serialize_pydantic_schema(MySchema)

    # After evolution, deserialize back
    EvolvedSchema = deserialize_schema(evolved_text)
    ```

See Also:
    - [`SchemaValidationError`][gepa_adk.domain.exceptions.SchemaValidationError]:
      Exception raised for validation failures.
    - [Single-Agent Evolution Guide](/guides/single-agent): Usage in evolution workflows.

Note:
    Schema validation uses AST parsing before controlled exec() to prevent
    arbitrary code execution. Import statements and function definitions
    are explicitly rejected.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional, Union

import structlog
from pydantic import BaseModel, Field

from gepa_adk.domain.exceptions import SchemaValidationError

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

__all__ = [
    "SCHEMA_NAMESPACE",
    "SchemaValidationResult",
    "serialize_pydantic_schema",
    "validate_schema_text",
    "deserialize_schema",
]


# =============================================================================
# Constants
# =============================================================================

SCHEMA_NAMESPACE: dict[str, Any] = {
    # Pydantic
    "BaseModel": BaseModel,
    "Field": Field,
    # Built-in types
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "type": type,
    # Typing module (imported at module level for namespace)
    "Any": Any,
    "Optional": None,  # Placeholder - will be set below
    "Union": None,  # Placeholder - will be set below
    "List": list,  # Generic alias
    "Dict": dict,  # Generic alias
}

SCHEMA_NAMESPACE["Optional"] = Optional
SCHEMA_NAMESPACE["Union"] = Union


# =============================================================================
# Data Structures
# =============================================================================


@dataclass(frozen=True)
class SchemaValidationResult:
    """Result of validating schema text.

    This dataclass contains both the deserialized Pydantic model class
    and metadata about the schema structure.

    Attributes:
        schema_class (type[BaseModel]): The deserialized Pydantic BaseModel subclass.
        class_name (str): Name of the class found in the schema text.
        field_count (int): Number of fields defined in the schema.
        field_names (tuple[str, ...]): Tuple of field names in the schema.

    Examples:
        Validating schema text and inspecting results:

        ```python
        result = validate_schema_text(schema_text)
        print(f"Class: {result.class_name}")
        print(f"Fields: {result.field_names}")
        instance = result.schema_class(name="test", value=42)
        ```

        Creating a result directly (typically done by validate_schema_text):

        ```python
        result = SchemaValidationResult(
            schema_class=MySchema,
            class_name="MySchema",
            field_count=2,
            field_names=("name", "value"),
        )
        ```
    """

    schema_class: type[BaseModel]
    class_name: str
    field_count: int
    field_names: tuple[str, ...]


# =============================================================================
# Serialization (US1)
# =============================================================================


def serialize_pydantic_schema(schema_class: type[BaseModel]) -> str:
    """Serialize a Pydantic model class to Python source code.

    Uses inspect.getsource() to retrieve the original source code definition
    of the schema class. This preserves Field() constraints, defaults, and
    docstrings.

    Args:
        schema_class (type[BaseModel]): The Pydantic BaseModel subclass to serialize.

    Returns:
        Python source code string defining the class.

    Raises:
        TypeError: If schema_class is not a BaseModel subclass or is an instance.
        OSError: If source code cannot be retrieved (e.g., dynamic class).

    Examples:
        Serialize a schema to source code:

        ```python
        from pydantic import BaseModel, Field
        from gepa_adk.utils.schema_utils import serialize_pydantic_schema

        class MySchema(BaseModel):
            name: str
            value: int = Field(ge=0)

        text = serialize_pydantic_schema(MySchema)
        # text contains the Python source code for MySchema
        ```
    """
    # Type validation
    if not isinstance(schema_class, type):
        raise TypeError(
            f"Expected a class, got {type(schema_class).__name__} instance. "
            "Pass the class itself, not an instance."
        )

    if not issubclass(schema_class, BaseModel):
        raise TypeError(
            f"Expected a BaseModel subclass, got {schema_class.__name__}. "
            "Schema class must inherit from pydantic.BaseModel."
        )

    logger.debug(
        "schema.serialize.start",
        class_name=schema_class.__name__,
        field_count=len(schema_class.model_fields),
    )

    try:
        source = inspect.getsource(schema_class)
    except OSError as e:
        logger.warning(
            "schema.serialize.failed",
            class_name=schema_class.__name__,
            error=str(e),
        )
        raise

    logger.debug(
        "schema.serialize.complete",
        class_name=schema_class.__name__,
        source_length=len(source),
    )

    return source


# =============================================================================
# Validation (US2)
# =============================================================================


def _validate_syntax(schema_text: str) -> ast.Module:
    """Validate Python syntax and return AST.

    Args:
        schema_text: Python source code to parse.

    Returns:
        Parsed AST module.

    Raises:
        SchemaValidationError: If syntax is invalid.
    """
    try:
        return ast.parse(schema_text)
    except SyntaxError as e:
        logger.debug(
            "schema.validate.syntax_error",
            line_number=e.lineno,
            error=str(e),
        )
        raise SchemaValidationError(
            f"Invalid Python syntax at line {e.lineno}: {e.msg}",
            raw_output=schema_text,
            validation_error=str(e),
            cause=e,
            line_number=e.lineno,
            validation_stage="syntax",
        ) from e


def _validate_structure(tree: ast.Module, schema_text: str) -> str:
    """Validate AST structure for security and correctness.

    Checks for:
    - No import statements
    - No function definitions
    - At least one class inheriting from BaseModel

    Args:
        tree: Parsed AST module.
        schema_text: Original source text (for error context).

    Returns:
        Name of the BaseModel subclass found.

    Raises:
        SchemaValidationError: If structure is invalid.
    """
    class_name: str | None = None

    for node in ast.walk(tree):
        # Reject import statements
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            logger.debug(
                "schema.validate.import_rejected",
                node_type=type(node).__name__,
            )
            raise SchemaValidationError(
                "Import statements are not allowed in schema definitions",
                raw_output=schema_text,
                validation_error="Import statements not allowed for security",
                line_number=node.lineno,
                validation_stage="structure",
            )

        # Reject function definitions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            logger.debug(
                "schema.validate.function_rejected",
                function_name=node.name,
            )
            raise SchemaValidationError(
                f"Function definitions are not allowed: '{node.name}'",
                raw_output=schema_text,
                validation_error="Function definitions not allowed for security",
                line_number=node.lineno,
                validation_stage="structure",
            )

        # Find BaseModel subclass
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "BaseModel":
                    class_name = node.name
                    break

    if not class_name:
        logger.debug("schema.validate.no_basemodel")
        raise SchemaValidationError(
            "No BaseModel subclass found in schema text",
            raw_output=schema_text,
            validation_error="Schema must define a class inheriting from BaseModel",
            validation_stage="structure",
        )

    return class_name


def _execute_schema(
    schema_text: str,
    class_name: str,
    namespace: dict[str, Any],
) -> type[BaseModel]:
    """Execute schema text in controlled namespace.

    Args:
        schema_text: Validated Python source code.
        class_name: Name of the class to extract.
        namespace: Controlled namespace for exec().

    Returns:
        The deserialized BaseModel subclass.

    Raises:
        SchemaValidationError: If execution fails.
    """
    # Create a copy of namespace to avoid pollution
    exec_namespace = namespace.copy()

    try:
        exec(schema_text, exec_namespace)  # noqa: S102
    except Exception as e:
        logger.debug(
            "schema.validate.exec_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise SchemaValidationError(
            f"Schema execution failed: {e}",
            raw_output=schema_text,
            validation_error=str(e),
            cause=e,
            validation_stage="execution",
        ) from e

    schema_class = exec_namespace.get(class_name)
    if schema_class is None:
        raise SchemaValidationError(
            f"Class '{class_name}' not found after execution",
            raw_output=schema_text,
            validation_error=f"Expected class {class_name} was not created",
            validation_stage="execution",
        )

    if not issubclass(schema_class, BaseModel):
        raise SchemaValidationError(
            f"'{class_name}' is not a valid BaseModel subclass",
            raw_output=schema_text,
            validation_error="Class does not inherit from BaseModel",
            validation_stage="execution",
        )

    return schema_class


def validate_schema_text(
    schema_text: str,
    *,
    allowed_namespace: dict[str, Any] | None = None,
) -> SchemaValidationResult:
    """Validate schema text and return the deserialized class.

    Performs three-stage validation:
    1. **Syntax**: Parse Python syntax with ast.parse()
    2. **Structure**: Check for security violations and BaseModel inheritance
    3. **Execution**: Execute in controlled namespace and verify class

    Args:
        schema_text: Python source code defining a Pydantic model.
        allowed_namespace: Override default namespace. If None, uses SCHEMA_NAMESPACE.

    Returns:
        SchemaValidationResult with the deserialized class and metadata.

    Raises:
        SchemaValidationError: If validation fails at any stage.

    Example:
        >>> schema_text = '''
        ... class MySchema(BaseModel):
        ...     name: str
        ...     value: int
        ... '''
        >>> result = validate_schema_text(schema_text)
        >>> result.class_name
        'MySchema'
        >>> result.field_names
        ('name', 'value')
    """
    logger.debug(
        "schema.validate.start",
        text_length=len(schema_text),
    )

    # Stage 1: Syntax validation
    tree = _validate_syntax(schema_text)

    # Stage 2: Structure validation
    class_name = _validate_structure(tree, schema_text)

    # Stage 3: Execution
    namespace = allowed_namespace if allowed_namespace is not None else SCHEMA_NAMESPACE
    schema_class = _execute_schema(schema_text, class_name, namespace)

    # Build result
    field_names = tuple(schema_class.model_fields.keys())
    result = SchemaValidationResult(
        schema_class=schema_class,
        class_name=class_name,
        field_count=len(field_names),
        field_names=field_names,
    )

    logger.debug(
        "schema.validate.complete",
        class_name=class_name,
        field_count=result.field_count,
        field_names=list(field_names),
    )

    return result


# =============================================================================
# Deserialization (US3)
# =============================================================================


def deserialize_schema(schema_text: str) -> type[BaseModel]:
    """Deserialize validated schema text to a Pydantic model class.

    Convenience function that calls validate_schema_text and returns only
    the schema class. Use this when you only need the class and don't need
    the validation metadata.

    Args:
        schema_text: Python source code defining a Pydantic model.

    Returns:
        The deserialized Pydantic BaseModel subclass.

    Raises:
        SchemaValidationError: If validation fails.

    Example:
        >>> schema_text = '''
        ... class EvolvedSchema(BaseModel):
        ...     result: str
        ...     confidence: float = Field(ge=0.0, le=1.0)
        ... '''
        >>> EvolvedSchema = deserialize_schema(schema_text)
        >>> instance = EvolvedSchema(result="success", confidence=0.95)
    """
    logger.debug(
        "schema.deserialize.start",
        text_length=len(schema_text),
    )

    result = validate_schema_text(schema_text)

    logger.debug(
        "schema.deserialize.complete",
        class_name=result.class_name,
    )

    return result.schema_class
