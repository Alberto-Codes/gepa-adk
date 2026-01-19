# Data Model: Output Schema Evolution

**Feature**: 123-output-schema-evolution
**Date**: 2026-01-18

## Overview

This feature adds schema serialization, validation, and deserialization utilities for evolving Pydantic output schemas as components. No new domain models are required—the existing `Candidate.components` structure already supports arbitrary string-keyed components.

---

## Existing Entities (No Changes Required)

### Candidate

**Location**: `src/gepa_adk/domain/models.py`

```python
@dataclass(slots=True, kw_only=True)
class Candidate:
    components: dict[str, str]  # Already supports "output_schema" as a key
    generation: int = 0
    parent_id: str | None = None
    parent_ids: list[int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Usage for Output Schema**:
```python
candidate = Candidate(
    components={
        "instruction": "Evaluate the input...",
        "output_schema": "class EvalOutput(BaseModel):\n    score: float\n    feedback: str",
    }
)
```

### EvolutionResult

**Location**: `src/gepa_adk/domain/models.py`

```python
@dataclass(slots=True, frozen=True, kw_only=True)
class EvolutionResult:
    evolved_component_text: str  # Contains evolved schema text when output_schema is primary
    # ... other fields unchanged
```

---

## New Data Structures

### SchemaValidationResult

**Location**: `src/gepa_adk/utils/schema_utils.py` (new file)

**Purpose**: Return type for validation function, includes both the class and metadata.

```python
@dataclass(frozen=True)
class SchemaValidationResult:
    """Result of validating a schema text."""

    schema_class: type[BaseModel]
    """The deserialized Pydantic model class."""

    class_name: str
    """Name of the class found in the schema text."""

    field_count: int
    """Number of fields defined in the schema."""

    field_names: tuple[str, ...]
    """Names of all fields in the schema."""
```

### Allowed Namespace Configuration

**Location**: `src/gepa_adk/utils/schema_utils.py`

**Purpose**: Defines what names are available during schema deserialization.

```python
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

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
    # Typing module
    "Any": Any,
    "Dict": Dict,
    "List": List,
    "Optional": Optional,
    "Union": Union,
}
```

---

## Extended Exceptions

### SchemaValidationError (Extend Existing)

**Location**: `src/gepa_adk/domain/exceptions.py`

The existing `SchemaValidationError` class is already suitable. Additional context fields may be added:

```python
class SchemaValidationError(ScoringError):
    """Raised when schema text is invalid."""

    def __init__(
        self,
        message: str,
        *,
        raw_output: str,
        validation_error: str,
        cause: Exception | None = None,
        line_number: int | None = None,  # NEW: Line where error occurred
        validation_stage: str | None = None,  # NEW: "syntax", "structure", "execution"
    ) -> None:
        super().__init__(message, cause=cause)
        self.raw_output = raw_output
        self.validation_error = validation_error
        self.line_number = line_number
        self.validation_stage = validation_stage
```

---

## Function Signatures

### serialize_pydantic_schema

```python
def serialize_pydantic_schema(
    schema_class: type[BaseModel],
) -> str:
    """Serialize a Pydantic model class to Python source code.

    Args:
        schema_class: The Pydantic BaseModel subclass to serialize.

    Returns:
        Python source code string defining the class.

    Raises:
        TypeError: If schema_class is not a BaseModel subclass.
        OSError: If source code cannot be retrieved (e.g., built-in class).
    """
```

### validate_schema_text

```python
def validate_schema_text(
    schema_text: str,
    *,
    allowed_namespace: dict[str, Any] | None = None,
) -> SchemaValidationResult:
    """Validate schema text and return the deserialized class.

    Args:
        schema_text: Python source code defining a Pydantic model.
        allowed_namespace: Override default namespace. If None, uses SCHEMA_NAMESPACE.

    Returns:
        SchemaValidationResult with the deserialized class and metadata.

    Raises:
        SchemaValidationError: If validation fails at any stage.
    """
```

### deserialize_schema

```python
def deserialize_schema(
    schema_text: str,
) -> type[BaseModel]:
    """Deserialize validated schema text to a Pydantic model class.

    Convenience function that calls validate_schema_text and returns only the class.

    Args:
        schema_text: Python source code defining a Pydantic model.

    Returns:
        The deserialized Pydantic BaseModel subclass.

    Raises:
        SchemaValidationError: If validation fails.
    """
```

---

## State Transitions

### Schema Evolution Lifecycle

```
┌─────────────────┐
│ Pydantic Model  │  (agent.output_schema = MySchema)
│     Class       │
└────────┬────────┘
         │ serialize_pydantic_schema()
         ▼
┌─────────────────┐
│  Schema Text    │  (Candidate.components["output_schema"])
│   (Python src)  │
└────────┬────────┘
         │ Evolution Loop (mutation → validation → acceptance)
         ▼
┌─────────────────┐
│ Evolved Schema  │  (EvolutionResult.evolved_component_text)
│     Text        │
└────────┬────────┘
         │ deserialize_schema() / validate_schema_text()
         ▼
┌─────────────────┐
│ Evolved Model   │  (agent.output_schema = EvolvedSchema)
│     Class       │
└─────────────────┘
```

---

## Validation Rules

### Syntax Stage

| Rule | Check | Error |
|------|-------|-------|
| Valid Python | `ast.parse()` succeeds | SyntaxError with line number |
| No imports | No `Import` or `ImportFrom` nodes | "Import statements not allowed" |
| No functions | No `FunctionDef` or `AsyncFunctionDef` nodes | "Function definitions not allowed" |

### Structure Stage

| Rule | Check | Error |
|------|-------|-------|
| Has class | At least one `ClassDef` node | "No class definition found" |
| Inherits BaseModel | Class has `BaseModel` in bases | "Class must inherit from BaseModel" |
| No decorators (except Field) | No `@validator`, `@root_validator` | "Custom validators not allowed" |

### Execution Stage

| Rule | Check | Error |
|------|-------|-------|
| Executes cleanly | `exec()` succeeds | Execution error with traceback |
| Class is BaseModel | `issubclass(cls, BaseModel)` | "Not a valid BaseModel subclass" |
| Has fields | `cls.model_fields` is not empty | "Schema must define at least one field" |

---

## Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                        Evolution Engine                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  Candidate  │───▶│  Proposer   │───▶│ validate_schema_text│  │
│  │ .components │    │ (mutation)  │    │ (before acceptance) │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Schema Utils Module                         │
│  ┌───────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │serialize_pydantic_│  │validate_schema_ │  │deserialize_   │  │
│  │schema()           │  │text()           │  │schema()       │  │
│  └───────────────────┘  └─────────────────┘  └───────────────┘  │
│                              │                                   │
│                              ▼                                   │
│                   ┌─────────────────────┐                        │
│                   │SchemaValidationError│                        │
│                   └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Migration Notes

- **No database migrations**: This feature is in-memory only
- **No breaking changes**: All existing code continues to work
- **Backwards compatible**: Agents without output_schema are unaffected
